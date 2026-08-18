from django.test import RequestFactory, TestCase
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.accounts.models import TestModel, User
from apps.core.exceptions import get_error_message
from apps.core.middleware import CurrentRequestMiddleware
from apps.core.models import ActivityLog, Notification
from apps.core.response import no_content_response
from apps.core.services.notification_service import notify
from apps.core.thread_local import get_current_request, set_current_request


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
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            notification_type="INFO",
            title="Other user's notification",
            message="Must remain private.",
        )
        self.client = APIClient()
        self.client.force_login(self.owner)

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
