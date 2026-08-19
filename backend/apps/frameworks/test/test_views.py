import uuid
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

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


class DatapointTestMixin:

    def create_datapoint(
        self,
        code="ENERGY_API_TEST",
        label="Energy API Test",
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
            code=f"CATEGORY_{code}",
            name=f"Category {code}",
            description="API test category",
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
            description="API test datapoint",
            data_type=data_type,
            collection_level=CollectionLevel.COMPANY,
            frequency=CollectionFrequency.ANNUAL,
            is_required=False,
            display_order=1,
            is_active=is_active,
        )


class PermissionMockMixin:

    permission_patch = (
        "apps.accounts.permissions."
        "HasRolePermission.has_permission"
    )

    def enable_rbac(self):
        return patch(
            self.permission_patch,
            return_value=True,
        )


class FrameworkAPITests(
    PermissionMockMixin,
    APITestCase,
):

    def setUp(self):
        self.user = self.create_user()

        self.client.force_authenticate(
            user=self.user
        )

        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
            description="GRI Framework",
            is_enabled=True,
        )

        self.brsr = Framework.objects.create(
            code="BRSR",
            name="Business Responsibility and Sustainability Reporting",
            is_enabled=True,
        )

    def create_user(self):
        from apps.accounts.models import User

        return User.objects.create_user(
            username="framework_test_user",
            email="framework_test@example.com",
            password="testpassword",
        )

    def test_framework_list(self):
        with self.enable_rbac():
            url = "/api/frameworks/"

            response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsInstance(
            response.data,
            list,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

    def test_framework_search_by_code(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/",
                {
                    "search": "GRI",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["code"],
            "GRI",
        )

    def test_framework_search_by_name(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/",
                {
                    "search": "Business Responsibility",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["code"],
            "BRSR",
        )

    def test_framework_filter_is_enabled(self):
        self.brsr.is_enabled = False
        self.brsr.save()

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/",
                {
                    "is_enabled": "false",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["code"],
            "BRSR",
        )

    def test_framework_detail(self):
        with self.enable_rbac():
            response = self.client.get(
                f"/api/frameworks/{self.framework.id}/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["code"],
            "GRI",
        )

    def test_framework_create(self):
        with self.enable_rbac():
            response = self.client.post(
                "/api/frameworks/",
                {
                    "code": "GHG",
                    "name": "GHG Protocol",
                    "description": "GHG Protocol",
                    "is_enabled": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Framework.objects.filter(
                code="GHG"
            ).exists()
        )

    def test_framework_update(self):
        with self.enable_rbac():
            response = self.client.patch(
                f"/api/frameworks/{self.framework.id}/",
                {
                    "name": "Updated GRI",
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.framework.refresh_from_db()

        self.assertEqual(
            self.framework.name,
            "Updated GRI",
        )


class FrameworkVersionAPITests(
    PermissionMockMixin,
    APITestCase,
):

    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="version_test_user",
            email="version_test@example.com",
            password="testpassword",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version_2021 = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            version_name="GRI 2021",
            is_active=True,
            is_default=True,
        )

        self.version_2022 = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2022",
            version_name="GRI 2022",
            is_active=False,
            is_default=False,
        )

    def test_version_list(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/versions/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsInstance(
            response.data,
            list,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

    def test_filter_versions_by_framework(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/versions/",
                {
                    "framework": str(
                        self.framework.id
                    ),
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

    def test_filter_versions_by_active_state(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/versions/",
                {
                    "is_active": "true",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["version_code"],
            "2021",
        )

    def test_filter_versions_by_default(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/versions/",
                {
                    "is_default": "true",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_search_versions(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/versions/",
                {
                    "search": "2021",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )


class FrameworkNodeAPITests(
    PermissionMockMixin,
    APITestCase,
):

    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="node_test_user",
            email="node_test@example.com",
            password="testpassword",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
        )

        self.root = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
        )

        self.child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=self.root,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
        )

        self.disclosure = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=self.child,
            code="302-1",
            title="Energy consumption",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            display_order=1,
        )

    def test_node_list(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/nodes/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsInstance(
            response.data,
            list,
        )

        self.assertEqual(
            len(response.data),
            3,
        )

    def test_filter_nodes_by_framework_version(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/nodes/",
                {
                    "framework_version": str(
                        self.version.id
                    ),
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            3,
        )

    def test_filter_nodes_by_code(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/nodes/",
                {
                    "code": "302",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

    def test_filter_nodes_by_node_type(self):
        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/nodes/",
                {
                    "node_type": "DISCLOSURE",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["code"],
            "302-1",
        )

    def test_filter_nodes_by_active_state(self):
        self.disclosure.is_active = False
        self.disclosure.save()

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/nodes/",
                {
                    "is_active": "true",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )


class FrameworkTreeAPITests(
    PermissionMockMixin,
    APITestCase,
):

    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="tree_test_user",
            email="tree_test@example.com",
            password="testpassword",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            version_name="GRI 2021",
        )

        self.root = FrameworkNode.objects.create(
            framework_version=self.version,
            code="GRI-300",
            title="Environmental Standards",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=1,
            is_active=True,
        )

        self.child = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=self.root,
            code="GRI-302",
            title="Energy",
            node_type=FrameworkNode.NodeType.SUBSECTION,
            display_order=1,
            is_active=True,
        )

        self.disclosure = FrameworkNode.objects.create(
            framework_version=self.version,
            parent=self.child,
            code="302-1",
            title="Energy consumption",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            display_order=1,
            is_active=True,
        )

        self.inactive_node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="INACTIVE",
            title="Inactive Node",
            node_type=FrameworkNode.NodeType.SECTION,
            display_order=99,
            is_active=False,
        )

    def tree_url(self):
        return (
            f"/api/frameworks/versions/"
            f"{self.version.id}/tree/"
        )

    def test_framework_tree_returns_framework_information(self):
        with self.enable_rbac():
            response = self.client.get(
                self.tree_url()
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["framework"]["code"],
            "GRI",
        )

        self.assertEqual(
            response.data["framework"]["name"],
            "Global Reporting Initiative",
        )

        self.assertEqual(
            response.data["version"]["code"],
            "2021",
        )

    def test_framework_tree_contains_nested_children(self):
        with self.enable_rbac():
            response = self.client.get(
                self.tree_url()
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        tree = response.data["tree"]

        self.assertEqual(
            len(tree),
            1,
        )

        self.assertEqual(
            tree[0]["code"],
            "GRI-300",
        )

        self.assertEqual(
            tree[0]["children"][0]["code"],
            "GRI-302",
        )

        self.assertEqual(
            tree[0]["children"][0]["children"][0]["code"],
            "302-1",
        )

    def test_framework_tree_excludes_inactive_nodes(self):
        with self.enable_rbac():
            response = self.client.get(
                self.tree_url()
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        tree = response.data["tree"]

        codes = []

        def collect_codes(nodes):
            for node in nodes:
                codes.append(node["code"])
                collect_codes(
                    node["children"]
                )

        collect_codes(tree)

        self.assertNotIn(
            "INACTIVE",
            codes,
        )

    def test_framework_tree_invalid_version_returns_404(self):
        invalid_version_id = uuid.uuid4()

        with self.enable_rbac():
            response = self.client.get(
                f"/api/frameworks/versions/"
                f"{invalid_version_id}/tree/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class DatapointMappingAPITests(
    DatapointTestMixin,
    PermissionMockMixin,
    APITestCase,
):

    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="mapping_test_user",
            email="mapping_test@example.com",
            password="testpassword",
        )

        self.client.force_authenticate(
            user=self.user
        )

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

        self.node_2 = FrameworkNode.objects.create(
            framework_version=self.version,
            code="302-2",
            title="Energy intensity",
            node_type=FrameworkNode.NodeType.DISCLOSURE,
            is_active=True,
        )

        self.datapoint = self.create_datapoint(
            code="ENERGY_API_TEST_1",
            label="Energy API Test 1",
        )

        self.datapoint_2 = self.create_datapoint(
            code="ENERGY_API_TEST_2",
            label="Energy API Test 2",
        )

    def test_mapping_list(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/"
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsInstance(
            response.data,
            list,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_create_mapping(self):
        with self.enable_rbac():
            response = self.client.post(
                "/api/frameworks/mappings/",
                {
                    "framework_node": str(
                        self.node.id
                    ),
                    "datapoint": str(
                        self.datapoint.id
                    ),
                    "mapping_type": "DIRECT",
                    "aggregation": "NONE",
                    "is_primary": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            DatapointMapping.objects.filter(
                framework_node=self.node,
                datapoint=self.datapoint,
            ).exists()
        )

    def test_filter_mapping_by_framework_node(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "framework_node": str(
                        self.node.id
                    ),
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_filter_mapping_by_framework_version(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "framework_version": str(
                        self.version.id
                    ),
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_filter_mapping_by_datapoint(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "datapoint": str(
                        self.datapoint.id
                    ),
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_filter_mapping_by_mapping_type(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            mapping_type="DIRECT",
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "mapping_type": "DIRECT",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_filter_mapping_by_confidence(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            confidence="CONFIRMED",
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "confidence": "CONFIRMED",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_filter_mapping_by_primary_state(self):
        DatapointMapping.objects.create(
            framework_node=self.node,
            datapoint=self.datapoint,
            is_primary=True,
        )

        with self.enable_rbac():
            response = self.client.get(
                "/api/frameworks/mappings/",
                {
                    "is_primary": "true",
                },
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )
