from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.frameworks.models import (
    Framework,
    FrameworkVersion,
    FrameworkNode,
    DatapointMapping,
)

from apps.datapoints.models import (
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    CollectionLevel,
    CollectionFrequency,
)

from apps.modules.models import Module


class M4TestDataMixin:

    def create_module(self):
        return Module.objects.get_or_create(
            code="energy",
            defaults={
                "name": "Energy",
                "description": "Energy module",
                "esg_pillar": "E",
                "icon": "zap",
                "is_core": False,
                "is_enabled": True,
                "display_order": 1,
            },
        )[0]

    def create_category(self, module):
        return DatapointCategory.objects.get_or_create(
            code="TEST_ENERGY_CATEGORY",
            defaults={
                "name": "Test Energy Category",
                "description": "Test category for M7 tests",
                "module": module,
                "esg_pillar": "E",
                "display_order": 1,
                "is_active": True,
            },
        )[0]

    def create_datapoint(
        self,
        code="ENERGY_CONSUMPTION_TEST",
        label="Energy Consumption Test",
        data_type=DatapointDataType.DECIMAL,
        is_active=True,
    ):
        module = self.create_module()

        category = self.create_category(module)

        return Datapoint.objects.create(
            code=code,
            category=category,
            module=module,
            label=label,
            description="Test datapoint",
            data_type=data_type,
            collection_level=CollectionLevel.COMPANY,
            frequency=CollectionFrequency.ANNUAL,
            is_required=False,
            display_order=1,
            is_active=is_active,
        )


class FrameworkModelTests(TestCase):

    def test_create_framework(self):
        framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
            description="GRI Framework",
            is_enabled=True,
        )

        self.assertEqual(framework.code, "GRI")
        self.assertEqual(
            framework.name,
            "Global Reporting Initiative",
        )
        self.assertTrue(framework.is_enabled)

    def test_framework_code_must_be_unique(self):
        Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        with self.assertRaises(IntegrityError):
            Framework.objects.create(
                code="GRI",
                name="Another Framework",
            )

    def test_framework_string_representation(self):
        framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.assertEqual(
            str(framework),
            "GRI - Global Reporting Initiative",
        )


class FrameworkVersionModelTests(TestCase):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

    def test_create_framework_version(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            version_name="GRI Standards 2021",
            is_active=True,
            is_default=True,
        )

        self.assertEqual(
            version.framework,
            self.framework,
        )

        self.assertEqual(
            version.version_code,
            "2021",
        )

        self.assertTrue(version.is_active)
        self.assertTrue(version.is_default)

    def test_valid_effective_date_range(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            effective_from=date(2021, 1, 1),
            effective_to=date(2021, 12, 31),
        )

        self.assertEqual(version.effective_from, date(2021, 1, 1))

    def test_effective_from_after_effective_to_is_rejected(self):
        with self.assertRaises(ValidationError) as context:
            FrameworkVersion.objects.create(
                framework=self.framework,
                version_code="2021",
                effective_from=date(2022, 1, 1),
                effective_to=date(2021, 12, 31),
            )

        self.assertIn("effective_to", context.exception.message_dict)

    def test_equal_effective_dates_are_accepted(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            effective_from=date(2021, 1, 1),
            effective_to=date(2021, 1, 1),
        )

        self.assertEqual(version.effective_from, version.effective_to)

    def test_valid_published_at_before_effective_from(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            published_at=date(2020, 12, 1),
            effective_from=date(2021, 1, 1),
        )

        self.assertEqual(version.published_at, date(2020, 12, 1))

    def test_published_at_after_effective_from_is_rejected(self):
        with self.assertRaises(ValidationError) as context:
            FrameworkVersion.objects.create(
                framework=self.framework,
                version_code="2021",
                published_at=date(2021, 2, 1),
                effective_from=date(2021, 1, 1),
            )

        self.assertIn("published_at", context.exception.message_dict)

    def test_default_active_version_is_accepted(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            is_active=True,
            is_default=True,
        )

        self.assertTrue(version.is_default)

    def test_default_inactive_version_is_rejected(self):
        with self.assertRaises(ValidationError) as context:
            FrameworkVersion.objects.create(
                framework=self.framework,
                version_code="2021",
                is_active=False,
                is_default=True,
            )

        self.assertIn("is_default", context.exception.message_dict)

    def test_framework_version_code_unique_per_framework(self):
        FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

        with self.assertRaises(ValidationError):
            FrameworkVersion.objects.create(
                framework=self.framework,
                version_code="2021",
            )

    def test_only_one_default_version_per_framework(self):
        FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            is_default=True,
        )

        with self.assertRaises(ValidationError):
            FrameworkVersion.objects.create(
                framework=self.framework,
                version_code="2022",
                is_default=True,
            )

    def test_same_version_code_allowed_for_different_frameworks(self):
        other_framework = Framework.objects.create(
            code="BRSR",
            name="BRSR",
        )

        FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

        version = FrameworkVersion.objects.create(
            framework=other_framework,
            version_code="2021",
        )

        self.assertEqual(
            version.version_code,
            "2021",
        )


