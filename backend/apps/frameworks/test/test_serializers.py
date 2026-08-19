from django.test import TestCase

from apps.frameworks.models import (
    Framework,
    FrameworkVersion,
    FrameworkNode,
    DatapointMapping,
)

from apps.frameworks.serializers import (
    FrameworkSerializer,
    FrameworkVersionSerializer,
    FrameworkNodeSerializer,
    DatapointMappingSerializer,
)

from apps.datapoints.models import (
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    CollectionLevel,
    CollectionFrequency,
)

from apps.modules.models import Module


class DatapointTestMixin:

    def create_datapoint(
        self,
        code="ENERGY_SERIALIZER_TEST",
        label="Energy Serializer Test",
        data_type=DatapointDataType.DECIMAL,
        is_active=True,
    ):
        module = Module.objects.get_or_create(
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

        category = DatapointCategory.objects.create(
            code="SERIALIZER_ENERGY_CATEGORY",
            name="Serializer Energy Category",
            description="Serializer test category",
            module=module,
            esg_pillar="E",
            display_order=1,
            is_active=True,
        )

        return Datapoint.objects.create(
            code=code,
            category=category,
            module=module,
            label=label,
            description="Serializer test datapoint",
            data_type=data_type,
            collection_level=CollectionLevel.COMPANY,
            frequency=CollectionFrequency.ANNUAL,
            is_required=False,
            display_order=1,
            is_active=is_active,
        )


class FrameworkSerializerTests(TestCase):

    def test_framework_serializer_contains_expected_fields(self):
        framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
            description="GRI",
        )

        serializer = FrameworkSerializer(
            instance=framework
        )

        expected_fields = {
            "id",
            "code",
            "name",
            "description",
            "is_enabled",
            "created_at",
            "updated_at",
        }

        self.assertEqual(
            set(serializer.data.keys()),
            expected_fields,
        )

    def test_created_at_and_updated_at_are_read_only(self):
        serializer = FrameworkSerializer()

        self.assertTrue(
            serializer.fields["created_at"].read_only
        )

        self.assertTrue(
            serializer.fields["updated_at"].read_only
        )


class FrameworkVersionSerializerTests(TestCase):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

    def test_framework_code_is_returned(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

        serializer = FrameworkVersionSerializer(
            instance=version
        )

        self.assertEqual(
            serializer.data["framework_code"],
            "GRI",
        )

    def test_active_version_cannot_change_framework(self):
        other_framework = Framework.objects.create(
            code="BRSR",
            name="BRSR",
        )

        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            is_active=True,
        )

        serializer = FrameworkVersionSerializer(
            instance=version,
            data={
                "framework": str(other_framework.id),
            },
            partial=True,
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "framework",
            serializer.errors,
        )

    def test_active_version_cannot_change_version_code(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            is_active=True,
        )

        serializer = FrameworkVersionSerializer(
            instance=version,
            data={
                "version_code": "2022",
            },
            partial=True,
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "version_code",
            serializer.errors,
        )

    def test_inactive_version_can_change_version_code(self):
        version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            is_active=False,
        )

        serializer = FrameworkVersionSerializer(
            instance=version,
            data={
                "version_code": "2022",
            },
            partial=True,
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )


