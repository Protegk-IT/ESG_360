from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import (
    Permission,
    Role,
    UserRoleAssignment,
)

from apps.frameworks.models import (
    DatapointMapping,
    Framework,
    FrameworkNode,
    FrameworkVersion,
)

from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
)
from apps.modules.models import Module


User = get_user_model()


class FrameworkAPITests(APITestCase):
    """
    API tests for the M7 Framework module.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="framework_test_user",
            email="framework_test@example.com",
            password="testpass123",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.framework = Framework.objects.create(
            code="GRI",
            name="Global Reporting Initiative",
            description="GRI Standards",
            is_enabled=True,
        )

        self.version = FrameworkVersion.objects.create(
            framework=self.framework,
            version_code="2021",
            version_name="GRI Standards 2021",
            is_active=True,
            is_default=True,
        )

        self.manage_permission, _ = Permission.objects.get_or_create(
            code="framework_mapping.manage",
            defaults={
                "name": "Manage framework mappings",
                "module_code": "framework_mapping",
                "action": "MANAGE",
            },
        )

    def create_datapoint(self, code="ENERGY_TOTAL"):
        module, _ = Module.objects.get_or_create(
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
        )
        category, _ = DatapointCategory.objects.get_or_create(
            code="TEST_ENERGY_CATEGORY",
            defaults={
                "name": "Test Energy Category",
                "module": module,
                "esg_pillar": "E",
                "display_order": 1,
                "is_active": True,
            },
        )

        return Datapoint.objects.create(
            code=code,
            category=category,
            module=module,
            label="Total Energy",
            data_type="DECIMAL",
            collection_level=CollectionLevel.COMPANY,
            frequency=CollectionFrequency.ANNUAL,
            is_active=True,
        )

    # ------------------------------------------------------------------
    # RBAC TEST HELPERS
    # ------------------------------------------------------------------

    def grant_framework_mapping_manage(self):
        """
        Give the current test user the real
        framework_mapping.manage capability through
        the actual RBAC data model.
        """

        role, _ = Role.objects.get_or_create(
            role_code="m7_test_admin",
            defaults={
                "role_name": "M7 Test Admin",
                "is_active": True,
            },
        )

        role.is_active = True
        role.save(
            update_fields=["is_active"]
        )

        role.permissions.add(self.manage_permission)

        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
            is_active=True,
        )

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    def test_framework_list_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse("frameworks:framework-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_authenticated_user_can_read_frameworks(self):
        response = self.client.get(
            reverse("frameworks:framework-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # FRAMEWORK READ
    # ------------------------------------------------------------------

    def test_framework_list(self):
        response = self.client.get(
            reverse("frameworks:framework-list")
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

    def test_framework_search(self):
        response = self.client.get(
            reverse("frameworks:framework-list"),
            {"search": "GRI"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_framework_enabled_filter(self):
        response = self.client.get(
            reverse("frameworks:framework-list"),
            {"is_enabled": "true"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_framework_detail(self):
        response = self.client.get(
            reverse(
                "frameworks:framework-detail",
                args=[self.framework.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["code"],
            "GRI",
        )

    # ------------------------------------------------------------------
    # FRAMEWORK ADMINISTRATIVE WRITE RBAC
    # ------------------------------------------------------------------

    def test_framework_create_requires_manage_permission(self):
        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
                "is_enabled": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_framework_create_allowed_with_manage_permission(self):
        self.grant_framework_mapping_manage()

        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
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
                code="BRSR"
            ).exists()
        )

    def test_framework_update_requires_manage_permission(self):
        response = self.client.patch(
            reverse(
                "frameworks:framework-detail",
                args=[self.framework.id],
            ),
            {
                "name": "Updated GRI",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_framework_update_allowed_with_manage_permission(self):
        self.grant_framework_mapping_manage()

        response = self.client.patch(
            reverse(
                "frameworks:framework-detail",
                args=[self.framework.id],
            ),
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

    def test_framework_delete_requires_manage_permission(self):
        response = self.client.delete(
            reverse(
                "frameworks:framework-detail",
                args=[self.framework.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_framework_delete_allowed_with_manage_permission(self):
        self.grant_framework_mapping_manage()

        framework = Framework.objects.create(
            code="BRSR",
            name="Business Responsibility and Sustainability Report",
        )

        response = self.client.delete(
            reverse(
                "frameworks:framework-detail",
                args=[framework.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

    # ------------------------------------------------------------------
    # FRAMEWORK VERSION
    # ------------------------------------------------------------------

    def test_version_list_authenticated(self):
        response = self.client.get(
            reverse(
                "frameworks:framework-version-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_version_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "frameworks:framework-version-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_version_create_requires_manage_permission(self):
        response = self.client.post(
            reverse(
                "frameworks:framework-version-list"
            ),
            {
                "framework": str(
                    self.framework.id
                ),
                "version_code": "2022",
                "version_name": "GRI Standards 2022",
                "is_active": True,
                "is_default": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_version_create_allowed_with_manage_permission(
        self,
    ):
        self.grant_framework_mapping_manage()

        response = self.client.post(
            reverse(
                "frameworks:framework-version-list"
            ),
            {
                "framework": str(
                    self.framework.id
                ),
                "version_code": "2022",
                "version_name": "GRI Standards 2022",
                "is_active": True,
                "is_default": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # FRAMEWORK NODE
    # ------------------------------------------------------------------

    def test_node_list_authenticated(self):
        FrameworkNode.objects.create(
            framework_version=self.version,
            code="ROOT",
            title="Root",
            node_type="SECTION",
            display_order=1,
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "frameworks:framework-node-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_node_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "frameworks:framework-node-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_node_create_requires_manage_permission(self):
        response = self.client.post(
            reverse(
                "frameworks:framework-node-list"
            ),
            {
                "framework_version": str(
                    self.version.id
                ),
                "code": "ROOT",
                "title": "Root",
                "node_type": "SECTION",
                "display_order": 1,
                "is_answerable": False,
                "is_core": True,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_node_create_allowed_with_manage_permission(
        self,
    ):
        self.grant_framework_mapping_manage()

        response = self.client.post(
            reverse(
                "frameworks:framework-node-list"
            ),
            {
                "framework_version": str(
                    self.version.id
                ),
                "code": "ROOT",
                "title": "Root",
                "node_type": "SECTION",
                "display_order": 1,
                "is_answerable": False,
                "is_core": True,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # FRAMEWORK TREE
    # ------------------------------------------------------------------

    def test_framework_tree_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "frameworks:framework-tree",
                args=[self.version.id],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_authenticated_user_can_read_framework_tree(
        self,
    ):
        root = FrameworkNode.objects.create(
            framework_version=self.version,
            code="ROOT",
            title="Root",
            node_type="SECTION",
            display_order=1,
            is_active=True,
        )

        FrameworkNode.objects.create(
            framework_version=self.version,
            parent=root,
            code="CHILD",
            title="Child",
            node_type="DISCLOSURE",
            display_order=1,
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "frameworks:framework-tree",
                args=[self.version.id],
            )
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
            response.data["version"]["code"],
            "2021",
        )

        self.assertEqual(
            len(response.data["tree"]),
            1,
        )

        self.assertEqual(
            response.data["tree"][0]["code"],
            "ROOT",
        )

        self.assertEqual(
            len(
                response.data["tree"][0]["children"]
            ),
            1,
        )

    # ------------------------------------------------------------------
    # DATAPOINT MAPPING
    # ------------------------------------------------------------------

    def test_mapping_list_authenticated(self):
        response = self.client.get(
            reverse(
                "frameworks:mapping-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_mapping_requires_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "frameworks:mapping-list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_mapping_create_requires_manage_permission(
        self,
    ):
        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="302-1",
            title="Energy Consumption",
            node_type="DISCLOSURE",
            display_order=1,
            is_active=True,
        )

        datapoint = self.create_datapoint()

        response = self.client.post(
            reverse(
                "frameworks:mapping-list"
            ),
            {
                "framework_node": str(
                    node.id
                ),
                "datapoint": str(
                    datapoint.id
                ),
                "mapping_type": "DIRECT",
                "aggregation": "NONE",
                "is_primary": True,
                "confidence": "CONFIRMED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_mapping_create_allowed_with_manage_permission(
        self,
    ):
        self.grant_framework_mapping_manage()

        node = FrameworkNode.objects.create(
            framework_version=self.version,
            code="302-1",
            title="Energy Consumption",
            node_type="DISCLOSURE",
            display_order=1,
            is_active=True,
        )

        datapoint = self.create_datapoint()

        response = self.client.post(
            reverse(
                "frameworks:mapping-list"
            ),
            {
                "framework_node": str(
                    node.id
                ),
                "datapoint": str(
                    datapoint.id
                ),
                "mapping_type": "DIRECT",
                "aggregation": "NONE",
                "is_primary": True,
                "confidence": "CONFIRMED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            DatapointMapping.objects.filter(
                framework_node=node,
                datapoint=datapoint,
            ).exists()
        )

    # ------------------------------------------------------------------
    # REAL RBAC DATE VALIDITY
    # ------------------------------------------------------------------

    def test_expired_manage_assignment_is_rejected(self):
        from django.utils import timezone
        from datetime import timedelta

        role, _ = Role.objects.get_or_create(
            role_code="m7_expired_role",
            defaults={
                "role_name": "M7 Expired Role",
                "is_active": True,
            },
        )

        role.is_active = True
        role.save(
            update_fields=["is_active"]
        )

        role.permissions.add(self.manage_permission)

        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
            is_active=True,
            valid_to=(
                timezone.now().date()
                - timedelta(days=1)
            ),
        )

        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
                "is_enabled": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_inactive_manage_assignment_is_rejected(
        self,
    ):
        role, _ = Role.objects.get_or_create(
            role_code="m7_inactive_role",
            defaults={
                "role_name": "M7 Inactive Role",
                "is_active": True,
            },
        )

        role.is_active = True
        role.save(
            update_fields=["is_active"]
        )

        role.permissions.add(self.manage_permission)

        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
            is_active=False,
        )

        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
                "is_enabled": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_inactive_role_manage_assignment_is_rejected(
        self,
    ):
        role, _ = Role.objects.get_or_create(
            role_code="m7_inactive_role_definition",
            defaults={
                "role_name": "M7 Inactive Role Definition",
                "is_active": False,
            },
        )

        role.is_active = False
        role.save(
            update_fields=["is_active"]
        )

        role.permissions.add(self.manage_permission)

        UserRoleAssignment.objects.create(
            user=self.user,
            role=role,
            is_active=True,
        )

        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
                "is_enabled": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # ------------------------------------------------------------------
    # SUPERUSER
    # ------------------------------------------------------------------

    def test_superuser_can_perform_administrative_write(
        self,
    ):
        self.user.is_superuser = True
        self.user.save(
            update_fields=["is_superuser"]
        )

        response = self.client.post(
            reverse("frameworks:framework-list"),
            {
                "code": "BRSR",
                "name": "BRSR",
                "description": "BRSR framework",
                "is_enabled": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