class FrameworkNodeModelTests(TestCase):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

    def test_create_root_node(self):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
        )

        self.assertEqual(node.depth, 0)
        self.assertEqual(
            node.path,
            "/GRI-300/",
        )

    def test_create_child_node(self):
        parent = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
        )

        child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=parent,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
        )

        self.assertEqual(child.depth, 1)

        self.assertEqual(
            child.path,
            "/GRI-300/GRI-302/",
        )

    def test_create_grandchild_node(self):
        parent = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=parent,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
        )

        grandchild = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=child,
            code="302-1",
            title="Energy consumption",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
        )

        self.assertEqual(
            grandchild.depth,
            2,
        )

        self.assertEqual(
            grandchild.path,
            "/GRI-300/GRI-302/302-1/",
        )

    def test_node_cannot_be_its_own_parent(self):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        node.parent = node

        with self.assertRaises(ValidationError):
            node.save()

    def test_parent_must_belong_to_same_framework_version(self):
        other_framework = Framework.objects.create(
            code="BRSR",
            name="BRSR",
        )

        other_version = FrameworkVersion.objects.create(
            framework=other_framework,
            version_code="2023",
        )

        parent = FrameworkNode.objects.create(
            framework_version=other_version,
            code="BRSR-1",
            title="BRSR Section",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        node = FrameworkNode(
            framework_version=self.version,
            parent=parent,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        with self.assertRaises(ValidationError):
            node.save()

    def test_node_code_must_be_unique_per_framework_version(self):
        FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        with self.assertRaises(ValidationError):
            FrameworkNode.objects.create(
                framework_version=self.version,
                code="GRI-300",
                title="Duplicate",
                node_type=FrameworkNode.NodeType.SECTION,
            )

    def test_same_node_code_allowed_in_different_versions(self):
        other_version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2022",
        )

        FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        node = FrameworkNode.objects.create(
            framework_version=other_version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        self.assertEqual(
            node.code,
            "GRI-300",
        )

    def test_moving_node_updates_descendant_metadata(self):
        parent_1 = FrameworkNode.objects.create(
            framework_version=self.version,
            code="ROOT-1",
            title="Root 1",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        parent_2 = FrameworkNode.objects.create(
            framework_version=self.version,
            code="ROOT-2",
            title="Root 2",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=parent_1,
            code="CHILD",
            title="Child",
            node_type=FrameworkNode.NodeType.SUBSECTION,
        )

        grandchild = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=child,
            code="GRANDCHILD",
            title="Grandchild",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
        )

        child.parent = parent_2
        child.save()

        child.refresh_from_db()
        grandchild.refresh_from_db()

        self.assertEqual(
            child.depth,
            1,
        )

        self.assertEqual(
            child.path,
            "/ROOT-2/CHILD/",
        )

        self.assertEqual(
            grandchild.depth,
            2,
        )

        self.assertEqual(
            grandchild.path,
            "/ROOT-2/CHILD/GRANDCHILD/",
        )

    def test_node_string_representation(self):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
        )

        self.assertEqual(
            str(node),
            "GRI-302 - Energy",
        )


class DatapointMappingModelTests(
    M4TestDataMixin,
    TestCase,
):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

        self.node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="302-1",
            title="Energy consumption",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            is_active=True,
        )

        self.datapoint = self.create_datapoint()

    def test_create_mapping(self):
        mapping = DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            mapping_type=DatapointMapping.MappingType.DIRECT,
            aggregation=DatapointMapping.Aggregation.NONE,
        )

        self.assertEqual(
            mapping.framework_node,
            self.node,
        )

        self.assertEqual(
            mapping.datapoint,
            self.datapoint,
        )

    def test_inactive_node_cannot_be_mapped(self):
        self.node.is_active = False
        self.node.save()

        mapping = DatapointMapping(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.assertRaises(ValidationError):
            mapping.save()

    def test_inactive_datapoint_cannot_be_mapped(self):
        self.datapoint.is_active = False
        self.datapoint.save()

        mapping = DatapointMapping(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.assertRaises(ValidationError):
            mapping.save()

    def test_same_node_and_datapoint_mapping_not_allowed(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.assertRaises(ValidationError):
            DatapointMapping.objects.create(
                framework_node=self.node,
                datapoint=self.datapoint,
            )

    def test_only_one_primary_mapping_per_node(self):
        datapoint_2 = self.create_datapoint(
            code="ENERGY_CONSUMPTION_TEST_2",
            label="Energy Consumption Test 2",
        )

        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            is_primary=True,
        )

        with self.assertRaises(ValidationError):
            DatapointMapping.objects.create(
                framework_node=self.node,
                datapoint=datapoint_2,
                is_primary=True,
            )

    def test_multiple_non_primary_mappings_allowed(self):
        datapoint_2 = self.create_datapoint(
            code="ENERGY_CONSUMPTION_TEST_2",
            label="Energy Consumption Test 2",
        )

        mapping_1 = DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            is_primary=False,
        )

        mapping_2 = DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=datapoint_2,
            is_primary=False,
        )

        self.assertIsNotNone(mapping_1.pk)
        self.assertIsNotNone(mapping_2.pk)

    def test_mapping_string_representation(self):
        mapping = DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        self.assertEqual(
            str(mapping),
            "302-1 -> ENERGY_CONSUMPTION_TEST",
        )
