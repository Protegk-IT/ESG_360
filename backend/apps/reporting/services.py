from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)


def freeze_report_run(report_run):
    """
    Freeze the current M7 framework structure for a ReportRun.

    Flow:

        ReportRun
            |
            | framework_version
            v
        FrameworkVersion
            |
            +--> Framework
            |
            +--> FrameworkNode
                    |
                    +--> DatapointMapping
                            |
                            +--> Datapoint

        The live M7 data is copied into immutable M8 snapshot
        records.

    The complete operation is transactional.

    If any part fails, the entire snapshot creation is rolled back.
    """

    if not isinstance(report_run, ReportRun):
        raise ValidationError(
            "freeze_report_run requires a ReportRun instance."
        )

    # --------------------------------------------------------------
    # 1. Reject re-freezing
    # --------------------------------------------------------------

    if report_run.is_frozen:
        raise ValidationError(
            "This report run has already been frozen."
        )

    # --------------------------------------------------------------
    # 2. Lock the ReportRun
    # --------------------------------------------------------------
    #
    # This prevents two concurrent freeze requests from both
    # attempting to freeze the same ReportRun.
    #

    with transaction.atomic():

        report_run = (
            ReportRun.objects
            .select_for_update()
            .select_related(
                "framework_version",
                "framework_version__framework",
                "reporting_period",
            )
            .get(pk=report_run.pk)
        )

        # ----------------------------------------------------------
        # 3. Check again after acquiring the database lock
        # ----------------------------------------------------------
        #
        # This second check is important for concurrent requests.
        #

        if report_run.is_frozen:
            raise ValidationError(
                "This report run has already been frozen."
            )

        framework_version = report_run.framework_version
        framework = framework_version.framework

        frozen_at = timezone.now()

        # ----------------------------------------------------------
        # 4. Create the framework snapshot
        # ----------------------------------------------------------

        snapshot = FrameworkSnapshot.objects.create(
            report_run=report_run,

            source_framework_id=framework.id,
            source_framework_version_id=framework_version.id,

            framework_code=framework.code,
            framework_name=framework.name,

            version_code=framework_version.version_code,
            version_name=framework_version.version_name,

            frozen_at=frozen_at,
        )

        # ----------------------------------------------------------
        # 5. Read the live M7 framework nodes
        # ----------------------------------------------------------
        #
        # Deterministic ordering is important.
        #
        # We order using the structural fields from M7:
        #
        #     path
        #     display_order
        #     code
        #     id
        #
        # This means the same M7 structure produces the same
        # snapshot ordering.
        #

        nodes = (
            framework_version.nodes
            .select_related("parent")
            .prefetch_related(
                "datapoint_mappings",
                "datapoint_mappings__datapoint",
            )
            .order_by(
                "path",
                "display_order",
                "code",
                "id",
            )
        )

                # ----------------------------------------------------------
        # 6. Create SnapshotNodes
        # ----------------------------------------------------------

        node_map = {}

        for node in nodes:
            snapshot_node = SnapshotNode.objects.create(
                snapshot=snapshot,
                source_node_id=node.id,
                code=node.code,
                title=node.title,
                description=node.description,
                instructions=node.instructions,
                node_type=node.node_type,
                display_order=node.display_order,
                depth=node.depth,
                path=node.path,
                response_format=node.response_format,
                is_answerable=node.is_answerable,
                is_core=node.is_core,
                is_active=node.is_active,
                metadata={},
            )

            node_map[node.id] = snapshot_node

        # ----------------------------------------------------------
        # 7. Establish parent relationships
        # ----------------------------------------------------------

        for node in nodes:

            if node.parent_id is None:
                continue

            snapshot_node = node_map[node.id]
            snapshot_parent = node_map.get(node.parent_id)

            if snapshot_parent is None:
                raise ValidationError(
                    (
                        "Framework snapshot cannot be created "
                        "because a node's parent is missing from "
                        "the selected framework version."
                    )
                )

            snapshot_node.parent = snapshot_parent

            # IMPORTANT:
            # Parent assignment happens during the controlled
            # freeze operation.
            #
            # We use QuerySet.update() here so we do not expose
            # a normal model save/update path for immutable
            # snapshot data.

            SnapshotNode.objects.filter(
                pk=snapshot_node.pk
            ).update(
                parent=snapshot_parent
            )

        # ----------------------------------------------------------
        # 8. Create SnapshotMappings
        # ----------------------------------------------------------
        #
        # M7 mappings are copied into M8.
        #
        # The historical snapshot stores the datapoint identity,
        # but does NOT store M5 answers or M6 calculated values.
        #

        for node in nodes:

            snapshot_node = node_map[node.id]

            mappings = sorted(
                node.datapoint_mappings.all(),
                key=lambda mapping: (
                    mapping.is_primary is not True,
                    mapping.datapoint.code,
                    mapping.id,
                ),
            )

            for display_order, mapping in enumerate(
                mappings
            ):

                datapoint = mapping.datapoint

                SnapshotMapping.objects.create(
                    snapshot_node=snapshot_node,

                    source_mapping_id=mapping.id,
                    source_datapoint_id=datapoint.id,

                    canonical_datapoint_code=datapoint.code,

                    mapping_type=mapping.mapping_type,
                    aggregation=mapping.aggregation,
                    transform_expression=(
                        mapping.transform_expression
                    ),
                    is_primary=mapping.is_primary,
                    confidence=mapping.confidence,
                    mapping_note=mapping.mapping_note,
                    reviewed_at=mapping.reviewed_at,

                    display_order=display_order,

                    metadata={},
                )

        # ----------------------------------------------------------
        # 9. Mark ReportRun as frozen
        # ----------------------------------------------------------

        report_run.status = ReportRun.Status.FROZEN
        report_run.snapshot_frozen_at = frozen_at

        report_run.save(
            update_fields=[
                "status",
                "snapshot_frozen_at",
                "updated_at",
            ]
        )

        # ----------------------------------------------------------
        # 10. Return the completed frozen ReportRun
        # ----------------------------------------------------------

        return report_run