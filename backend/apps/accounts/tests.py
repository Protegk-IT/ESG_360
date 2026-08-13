from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User, UserDepartment, UserRoleAssignment
from apps.accounts.serializers import RoleSerializer, UserSerializer
from apps.accounts.services.rbac import RBACService
from apps.accounts.constants import PERMISSIONS, ROLE_PERMISSIONS
from apps.companies.models import Company, Department
from apps.organizations.models import OrgNode


class RBACScopeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Scope Co",
            company_code="SCOPE",
            contact_person="Owner",
            email="owner@example.com",
            mobile_number="9999999999",
        )
        self.root = OrgNode.objects.get(company=self.company, parent__isnull=True)
        self.site_a = OrgNode.objects.create(
            company=self.company,
            parent=self.root,
            node_type="BUSINESS_UNIT",
            code="SITE-A",
            name="Site A",
        )
        self.site_a_child = OrgNode.objects.create(
            company=self.company,
            parent=self.site_a,
            node_type="FACILITY",
            code="SITE-A-CHILD",
            name="Site A Child",
        )
        self.site_b = OrgNode.objects.create(
            company=self.company,
            parent=self.root,
            node_type="BUSINESS_UNIT",
            code="SITE-B",
            name="Site B",
        )
        self.user = User.objects.create_user(username="rahul", password="safe-password-123")

        self.enter_permission = Permission.objects.create(
            code="data.enter", name="Enter data", module_code="data", action="EDIT"
        )
        self.approve_permission = Permission.objects.create(
            code="data.approve", name="Approve data", module_code="data", action="APPROVE"
        )
        self.org_view_permission = Permission.objects.create(
            code="organization.view", name="View organization", module_code="organization", action="VIEW"
        )
        self.org_create_permission = Permission.objects.create(
            code="organization.create", name="Create organization", module_code="organization", action="CREATE"
        )
        self.entry_role = Role.objects.create(role_code="entry", role_name="Entry")
        self.entry_role.permissions.add(self.enter_permission, self.org_view_permission)
        self.reviewer_role = Role.objects.create(role_code="reviewer", role_name="Reviewer")
        self.reviewer_role.permissions.add(self.approve_permission)

    def test_permissions_resolve_against_the_role_assignment_scope(self):
        """A user's enter and approve permissions can safely apply to different sites."""
        UserRoleAssignment.objects.create(user=self.user, role=self.entry_role, org_node=self.site_a)
        UserRoleAssignment.objects.create(user=self.user, role=self.reviewer_role, org_node=self.site_b)

        entered_nodes = set(RBACService.get_allowed_org_nodes(self.user, "data.enter", module_code="data"))
        approved_nodes = set(RBACService.get_allowed_org_nodes(self.user, "data.approve", module_code="data"))

        self.assertEqual(entered_nodes, {self.site_a.id, self.site_a_child.id})
        self.assertEqual(approved_nodes, {self.site_b.id})
        self.assertTrue(RBACService.has_permission(self.user, "data.enter"))
        self.assertTrue(RBACService.has_permission(self.user, "data.approve"))

    def test_module_restrictions_and_expired_assignments_grant_nothing(self):
        assignment = UserRoleAssignment.objects.create(
            user=self.user,
            role=self.entry_role,
            org_node=self.site_a,
            module_code="other",
        )
        self.assertFalse(RBACService.has_permission(self.user, "data.enter"))
        self.assertEqual(RBACService.get_allowed_org_nodes(self.user, "data.enter", module_code="data"), [])

        assignment.module_code = "data"
        assignment.valid_to = timezone.localdate() - timedelta(days=1)
        assignment.save()
        self.assertFalse(RBACService.has_permission(self.user, "data.enter"))

    def test_org_endpoint_filters_the_queryset_and_hides_out_of_scope_rows(self):
        UserRoleAssignment.objects.create(user=self.user, role=self.entry_role, org_node=self.site_a)
        client = APIClient()
        client.force_login(self.user)

        response = client.get("/api/org/nodes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({node["id"] for node in response.data}, {str(self.site_a.id), str(self.site_a_child.id)})

        response = client.get(f"/api/org/nodes/{self.site_b.id}/")
        self.assertEqual(response.status_code, 404)

        response = client.get(f"/api/org/nodes/{self.site_a.id}/ancestors/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_org_create_cannot_target_a_parent_outside_the_create_scope(self):
        self.entry_role.permissions.add(self.org_create_permission)
        UserRoleAssignment.objects.create(user=self.user, role=self.entry_role, org_node=self.site_a)
        client = APIClient()
        client.force_login(self.user)

        out_of_scope_response = client.post(
            "/api/org/nodes/",
            {
                "company": str(self.company.id),
                "parent": str(self.site_b.id),
                "node_type": "FACILITY",
                "code": "B-NEW",
                "name": "B New",
            },
            format="json",
        )
        self.assertEqual(out_of_scope_response.status_code, 404)

        in_scope_response = client.post(
            "/api/org/nodes/",
            {
                "company": str(self.company.id),
                "parent": str(self.site_a.id),
                "node_type": "FACILITY",
                "code": "A-NEW",
                "name": "A New",
            },
            format="json",
        )
        self.assertEqual(in_scope_response.status_code, 201)


class AuthenticationAndAdministrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="safe-password-123")
        self.permission = Permission.objects.create(
            code="dashboard.view", name="View dashboard", module_code="dashboard", action="VIEW"
        )
        role = Role.objects.create(role_code="member", role_name="Member")
        role.permissions.add(self.permission)
        UserRoleAssignment.objects.create(user=self.user, role=role)

    def test_login_returns_flat_permissions_and_a_csrf_token(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": "member", "password": "safe-password-123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["permissions"], ["dashboard.view"])
        self.assertTrue(response.data["csrfToken"])

    def test_seed_catalog_covers_active_viewsets_without_legacy_codes(self):
        seeded_codes = {code for code, *_ in PERMISSIONS}
        assigned_codes = {
            code for permission_codes in ROLE_PERMISSIONS.values()
            for code in permission_codes
        }
        active_endpoint_codes = {
            "user.view", "user.create", "user.edit", "user.delete",
            "role.view", "role.create", "role.edit", "role.delete",
            "permission.view", "dashboard.view", "activity_log.view",
        }
        for module in (
            "company", "country", "state", "city", "department",
            "organization", "reporting_period",
        ):
            active_endpoint_codes.update(
                f"{module}.{action}" for action in ("view", "create", "edit", "delete")
            )

        self.assertTrue(active_endpoint_codes.issubset(seeded_codes))
        self.assertTrue(assigned_codes.issubset(seeded_codes))
        self.assertFalse(any(code.startswith(("org.", "period.")) for code in seeded_codes))

    def test_role_writes_are_superuser_only(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/accounts/roles/",
            {"role_code": "not-allowed", "role_name": "Not Allowed"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_system_roles_return_a_validation_error_when_deleted(self):
        system_role = Role.objects.create(role_code="system", role_name="System", is_system=True)
        superuser = User.objects.create_superuser(username="admin", password="safe-password-123")
        self.client.force_login(superuser)

        response = self.client.delete(f"/api/accounts/roles/{system_role.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Role.objects.filter(pk=system_role.pk).exists())

    def test_session_authenticated_unsafe_requests_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="member", password="safe-password-123"))

        response = client.post("/api/accounts/logout/")
        self.assertEqual(response.status_code, 403)

        csrf_response = client.get("/api/accounts/csrf/")
        self.assertEqual(csrf_response.status_code, 200)
        token = csrf_response.json()["csrfToken"]
        response = client.post("/api/accounts/logout/", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)


class CompatibilityAndDashboardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Compatibility Co", company_code="COMPAT",
            contact_person="Owner", email="owner@example.com", mobile_number="9999999999",
        )
        self.root = OrgNode.objects.get(company=self.company, parent__isnull=True)
        self.facility = OrgNode.objects.create(
            company=self.company, parent=self.root, node_type="FACILITY",
            code="FACILITY", name="Facility",
        )
        self.department = Department.objects.create(company=self.company, name="Operations", code="OPS")
        self.user = User.objects.create_user(username="editor", password="safe-password-123")
        self.role = Role.objects.create(role_code="editor", role_name="Editor")
        UserRoleAssignment.objects.create(user=self.user, role=self.role, org_node=self.facility)
        UserDepartment.objects.create(user=self.user, department=self.department, is_primary=True)

    def test_user_detail_includes_editor_hydration_fields(self):
        data = UserSerializer(self.user).data
        self.assertEqual(str(data["role"]), str(self.role.id))
        self.assertEqual(str(data["org_node"]), str(self.facility.id))
        self.assertEqual(str(data["department"]), str(self.department.id))

    def test_system_role_can_update_permissions_without_renaming(self):
        permission = Permission.objects.create(
            code="compat.view", name="View compatibility", module_code="compat", action="VIEW"
        )
        system_role = Role.objects.create(role_code="system", role_name="System", is_system=True)
        serializer = RoleSerializer(system_role, data={
            "role_code": "system", "role_name": "System", "description": "Updated",
            "permissions": [str(permission.id)],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(list(system_role.permissions.values_list("id", flat=True)), [permission.id])

    def test_dashboard_includes_facility_count(self):
        superuser = User.objects.create_superuser(username="dashboard-admin", password="safe-password-123")
        client = APIClient(HTTP_HOST="localhost")
        client.force_login(superuser)
        response = client.get("/api/accounts/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["facility"], 1)