class FrameworkNodeSerializerTests(TestCase):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

    def test_parent_code_is_returned(self):
        parent = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=parent,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
        )

        serializer = FrameworkNodeSerializer(
            instance=child
        )

        self.assertEqual(
            serializer.data["parent_code"],
            "GRI-300",
        )

    def test_root_parent_code_is_null(self):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        serializer = FrameworkNodeSerializer(
            instance=node
        )

        self.assertIsNone(
            serializer.data["parent_code"]
        )

    def test_self_parent_is_rejected(self):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        serializer = FrameworkNodeSerializer(
            instance=node,
            data={
                "parent": str(node.id),
            },
            partial=True,
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "parent",
            serializer.errors,
        )

    def test_parent_from_different_version_is_rejected(self):
        other_version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2022",
        )

        parent = FrameworkNode.objects.create(
            framework_version=other_version,
            code="OTHER",
            title="Other",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        serializer = FrameworkNodeSerializer(
            instance=node,
            data={
                "parent": str(parent.id),
            },
            partial=True,
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "parent",
            serializer.errors,
        )

    def test_depth_and_path_are_read_only(self):
        serializer = FrameworkNodeSerializer()

        self.assertTrue(
            serializer.fields["depth"].read_only
        )

        self.assertTrue(
            serializer.fields["path"].read_only
        )


class FrameworkTreeNodeSerializerTests(TestCase):

    def setUp(self):
        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

    def test_children_are_serialized_recursively(self):
        root = FrameworkNode.objects.create(
            framework_version=self.version,
            code="ROOT",
            title="Root",
            node_type=FrameworkNode.NodeType.SECTION,
        )

        child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=root,
            code="CHILD",
            title="Child",
            node_type=FrameworkNode.NodeType.SUBSECTION,
        )

        children_map = {
            None: [root],
            root.pk: [child],
        }

        serializer = FrameworkNodeSerializer(
            instance=root
        )

        self.assertEqual(
            serializer.data["code"],
            "ROOT",
        )


class DatapointMappingSerializerTests(
    DatapointTestMixin,
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

    def test_mapping_serializer_returns_related_datapoint_information(self):
        mapping = DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        serializer = DatapointMappingSerializer(
            instance=mapping
        )

        self.assertEqual(
            serializer.data["framework_node_code"],
            "302-1",
        )

        self.assertEqual(
            serializer.data["framework_version_code"],
            "2021",
        )

        self.assertEqual(
            serializer.data["datapoint_code"],
            "ENERGY_SERIALIZER_TEST",
        )

        self.assertEqual(
            serializer.data["datapoint_label"],
            "Energy Serializer Test",
        )

        self.assertEqual(
            serializer.data["datapoint_data_type"],
            "DECIMAL",
        )

    def test_inactive_framework_node_is_rejected(self):
        self.node.is_active = False
        self.node.save()

        serializer = DatapointMappingSerializer(
            data={
                "framework_node": str(
                    self.node.id
                ),
                "datapoint": str(
                    self.datapoint.id
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "framework_node",
            serializer.errors,
        )

    def test_inactive_datapoint_is_rejected(self):
        self.datapoint.is_active = False
        self.datapoint.save()

        serializer = DatapointMappingSerializer(
            data={
                "framework_node": str(
                    self.node.id
                ),
                "datapoint": str(
                    self.datapoint.id
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "datapoint",
            serializer.errors,
        )

    def test_direct_mapping_cannot_use_aggregation(self):
        serializer = DatapointMappingSerializer(
            data={
                "framework_node": str(
                    self.node.id
                ),
                "datapoint": str(
                    self.datapoint.id
                ),
                "mapping_type": (
                    DatapointMapping.MappingType.DIRECT
                ),
                "aggregation": (
                    DatapointMapping.Aggregation.SUM
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "aggregation",
            serializer.errors,
        )

    def test_narrative_mapping_cannot_use_aggregation(self):
        serializer = DatapointMappingSerializer(
            data={
                "framework_node": str(
                    self.node.id
                ),
                "datapoint": str(
                    self.datapoint.id
                ),
                "mapping_type": (
                    DatapointMapping.MappingType.NARRATIVE
                ),
                "aggregation": (
                    DatapointMapping.Aggregation.SUM
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "aggregation",
            serializer.errors,
        )

    def test_direct_mapping_with_none_aggregation_is_valid(self):
        serializer = DatapointMappingSerializer(
            data={
                "framework_node": str(
                    self.node.id
                ),
                "datapoint": str(
                    self.datapoint.id
                ),
                "mapping_type": (
                    DatapointMapping.MappingType.DIRECT
                ),
                "aggregation": (
                    DatapointMapping.Aggregation.NONE
                ),
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )
