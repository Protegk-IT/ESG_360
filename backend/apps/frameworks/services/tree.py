from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.frameworks.models import FrameworkNode


class FrameworkTreeService:
    """
    Service responsible for framework tree operations.

    Responsibilities:
        - Create framework nodes
        - Move framework nodes
        - Rebuild subtree metadata
        - Retrieve framework trees
        - Retrieve root nodes
        - Validate hierarchy-related operations

    This service does NOT handle:
        - RBAC
        - Datapoint mappings
        - Report generation
        - Calculation engine
    """

    @staticmethod
    @transaction.atomic
    def create_node(
        *,
        framework_version,
        code,
        title,
        node_type,
        parent=None,
        description="",
        instructions="",
        display_order=0,
        response_format="",
        is_answerable=False,
        is_core=False,
        is_active=True,
    ):
        """
        Create a new framework node.

        The FrameworkNode model is responsible for:
            - validation
            - calculating depth
            - calculating path
            - enforcing model-level constraints
        """

        if parent is not None:
            if parent.framework_version_id != framework_version.id:
                raise ValidationError(
                    "Parent node must belong to the same framework version."
                )

        node = FrameworkNode(
            framework_version=framework_version,
            parent=parent,
            code=code,
            title=title,
            node_type=node_type,
            description=description,
            instructions=instructions,
            display_order=display_order,
            response_format=response_format,
            is_answerable=is_answerable,
            is_core=is_core,
            is_active=is_active,
        )

        node.save()

        return node

    @staticmethod
    @transaction.atomic
    def move_node(
        *,
        node,
        new_parent=None,
    ):
        """
        Move an existing node to a new parent.

        Rules:
            - Parent must belong to the same framework version.
            - A node cannot be its own parent.
            - A node cannot be moved below one of its descendants.
            - The moved node's depth/path are recalculated.
            - All descendants' depth/path are rebuilt.
        """

        if new_parent is not None:

            # Parent must belong to the same framework version.
            if (
                new_parent.framework_version_id
                != node.framework_version_id
            ):
                raise ValidationError(
                    "Parent node must belong to the same framework version."
                )

            # Prevent self-parenting.
            if new_parent.pk == node.pk:
                raise ValidationError(
                    "A node cannot be its own parent."
                )

            # Prevent moving a node below one of its descendants.
            descendant_ids = FrameworkTreeService.get_descendant_ids(
                node
            )

            if new_parent.pk in descendant_ids:
                raise ValidationError(
                    "A node cannot be moved below one of its descendants."
                )

        # Capture the OLD path before it changes.
        # Descendants in the DB still have paths built from this
        # prefix, and we need it to find them after the move.
        old_path = node.path

        # Change parent.
        node.parent = new_parent

        # FrameworkNode.save():
        #   1. validates the node
        #   2. recalculates its own depth/path
        #   3. saves the node
        node.save()

        # Descendants still contain their OLD depth/path.
        # Rebuild the entire subtree using the pre-move path
        # to locate them.
        FrameworkTreeService.rebuild_subtree(node, old_path=old_path)

        return node

    @staticmethod
    def get_descendant_ids(node):
        """
        Return IDs of all descendants of a node.

        Uses the materialized path to avoid recursively querying
        every child.
        """

        if not node.path:
            return []

        return list(
            FrameworkNode.objects
            .filter(
                framework_version_id=node.framework_version_id,
                path__startswith=node.path,
            )
            .exclude(pk=node.pk)
            .values_list("pk", flat=True)
        )

    @staticmethod
    @transaction.atomic
    def rebuild_subtree(node, old_path=None):
        """
        Recalculate depth and path for a node and all descendants.

        The entire subtree is loaded once and rebuilt in memory,
        avoiding one database query per child.

        Args:
            node: The node whose subtree should be rebuilt. Its own
                depth/path are (re)calculated from its current
                `parent`.
            old_path: The node's materialized path *before* this
                change (e.g. before a move). Descendants still carry
                paths built from this prefix, so it's what we must
                query on to find them. If not provided, falls back to
                the node's current path (correct for calling this
                right after `create_node`, where nothing has moved).
        """

        # Determine which path prefix identifies the existing
        # descendants in the database.
        lookup_path = old_path if old_path is not None else node.path

        # Make sure the current node has correct metadata.
        node.calculate_tree_metadata()

        FrameworkNode.objects.filter(pk=node.pk).update(
            depth=node.depth,
            path=node.path,
        )

        if not lookup_path:
            return

        # Load descendants belonging to the same framework version,
        # found via their OLD path prefix.
        descendants = list(
            FrameworkNode.objects
            .filter(
                framework_version_id=node.framework_version_id,
                path__startswith=lookup_path,
            )
            .exclude(pk=node.pk)
        )

        if not descendants:
            return

        # Build an in-memory parent -> children structure.
        children_by_parent = {}

        for descendant in descendants:
            children_by_parent.setdefault(
                descendant.parent_id,
                [],
            ).append(descendant)

        # Deterministic ordering for every sibling group.
        for children in children_by_parent.values():
            children.sort(
                key=lambda child: (
                    child.display_order,
                    child.code,
                )
            )

        nodes_to_update = []
        now = timezone.now()

        # Traverse the subtree from the moved node.
        stack = [
            (
                node,
                children_by_parent.get(node.pk, []),
            )
        ]

        while stack:

            parent_node, children = stack.pop()

            for child in reversed(children):

                child.depth = parent_node.depth + 1
                child.path = (
                    f"{parent_node.path}{child.code}/"
                )
                child.updated_at = now

                nodes_to_update.append(child)

                grandchildren = children_by_parent.get(
                    child.pk,
                    [],
                )

                stack.append(
                    (
                        child,
                        grandchildren,
                    )
                )

        if nodes_to_update:
            FrameworkNode.objects.bulk_update(
                nodes_to_update,
                fields=[
                    "depth",
                    "path",
                    "updated_at",
                ],
            )

    @staticmethod
    def get_tree(framework_version):
        """
        Return the complete active framework tree in deterministic
        hierarchical order.

        Ordering rules:

            1. Parent before children.
            2. Siblings ordered by display_order.
            3. Code is used as a deterministic tie-breaker.

        Returns:
            list[FrameworkNode]
        """

        nodes = list(
            FrameworkNode.objects
            .filter(
                framework_version_id=framework_version.id,
                is_active=True,
            )
            .select_related(
                "framework_version",
                "parent",
            )
        )

        children_by_parent = {}

        for node in nodes:
            children_by_parent.setdefault(
                node.parent_id,
                [],
            ).append(node)

        # Deterministic sibling ordering.
        for children in children_by_parent.values():
            children.sort(
                key=lambda node: (
                    node.display_order,
                    node.code,
                )
            )

        ordered_nodes = []

        def traverse(parent_id):
            children = children_by_parent.get(
                parent_id,
                [],
            )

            for child in children:
                ordered_nodes.append(child)
                traverse(child.pk)

        # Start from root nodes.
        traverse(None)

        return ordered_nodes

    @staticmethod
    def get_root_nodes(framework_version):
        """
        Return active root nodes for a framework version.

        Root nodes have no parent.
        """

        return (
            FrameworkNode.objects
            .filter(
                framework_version_id=framework_version.id,
                parent__isnull=True,
                is_active=True,
            )
            .order_by(
                "display_order",
                "code",
            )
        )