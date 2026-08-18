from django.core.management.base import BaseCommand
from django.db import transaction

from apps.frameworks.models import (
    Framework,
    FrameworkNode,
    FrameworkVersion,
)


class Command(BaseCommand):
    help = (
        "Create representative framework and framework-version "
        "tree data for development/testing."
    )

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "Starting framework seed..."
            )
        )

        framework = self.create_framework()

        version = self.create_version(
            framework=framework
        )

        self.create_tree(
            version=version
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Framework seed completed successfully."
            )
        )

    def create_framework(self):
        """
        Create or update the representative GRI framework.
        """

        framework, created = Framework.objects.update_or_create(
            code="GRI",
            defaults={
                "name": "Global Reporting Initiative",
                "description": (
                    "Representative framework record for "
                    "development and framework-tree testing."
                ),
                "is_enabled": True,
            },
        )

        if created:
            self.stdout.write(
                "Created framework: GRI"
            )
        else:
            self.stdout.write(
                "Framework already exists: GRI"
            )

        return framework

    def create_version(self, *, framework):
        """
        Create or update the representative GRI version.
        """

        version, created = FrameworkVersion.objects.update_or_create(
            framework=framework,
            version_code="GRI-2021",
            defaults={
                "version_name": "GRI 2021",
                "is_active": True,
                "is_default": True,
            },
        )

        if created:
            self.stdout.write(
                "Created version: GRI-2021"
            )
        else:
            self.stdout.write(
                "Version already exists: GRI-2021"
            )

        return version

    def create_tree(self, *, version):
        """
        Create a small representative multi-level framework tree.

        This is intentionally NOT the complete official framework
        content population.
        """

        universal_standards = self.create_node(
            version=version,
            parent=None,
            code="UNIVERSAL-STANDARDS",
            title="Universal Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
        )

        self.create_node(
            version=version,
            parent=universal_standards,
            code="ORGANIZATIONAL-PROFILE",
            title="Organizational Profile",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
        )

        self.create_node(
            version=version,
            parent=universal_standards,
            code="REPORTING-PRACTICES",
            title="Reporting Practices",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=2,
        )

        topic_standards = self.create_node(
            version=version,
            parent=None,
            code="TOPIC-STANDARDS",
            title="Topic Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=2,
        )

        gri_300 = self.create_node(
            version=version,
            parent=topic_standards,
            code="GRI-300",
            title="GRI 300 Series",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
        )

        gri_302 = self.create_node(
            version=version,
            parent=gri_300,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
        )

        self.create_node(
            version=version,
            parent=gri_302,
            code="302-1",
            title="Energy consumption",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            display_order=1,
            is_answerable=True,
            response_format="NUMERIC",
        )

        self.create_node(
            version=version,
            parent=gri_302,
            code="302-2",
            title="Energy consumption outside the organization",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            display_order=2,
            is_answerable=True,
            response_format="NUMERIC",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Representative framework tree created/updated."
            )
        )

    def create_node(
        self,
        *,
        version,
        parent,
        code,
        title,
        node_type,
        display_order,
        description="",
        instructions="",
        response_format="",
        is_answerable=False,
        is_core=False,
        is_active=True,
    ):
        """
        Create or update one framework node.

        Uniqueness is scoped to the framework version + code.
        """

        node, created = FrameworkNode.objects.update_or_create(
            framework_version=version,
            code=code,
            defaults={
                "parent": parent,
                "title": title,
                "description": description,
                "instructions": instructions,
                "node_type": node_type,
                "display_order": display_order,
                "response_format": response_format,
                "is_answerable": is_answerable,
                "is_core": is_core,
                "is_active": is_active,
            },
        )

        if created:
            self.stdout.write(
                f"  Created node: {code}"
            )
        else:
            self.stdout.write(
                f"  Updated node: {code}"
            )

        return node