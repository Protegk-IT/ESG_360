from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from django.conf import settings
from django.test import RequestFactory, TestCase,TransactionTestCase,Client
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient
from unittest.mock import patch
from django.middleware.csrf import get_token
import uuid
from apps.accounts.models import TestModel, User
from apps.core.exceptions import get_error_message
from apps.core.middleware import CurrentRequestMiddleware
from apps.core.models import ActivityLog, Notification
from apps.core.response import no_content_response
from apps.core.services.notification_service import notify
from apps.core.thread_local import get_current_request, set_current_request
from django.core.exceptions import ValidationError
from apps.core.serializers import NotificationSerializer
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from django.contrib.admin import AdminSite

from apps.core.admin import NotificationAdmin

class ActivityLogMixinTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="audit-user",
            password="not-for-audit-log",
        )
        self.factory = RequestFactory()

    def tearDown(self):
        set_current_request(None)

    def _set_request(self):
        request = self.factory.post(
            "/api/example/",
            HTTP_USER_AGENT="core-tests",
            REMOTE_ADDR="203.0.113.11",
        )
        request.user = self.actor
        set_current_request(request)

    def test_create_update_and_delete_are_audited_with_request_metadata(self):
        self._set_request()
        item = TestModel.objects.create(name="First name")
        item_id = str(item.id)
        item.name = "Updated name"
        item.save(update_fields=["name"])
        item.delete()

        logs = list(ActivityLog.objects.filter(model_name="TestModel").order_by("created_at"))
        self.assertEqual([log.action for log in logs], ["CREATE", "UPDATE", "DELETE"])
        self.assertEqual(logs[0].changes, {"name": "First name"})
        self.assertEqual(
            logs[1].changes,
            {"name": {"old": "First name", "new": "Updated name"}},
        )
        self.assertEqual(logs[2].changes, {"name": "Updated name"})
        self.assertEqual(logs[2].object_id, item_id)
        self.assertEqual(logs[0].user, self.actor)
        self.assertEqual(logs[0].ip_address, "203.0.113.11")
        self.assertEqual(logs[0].user_agent, "core-tests")
        self.assertEqual(logs[0].request_path, "/api/example/")

    def test_sensitive_fields_and_unpersisted_update_fields_are_not_audited(self):
        create_log = ActivityLog.objects.get(
            model_name="User",
            action="CREATE",
            object_id=str(self.actor.pk),
        )
        self.assertNotIn("password", create_log.changes)
        self.assertNotIn("profile_image", create_log.changes)

        self.actor.full_name = "Not persisted"
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        update_log = ActivityLog.objects.filter(
            model_name="User",
            action="UPDATE",
            object_id=str(self.actor.pk),
        ).latest("created_at")
        self.assertEqual(update_log.changes, {"is_active": {"old": True, "new": False}})
        self.assertNotIn("full_name", update_log.changes)
        self.actor.refresh_from_db()
        self.assertIsNone(self.actor.full_name)

    def test_request_context_is_cleared_when_a_view_raises(self):
        request = self.factory.get("/api/example/")

        def raising_response(_request):
            raise RuntimeError("expected test failure")

        middleware = CurrentRequestMiddleware(raising_response)
        with self.assertRaises(RuntimeError):
            middleware(request)
        self.assertIsNone(get_current_request())

    def test_audit_log_failure_rolls_back_the_model_write(self):
        with patch(
            "apps.core.mixins.ActivityLog.objects.create",
            side_effect=RuntimeError("audit storage unavailable"),
        ):
            with self.assertRaisesMessage(RuntimeError, "audit storage unavailable"):
                TestModel.objects.create(name="Must not persist")

        self.assertFalse(TestModel.objects.filter(name="Must not persist").exists())

    def test_session_login_and_logout_are_audited(self):
        client = APIClient()
        login_response = client.post(
            "/api/accounts/login/",
            {"username": "audit-user", "password": "not-for-audit-log"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        login_log = ActivityLog.objects.get(action="LOGIN", user=self.actor)
        self.assertEqual(login_log.request_path, "/api/accounts/login/")

        logout_response = client.post("/api/accounts/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, 200)
        logout_log = ActivityLog.objects.get(action="LOGOUT", user=self.actor)
        self.assertEqual(logout_log.request_path, "/api/accounts/logout/")


class NotificationAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="notification-owner", password="safe-password")
        self.other_user = User.objects.create_user(username="other-user", password="safe-password")
        self.owned_unread = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Owned unread",
            message="Owner can read this.",
        )
        self.owned_read = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Owned read",
            message="Already read.",
            is_read=True,
            read_at=timezone.now(),
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            notification_type="INFO",
            title="Other user's notification",
            message="Must remain private.",
        )
        self.client = APIClient()
        self.client.force_login(self.owner)

    def test_new_notification_is_unread_without_read_timestamp(self):
        notification = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Unread notification",
            message="This notification is unread.",
        )

        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_mark_as_read_sets_read_state_and_timestamp(self):
        notification = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Read me",
            message="This notification should become read.",
        )

        before = timezone.now()
        notification.mark_as_read()
        after = timezone.now()

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        self.assertGreaterEqual(notification.read_at, before)
        self.assertLessEqual(notification.read_at, after)

    def test_mark_as_read_is_idempotent(self):
        notification = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Read me",
            message="Read timestamp must remain stable.",
        )

        notification.mark_as_read()
        notification.refresh_from_db()

        first_read_at = notification.read_at

        notification.mark_as_read()
        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertEqual(notification.read_at, first_read_at)

    def test_mark_as_unread_clears_read_timestamp(self):
        notification = Notification.objects.create(
            recipient=self.owner,
            notification_type="INFO",
            title="Unread again",
            message="This notification will become unread.",
            is_read=True,
            read_at=timezone.now(),
        )

        notification.mark_as_unread()
        notification.refresh_from_db()

        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_read_notification_requires_read_timestamp(self):
        notification = Notification(
            recipient=self.owner,
            notification_type="INFO",
            title="Invalid read notification",
            message="This state should fail validation.",
            is_read=True,
            read_at=None,
        )

        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_unread_notification_cannot_have_read_timestamp(self):
        notification = Notification(
            recipient=self.owner,
            notification_type="INFO",
            title="Invalid unread notification",
            message="This state should fail validation.",
            is_read=False,
            read_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_list_and_mutations_are_limited_to_the_authenticated_recipient(self):
        list_response = self.client.get("/api/notifications/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in list_response.data},
            {str(self.owned_unread.id), str(self.owned_read.id)},
        )

        denied_response = self.client.patch(
            f"/api/notifications/{self.other_notification.id}/read/",
            {},
            format="json",
        )
        self.assertEqual(denied_response.status_code, 404)
        self.assertEqual(denied_response.data["success"], False)
        self.assertEqual(denied_response.data["message"], "Notification not found.")
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

        mark_read_response = self.client.patch(
            f"/api/notifications/{self.owned_unread.id}/read/", {}, format="json"
        )
        self.assertEqual(mark_read_response.status_code, 200)
        self.owned_unread.refresh_from_db()
        first_read_at = self.owned_unread.read_at
        self.assertTrue(self.owned_unread.is_read)
        self.assertIsNotNone(first_read_at)

        # Repeating the endpoint is idempotent and does not rewrite the
        # original read timestamp.
        self.client.patch(f"/api/notifications/{self.owned_unread.id}/read/", {}, format="json")
        self.owned_unread.refresh_from_db()
        self.assertEqual(self.owned_unread.read_at, first_read_at)

        read_all_response = self.client.patch("/api/notifications/read-all/", {}, format="json")
        self.assertEqual(read_all_response.status_code, 200)
        self.assertEqual(read_all_response.data["updated_count"], 0)

        unread_response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(unread_response.status_code, 200)
        self.assertEqual(unread_response.data["count"], 0)

    def test_notification_helper_records_an_optional_related_object(self):
        related_object = TestModel.objects.create(name="Submission-like record")
        notification = notify(
            recipient=self.owner,
            notification_type="SUBMISSION_APPROVED",
            title="Approved",
            message="The record was approved.",
            related_object=related_object,
            action_url=f"/records/{related_object.id}",
            priority="HIGH",
        )

        self.assertEqual(notification.related_model, "TestModel")
        self.assertEqual(notification.related_object_id, str(related_object.id))
        self.assertEqual(notification.action_url, f"/records/{related_object.id}")
        self.assertEqual(notification.priority, "HIGH")

    def test_notify_creates_unread_notification(self):
        notification = notify(
            recipient=self.owner,
            notification_type="INFO",
            title="Service notification",
            message="Created through the notification service.",
        )

        self.assertEqual(notification.recipient, self.owner)
        self.assertEqual(notification.notification_type, "INFO")
        self.assertEqual(notification.title, "Service notification")
        self.assertEqual(
            notification.message,
            "Created through the notification service.",
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        self.assertFalse(notification.email_sent)

    def test_notify_requires_recipient(self):
        with self.assertRaises(ValidationError):
            notify(
                recipient=None,
                notification_type="INFO",
                title="Test",
                message="Test message",
            )

    def test_notify_requires_notification_type(self):
        with self.assertRaises(ValidationError):
            notify(
                recipient=self.owner,
                notification_type="",
                title="Test",
                message="Test message",
            )

    def test_notify_requires_title(self):
        with self.assertRaises(ValidationError):
            notify(
                recipient=self.owner,
                notification_type="INFO",
                title="",
                message="Test message",
            )

    def test_notify_requires_message(self):
        with self.assertRaises(ValidationError):
            notify(
                recipient=self.owner,
                notification_type="INFO",
                title="Test",
                message="",
            )

    def test_notify_rejects_invalid_priority(self):
        with self.assertRaises(ValidationError):
            notify(
                recipient=self.owner,
                notification_type="INFO",
                title="Test",
                message="Test message",
                priority="URGENT",
            )

    def test_notify_accepts_explicit_related_metadata(self):
        notification = notify(
            recipient=self.owner,
            notification_type="IMPORT_COMPLETED",
            title="Import completed",
            message="The import batch completed successfully.",
            related_model="ImportBatch",
            related_object_id="batch-123",
            action_url="/imports/batch-123/",
            priority=Notification.PRIORITY_HIGH,
        )

        self.assertEqual(notification.related_model, "ImportBatch")
        self.assertEqual(notification.related_object_id, "batch-123")
        self.assertEqual(notification.action_url, "/imports/batch-123/")
        self.assertEqual(
            notification.priority,
            Notification.PRIORITY_HIGH,
        )

    def test_notify_rejects_mixed_related_object_arguments(self):
        related_object = TestModel.objects.create(
            name="Related object"
        )

        with self.assertRaises(ValidationError):
            notify(
                recipient=self.owner,
                notification_type="INFO",
                title="Test",
                message="Test message",
                related_object=related_object,
                related_model="OtherModel",
                related_object_id="123",
            )
    def test_notification_serializer_exposes_notification_fields_as_read_only(self):
        serializer = NotificationSerializer(instance=self.owned_unread)

        expected_fields = {
            "id",
            "recipient",
            "notification_type",
            "title",
            "message",
            "related_model",
            "related_object_id",
            "action_url",
            "priority",
            "is_read",
            "read_at",
            "email_sent",
            "created_at",
            "updated_at",
        }

        self.assertEqual(set(serializer.fields.keys()), expected_fields)

        for field_name in expected_fields:
            self.assertTrue(
                serializer.fields[field_name].read_only,
                f"{field_name} should be read-only",
            )

    def test_user_can_retrieve_own_notification_detail(self):
        response = self.client.get(
            f"/api/notifications/{self.owned_unread.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            str(self.owned_unread.id),
        )
        self.assertEqual(
            response.data["title"],
            "Owned unread",
        )
    def test_user_cannot_retrieve_another_users_notification_detail(self):
        response = self.client.get(
            f"/api/notifications/{self.other_notification.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_notification_list_supports_unread_filter(self):
        response = self.client.get(
            "/api/notifications/?is_read=false"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {item["id"] for item in response.data},
            {str(self.owned_unread.id)},
        )

    def test_notification_list_supports_read_filter(self):
        response = self.client.get(
            "/api/notifications/?is_read=true"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {item["id"] for item in response.data},
            {str(self.owned_read.id)},
        )

    def test_notification_list_supports_priority_filter(self):
        high_notification = Notification.objects.create(
            recipient=self.owner,
            notification_type="ALERT",
            title="High priority",
            message="High priority notification.",
            priority=Notification.PRIORITY_HIGH,
        )

        response = self.client.get(
            "/api/notifications/?priority=HIGH"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {item["id"] for item in response.data},
            {str(high_notification.id)},
        )

    def test_notification_list_supports_notification_type_filter(self):
        matching = Notification.objects.create(
            recipient=self.owner,
            notification_type="REPORT_READY",
            title="Report ready",
            message="Your report is ready.",
        )

        response = self.client.get(
            "/api/notifications/?notification_type=REPORT_READY"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {item["id"] for item in response.data},
            {str(matching.id)},
        )

    def test_invalid_is_read_filter_returns_empty_result(self):
        response = self.client.get(
            "/api/notifications/?is_read=invalid"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_unauthenticated_user_cannot_access_notifications(self):
        self.client.logout()

        response = self.client.get("/api/notifications/")

        self.assertIn(response.status_code, (401, 403))

    def test_unauthenticated_user_cannot_access_notification_detail(self):
        self.client.logout()

        response = self.client.get(
            f"/api/notifications/{self.owned_unread.id}/"
        )

        self.assertIn(response.status_code, (401, 403))

    def test_user_cannot_mark_another_users_notification_as_read(self):
        response = self.client.patch(
            f"/api/notifications/{self.other_notification.id}/read/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.other_notification.refresh_from_db()

        self.assertFalse(self.other_notification.is_read)
        self.assertIsNone(self.other_notification.read_at)

    def test_filtered_notification_list_excludes_another_users_notifications(self):
        response = self.client.get(
            "/api/notifications/?notification_type=INFO"
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertNotIn(
            str(self.other_notification.id),
            returned_ids,
        )
    def test_unknown_notification_uuid_returns_not_found(self):
        response = self.client.get(
            f"/api/notifications/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_notification_uuid_cannot_be_marked_read(self):
        response = self.client.patch(
            f"/api/notifications/{uuid.uuid4()}/read/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_read_all_only_marks_current_users_notifications(self):
        response = self.client.patch(
            "/api/notifications/read-all/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.owned_unread.refresh_from_db()
        self.other_notification.refresh_from_db()

        self.assertTrue(self.owned_unread.is_read)
        self.assertIsNotNone(self.owned_unread.read_at)

        self.assertFalse(self.other_notification.is_read)
        self.assertIsNone(self.other_notification.read_at)

    def test_mark_as_read_sets_read_at(self):
        self.assertFalse(self.owned_unread.is_read)
        self.assertIsNone(self.owned_unread.read_at)

        response = self.client.patch(
            f"/api/notifications/{self.owned_unread.id}/read/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.owned_unread.refresh_from_db()

        self.assertTrue(self.owned_unread.is_read)
        self.assertIsNotNone(self.owned_unread.read_at)

    def test_api_mark_as_read_is_idempotent(self):
        response = self.client.patch(
            f"/api/notifications/{self.owned_unread.id}/read/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.owned_unread.refresh_from_db()
        first_read_at = self.owned_unread.read_at

        response = self.client.patch(
            f"/api/notifications/{self.owned_unread.id}/read/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.owned_unread.refresh_from_db()

        self.assertTrue(self.owned_unread.is_read)
        self.assertEqual(self.owned_unread.read_at, first_read_at)

    def test_unread_count_only_counts_current_users_notifications(self):
        response = self.client.get(
            "/api/notifications/unread-count/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)


class NotificationSessionCSRFApiTests(TestCase):
    """
    Smoke tests for the real Django session-authentication and CSRF
    contract used by the notification API.

    These tests intentionally use Django's test Client rather than
    DRF force_authenticate(), so that session authentication and CSRF
    enforcement are exercised explicitly.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="notification-session-user",
            password="test-password-123",
        )

        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Session CSRF test",
            message="Notification API session/CSRF smoke test.",
            notification_type="SYSTEM",
            priority="NORMAL",
        )

        self.client = Client(enforce_csrf_checks=True)

    def test_session_authenticated_notification_list(self):
        logged_in = self.client.login(
            username="notification-session-user",
            password="test-password-123",
        )

        self.assertTrue(logged_in)

        response = self.client.get(
            reverse("notification-list")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unsafe_notification_request_requires_csrf(self):
        logged_in = self.client.login(
            username="notification-session-user",
            password="test-password-123",
        )

        self.assertTrue(logged_in)

        response = self.client.patch(
            reverse("notification-read-all")
        )

        self.assertEqual(response.status_code, 403)

    def test_unsafe_notification_request_accepts_valid_csrf(self):
        logged_in = self.client.login(
            username="notification-session-user",
            password="test-password-123",
        )

        self.assertTrue(logged_in)

        response = self.client.get(
            reverse("notification-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        csrf_token = get_token(response.wsgi_request)

        self.client.cookies["csrftoken"] = csrf_token

        response = self.client.patch(
            reverse("notification-read-all"),
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.notification.refresh_from_db()

        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

class NotificationAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.superuser = User.objects.create_superuser(
            username="notification-admin",
            email="admin@example.com",
            password="testpass123",
        )

        self.recipient = User.objects.create_user(
            username="notification-recipient",
            email="recipient@example.com",
            password="testpass123",
        )

        self.notification = Notification.objects.create(
            recipient=self.recipient,
            notification_type="INFO",
            title="Test notification",
            message="Test notification message",
        )

        self.site = AdminSite()
        self.model_admin = NotificationAdmin(
            Notification,
            self.site,
        )

    def test_admin_cannot_add_notifications(self):
        self.assertFalse(
            self.model_admin.has_add_permission(self.superuser)
        )

    def test_admin_cannot_change_notifications(self):
        self.assertFalse(
            self.model_admin.has_change_permission(
                self.superuser,
                self.notification,
            )
        )

    def test_admin_cannot_delete_notifications(self):
        self.assertFalse(
            self.model_admin.has_delete_permission(
                self.superuser,
                self.notification,
            )
        )

class NotificationMigrationCompatibilityTests(TransactionTestCase):
    migrate_from = (
        "core",
        "0002_notification_notificatio_recipie_201701_idx_and_more",
    )
    migrate_to = (
        "core",
        "0003_notification_notification_read_state_consistent",
    )

    def setUp(self):
        super().setUp()

        self.executor = MigrationExecutor(connection)

        # The test database is initially at the latest migration.
        # Move the complete project schema back to the state represented
        # by core.0002 so that the legacy notification rows are created
        # against the historical schema.

        migration_state = [
            self.migrate_from,
            ("accounts", "0003_permission_testmodel_userdepartment_and_more"),
        ]

        self.executor.migrate(migration_state)

        # Get the historical app registry after migrating to 0002.
        old_apps = self.executor.loader.project_state(
            [self.migrate_from]
        ).apps

        #User = old_apps.get_model("accounts", "User")
        Notification = old_apps.get_model("core", "Notification")
        user_model = get_user_model()
        self.user = user_model.objects.create(
            username="migration-notification-user",
        )
        self.user_id = self.user.pk
        self.created_at = timezone.datetime(
            2026,
            8,
            20,
            10,
            30,
            tzinfo=timezone.get_current_timezone(),
        )

        self.legacy_read = Notification.objects.create(
            recipient_id=self.user.pk,
            notification_type="INFO",
            title="Legacy read notification",
            message="Legacy read notification",
            is_read=True,
            read_at=None,
        )

        self.legacy_unread = Notification.objects.create(
            recipient_id=self.user.pk,
            notification_type="INFO",
            title="Legacy unread notification",
            message="Legacy unread notification",
            is_read=False,
            read_at=self.created_at,
        )

        Notification.objects.filter(
            pk=self.legacy_read.pk,
        ).update(
            created_at=self.created_at,
        )

        Notification.objects.filter(
            pk=self.legacy_unread.pk,
        ).update(
            created_at=self.created_at,
        )

    def test_legacy_notification_read_state_is_normalized(self):
        # Use a fresh executor so Django reads the current migration
        # recorder state after setUp() moved core back to 0002.
        executor = MigrationExecutor(connection)

        executor.migrate(
            [
                self.migrate_to,
                (
                    "accounts",
                    "0003_permission_testmodel_userdepartment_and_more",
                ),
            ]
        )

        apps = executor.loader.project_state(
            [
                self.migrate_to,
                (
                    "accounts",
                    "0003_permission_testmodel_userdepartment_and_more",
                ),
            ]
        ).apps

        Notification = apps.get_model("core", "Notification")

        legacy_read = Notification.objects.get(
            pk=self.legacy_read.pk
        )
        legacy_unread = Notification.objects.get(
            pk=self.legacy_unread.pk
        )

        self.assertTrue(legacy_read.is_read)
        self.assertEqual(
            legacy_read.read_at,
            self.created_at,
        )

        self.assertFalse(legacy_unread.is_read)
        self.assertIsNone(legacy_unread.read_at)

class ErrorContractTests(TestCase):
    def test_error_message_extraction_preserves_detail_and_validation_messages(self):
        self.assertEqual(
            get_error_message({"detail": ErrorDetail("Not found.", code="not_found")}),
            "Not found.",
        )
        self.assertEqual(
            get_error_message({"name": [ErrorDetail("This field is required.", code="required")]}),
            "This field is required.",
        )

    def test_no_content_response_does_not_claim_to_return_a_json_body(self):
        response = no_content_response()
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)
