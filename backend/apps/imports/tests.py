import os
import tempfile
import uuid
from datetime import date, datetime
from unittest.mock import patch
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from apps.organizations.models import OrgNode
from apps.periods.models import ReportingPeriod
from apps.companies.models import Company

from openpyxl import Workbook

import threading
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections

from rest_framework.test import APIClient

from apps.imports.handlers import (
    FakeAnswersImportHandler,
    ImportHandlerRegistry,
    ImportHandler
)
from apps.imports.models import ImportBatch, ImportRow
from apps.imports.parser import ExcelParser, ImportFileError
from apps.imports.services import (
    ImportBatchService,
    ImportUploadService,
)


User = get_user_model()

class TestDestinationCommitHandler(ImportHandler):
    """
    Test-only handler that performs a real database write and then
    raises an exception.

    The purpose is to verify that ImportBatchService.commit()
    rolls back destination-side database writes together with
    the batch transaction.
    """

    @staticmethod
    def validate_row(data):
        return data, {}

    @staticmethod
    def validate_batch(rows):
        return None

    @staticmethod
    def commit(batch):
        from apps.modules.models import Module

        Module.objects.create(
            code=f"rollback-test-{batch.pk}",
            name="Rollback Test Module",
            is_enabled=True,
        )

        raise RuntimeError(
            "Destination write failed after database write"
        )

# ============================================================================
# Shared helpers
# ============================================================================


class ImportTestMixin:
    """Shared helpers for focused import-batch tests."""

    def create_user(self, username=None, **kwargs):
        if username is None:
            username = f"testuser_{User.objects.count()}"

        defaults = {
            "password": "TestPassword123!",
        }
        defaults.update(kwargs)

        return User.objects.create_user(
            username=username,
            **defaults,
        )

    def create_excel_file(
        self,
        rows=None,
        headers=None,
        filename="import_test.xlsx",
    ):
        if headers is None:
            headers = [
                "facility_code",
                "quantity",
            ]

        if rows is None:
            rows = [
                {
                    "facility_code": "FAC-001",
                    "quantity": 10,
                }
            ]

        workbook = Workbook()
        worksheet = workbook.active

        worksheet.append(headers)

        for row in rows:
            worksheet.append(
                [
                    row.get(header)
                    for header in headers
                ]
            )

        with tempfile.NamedTemporaryFile(
            suffix=".xlsx",
            delete=False,
        ) as tmp:
            temp_path = tmp.name

        try:
            workbook.save(temp_path)

            with open(temp_path, "rb") as file_handle:
                content = file_handle.read()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        return SimpleUploadedFile(
            filename,
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    def create_batch_directly(
        self,
        user=None,
        status=ImportBatch.Status.UPLOADED,
        rows=None,
        import_type=ImportBatch.ImportType.ANSWERS,
        module_code=None,
    ):
        if user is None:
            user = self.create_user()

        if rows is None:
            rows = [
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                }
            ]
        valid_rows = sum(
            1
            for row in rows
            if row.get("status") == ImportRow.Status.VALID
        )

        error_rows = sum(
            1
            for row in rows
            if row.get("status") == ImportRow.Status.ERROR
        )

        batch = ImportBatch.objects.create(
            import_type=import_type,
            file_name="test.xlsx",
            file_path="imports/test.xlsx",
            uploaded_by=user,
            status=status,
            module_code=module_code,
            total_rows=len(rows),
            valid_rows=valid_rows,
            error_rows=error_rows,
        )

        ImportRow.objects.bulk_create(
            [
                ImportRow(
                    batch=batch,
                    row_number=row["row_number"],
                    raw_data=row["raw_data"],
                    status=row.get(
                        "status",
                        ImportRow.Status.VALID,
                    ),
                    errors=row.get(
                        "errors",
                        {},
                    ),
                )
                for row in rows
            ]
        )

        return batch

    def create_valid_batch(self, user=None):
        return self.create_batch_directly(
            user=user,
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                }
            ],
        )

    def create_invalid_batch(self, user=None):
        return self.create_batch_directly(
            user=user,
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 10,
                    },
                }
            ],
        )

    def create_validated_batch(self, user=None):
        batch = self.create_valid_batch(user=user)

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            FakeAnswersImportHandler,
        )

        return ImportBatchService.validate_batch(batch)

    def api_client(self, user=None):
        client = APIClient()

        if user is not None:
            client.force_authenticate(user=user)

        return client


# ============================================================================
# Model / Domain tests
# ============================================================================


class ImportBatchModelTests(
    ImportTestMixin,
    TestCase,
):
    """Focused domain/model coverage."""

    def test_valid_batch_lifecycle_values(self):
        valid_statuses = {
            ImportBatch.Status.UPLOADED,
            ImportBatch.Status.VALIDATING,
            ImportBatch.Status.VALIDATED,
            ImportBatch.Status.FAILED,
            ImportBatch.Status.COMMITTED,
        }

        declared_statuses = {
            value
            for value, _ in ImportBatch.Status.choices
        }

        self.assertTrue(
            valid_statuses.issubset(declared_statuses)
        )

    def test_invalid_lifecycle_transition_rejected(self):
        batch = self.create_valid_batch()

        with self.assertRaises(ValidationError):
            ImportBatchService.commit(batch)

    def test_committed_batch_cannot_be_reopened_or_recommitted(self):
        batch = self.create_validated_batch()

        ImportBatchService.commit(batch)

        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.COMMITTED,
        )
        self.assertIsNotNone(batch.committed_at)

        with self.assertRaises(ValidationError):
            ImportBatchService.commit(batch)

        with self.assertRaises(ValidationError):
            ImportBatchService.validate_batch(batch)

    def test_row_belongs_to_one_batch(self):
        batch_one = self.create_batch_directly()
        batch_two = self.create_batch_directly()

        row = batch_one.rows.get()

        self.assertEqual(
            row.batch_id,
            batch_one.pk,
        )

        self.assertNotEqual(
            row.batch_id,
            batch_two.pk,
        )

        self.assertEqual(
            batch_one.rows.count(),
            1,
        )
        self.assertEqual(
            batch_two.rows.count(),
            1,
        )

    def test_row_numbers_are_preserved(self):
        batch = self.create_batch_directly(
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                },
                {
                    "row_number": 5,
                    "raw_data": {
                        "facility_code": "FAC-002",
                        "quantity": 20,
                    },
                },
            ]
        )

        row_numbers = list(
            batch.rows.order_by(
                "row_number"
            ).values_list(
                "row_number",
                flat=True,
            )
        )

        self.assertEqual(
            row_numbers,
            [2, 5],
        )

    def test_structured_row_errors_persist(self):
        errors = {
            "facility_code": [
                "This field is required."
            ],
            "quantity": [
                "Must be greater than or equal to zero."
            ],
        }

        batch = self.create_batch_directly(
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": -1,
                    },
                    "status": ImportRow.Status.ERROR,
                    "errors": errors,
                }
            ]
        )

        row = batch.rows.get()
        row.refresh_from_db()

        self.assertEqual(
            row.errors,
            errors,
        )

        self.assertIsInstance(
            row.errors,
            dict,
        )

    def test_batch_counts_match_its_rows(self):
        batch = self.create_batch_directly(
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.VALID,
                },
                {
                    "row_number": 3,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.ERROR,
                    "errors": {
                        "facility_code": [
                            "This field is required."
                        ]
                    },
                },
                {
                    "row_number": 4,
                    "raw_data": {
                        "facility_code": "FAC-003",
                        "quantity": 30,
                    },
                    "status": ImportRow.Status.VALID,
                },
            ]
        )

        valid_count = batch.rows.filter(
            status=ImportRow.Status.VALID
        ).count()

        error_count = batch.rows.filter(
            status=ImportRow.Status.ERROR
        ).count()

        self.assertEqual(
            batch.total_rows,
            batch.rows.count(),
        )

        self.assertEqual(
            batch.valid_rows,
            valid_count,
        )

        self.assertEqual(
            batch.error_rows,
            error_count,
        )

        self.assertEqual(
            valid_count,
            2,
        )

        self.assertEqual(
            error_count,
            1,
        )

    def test_valid_canonical_module_code_is_accepted(self):
        """
        Uses an existing module code from the database.

        If the project has no Module records in the test database,
        this test will need to create the appropriate Module fixture.
        """
        from apps.modules.models import Module

        user = self.create_user()

        module = Module.objects.create(
            code="energy",
            name="Energy",
            is_enabled=True,
        )

        uploaded_file = self.create_excel_file()

        batch = ImportUploadService.create_batch(
            uploaded_file=uploaded_file,
            uploaded_by=user,
            import_type=ImportBatch.ImportType.ANSWERS,
            module_code=module.code,
        )

        self.assertEqual(
            batch.module_code,
            module.code,
        )

    def test_unknown_module_code_is_rejected(self):
        user = self.create_user()

        uploaded_file = self.create_excel_file()

        with self.assertRaises(ValidationError):
            ImportUploadService.create_batch(
                uploaded_file=uploaded_file,
                uploaded_by=user,
                import_type=ImportBatch.ImportType.ANSWERS,
                module_code="DOES_NOT_EXIST",
            )

    def test_committed_batch_cannot_be_modified_directly(self):
        batch = self.create_validated_batch()

        ImportBatchService.commit(batch)

        batch.refresh_from_db()

        batch.file_name = "changed.xlsx"

        with self.assertRaisesMessage(
            ValidationError,
            "A committed import batch cannot be modified.",
        ):
            batch.save()

        batch.refresh_from_db()

        self.assertEqual(
            batch.file_name,
            "test.xlsx",
        )


    def test_committed_batch_cannot_be_deleted_directly(self):
        batch = self.create_validated_batch()

        ImportBatchService.commit(batch)

        batch.refresh_from_db()

        with self.assertRaisesMessage(
            ValidationError,
            "A committed import batch cannot be deleted.",
        ):
            batch.delete()

        self.assertTrue(
            ImportBatch.objects.filter(
                pk=batch.pk
            ).exists()
        )

# ============================================================================
# File parsing tests
# ============================================================================


class ExcelParserTests(ImportTestMixin,TestCase):
    """Focused spreadsheet parser coverage."""

    def setUp(self):
        self.parser = ExcelParser()

    def create_workbook_file(
        self,
        headers,
        rows,
        suffix=".xlsx",
    ):
        workbook = Workbook()
        worksheet = workbook.active

        worksheet.append(headers)

        for row in rows:
            worksheet.append(row)

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as tmp:
            path = tmp.name

        try:
            workbook.save(path)
        except Exception:
            if os.path.exists(path):
                os.unlink(path)
            raise

        return path

    def test_valid_xlsx_parses_rows_correctly(self):
        path = self.create_workbook_file(
            headers=[
                "facility_code",
                "quantity",
            ],
            rows=[
                ["FAC-001", 10],
                ["FAC-002", 20],
            ],
        )

        try:
            result = self.parser.parse(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["raw_data"],
            {
                "facility_code": "FAC-001",
                "quantity": 10,
            },
        )

        self.assertEqual(
            result[1]["raw_data"],
            {
                "facility_code": "FAC-002",
                "quantity": 20,
            },
        )

    def test_spreadsheet_row_numbers_are_preserved(self):
        path = self.create_workbook_file(
            headers=["facility_code"],
            rows=[
                ["FAC-001"],
                [None],
                ["FAC-003"],
            ],
        )

        try:
            result = self.parser.parse(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

        self.assertEqual(
            [row["row_number"] for row in result],
            [2, 4],
        )

    def test_blank_rows_are_handled_consistently(self):
        path = self.create_workbook_file(
            headers=[
                "facility_code",
                "quantity",
            ],
            rows=[
                ["FAC-001", 10],
                [None, None],
                ["FAC-002", 20],
            ],
        )

        try:
            result = self.parser.parse(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["row_number"],
            2,
        )

        self.assertEqual(
            result[1]["row_number"],
            4,
        )

    def test_malformed_or_unsupported_upload_is_rejected_cleanly(self):
        with tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False,
        ) as tmp:
            path = tmp.name
            tmp.write(b"facility_code,quantity\nFAC-001,10")

        try:
            with self.assertRaises(ImportFileError):
                self.parser.parse(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

        with self.assertRaises(ImportFileError):
            self.parser.parse(
                "does-not-exist.xlsx"
            )

    def test_common_cell_values_are_json_safe(self):
        path = self.create_workbook_file(
            headers=[
                "report_date",
                "created_at",
                "quantity",
            ],
            rows=[
                [
                    date(2026, 8, 14),
                    datetime(2026, 8, 14, 12, 30, 15),
                    12.5,
                ]
            ],
        )

        try:
            result = self.parser.parse(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

        data = result[0]["raw_data"]

        self.assertEqual(
            data["report_date"],
            "2026-08-14T00:00:00",
        )

        self.assertEqual(
            data["created_at"],
            "2026-08-14T12:30:15",
        )

        self.assertEqual(
            data["quantity"],
            12.5,
        )

    def test_file_like_object_is_supported(self):
        uploaded_file = self.create_excel_file(
            rows=[
                {
                    "facility_code": "FAC-001",
                    "quantity": 10,
                }
            ]
        )

        result = self.parser.parse(uploaded_file)

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0]["row_number"],
            2,
        )

        self.assertEqual(
            result[0]["raw_data"]["facility_code"],
            "FAC-001",
        )

        self.assertEqual(
            result[0]["raw_data"]["quantity"],
            10,
        )

    def test_file_size_limit_is_enforced(self):
        oversized_file = SimpleUploadedFile(
            "large.xlsx",
            b"x" * (ExcelParser.MAX_FILE_SIZE + 1),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        with self.assertRaisesMessage(
            ImportFileError,
            "The uploaded file is too large. Maximum allowed size is 10 MB.",
        ):
            self.parser.parse(oversized_file)
# ============================================================================
# Validation lifecycle tests
# ============================================================================


@override_settings(
    DEFAULT_FILE_STORAGE=(
        "django.core.files.storage.FileSystemStorage"
    ),
    MEDIA_ROOT=tempfile.gettempdir(),
)
class ImportValidationTests(ImportTestMixin,TestCase,):
    """Focused upload and validation lifecycle tests."""

    def setUp(self):
        ImportHandlerRegistry.clear()

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            FakeAnswersImportHandler,
        )

    def tearDown(self):
        ImportHandlerRegistry.clear()

    def test_upload_creates_batch_and_rows_without_destination_writes(self,):
        user = self.create_user()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
        ) as commit_mock:

            uploaded_file = self.create_excel_file(
                rows=[
                    {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                    {
                        "facility_code": "FAC-002",
                        "quantity": 20,
                    },
                ]
            )

            batch = ImportUploadService.create_batch(
                uploaded_file=uploaded_file,
                uploaded_by=user,
                import_type=ImportBatch.ImportType.ANSWERS,
            )

        self.assertEqual(
            batch.status,
            ImportBatch.Status.UPLOADED,
        )

        self.assertEqual(
            batch.rows.count(),
            2,
        )

        self.assertEqual(
            batch.total_rows,
            2,
        )

        commit_mock.assert_not_called()

    def test_validation_marks_valid_rows_correctly(self):
        batch = self.create_valid_batch()

        result = ImportBatchService.validate_batch(
            batch
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            ImportBatch.Status.VALIDATED,
        )

        self.assertEqual(
            result.valid_rows,
            1,
        )

        self.assertEqual(
            result.error_rows,
            0,
        )

        row = result.rows.get()

        self.assertEqual(
            row.status,
            ImportRow.Status.VALID,
        )

        self.assertEqual(
            row.errors,
            {},
        )

    def test_validation_records_row_errors(self):
        batch = self.create_batch_directly(
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 10,
                    },
                },
                {
                    "row_number": 3,
                    "raw_data": {
                        "facility_code": "FAC-002",
                        "quantity": -1,
                    },
                },
            ]
        )

        result = ImportBatchService.validate_batch(
            batch
        )

        self.assertEqual(
            result.status,
            ImportBatch.Status.FAILED,
        )

        self.assertEqual(
            result.valid_rows,
            0,
        )

        self.assertEqual(
            result.error_rows,
            2,
        )

        rows = list(
            result.rows.order_by(
                "row_number"
            )
        )

        self.assertEqual(
            rows[0].status,
            ImportRow.Status.ERROR,
        )

        self.assertIn(
            "facility_code",
            rows[0].errors,
        )

        self.assertEqual(
            rows[1].status,
            ImportRow.Status.ERROR,
        )

        self.assertIn(
            "quantity",
            rows[1].errors,
        )

    def test_batch_becomes_validated_only_when_all_rows_are_valid(
        self,
    ):
        batch = self.create_batch_directly(
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                },
                {
                    "row_number": 3,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 10,
                    },
                },
            ]
        )

        result = ImportBatchService.validate_batch(
            batch
        )

        self.assertEqual(
            result.status,
            ImportBatch.Status.FAILED,
        )

        self.assertNotEqual(
            result.status,
            ImportBatch.Status.VALIDATED,
        )

        with self.assertRaises(ValidationError):
            ImportBatchService.commit(result)

    def test_batch_with_validation_errors_cannot_commit(self):
        batch = self.create_invalid_batch()

        result = ImportBatchService.validate_batch(
            batch
        )

        self.assertEqual(
            result.status,
            ImportBatch.Status.FAILED,
        )

        with self.assertRaises(ValidationError):
            ImportBatchService.commit(result)


# ============================================================================
# Commit tests
# ============================================================================


class ImportCommitServiceTests(
    ImportTestMixin,
    TestCase,
):
    """Focused transactional commit coverage."""

    def setUp(self):
        ImportHandlerRegistry.clear()

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            FakeAnswersImportHandler,
        )

    def tearDown(self):
        ImportHandlerRegistry.clear()

    def test_validated_batch_commits_once(self):
        batch = self.create_validated_batch()

        result = ImportBatchService.commit(
            batch
        )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            ImportBatch.Status.COMMITTED,
        )

        self.assertIsNotNone(
            result.committed_at,
        )

        self.assertTrue(
            result.rows.filter(
                status=ImportRow.Status.COMMITTED
            ).exists()
        )

    def test_commit_is_atomic(self):
        batch = self.create_validated_batch()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
            side_effect=RuntimeError(
                "Commit failed"
            ),
        ):
            with self.assertRaises(RuntimeError):
                ImportBatchService.commit(
                    batch
                )

        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.VALIDATED,
        )

        self.assertIsNone(
            batch.committed_at,
        )

        row = batch.rows.get()

        self.assertEqual(
            row.status,
            ImportRow.Status.VALID,
        )

    def test_handler_exception_rolls_back_destination_effects(
        self,
    ):
        batch = self.create_validated_batch()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
            side_effect=RuntimeError(
                "Destination write failed"
            ),
        ) as commit_mock:

            with self.assertRaises(RuntimeError):
                ImportBatchService.commit(
                    batch
                )

        commit_mock.assert_called_once()

        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.VALIDATED,
        )

        self.assertIsNone(
            batch.committed_at,
        )

    def test_failed_commit_does_not_mark_batch_committed(
        self,
    ):
        batch = self.create_validated_batch()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
            side_effect=RuntimeError(
                "Commit failed"
            ),
        ):
            with self.assertRaises(RuntimeError):
                ImportBatchService.commit(
                    batch
                )

        batch.refresh_from_db()

        self.assertNotEqual(
            batch.status,
            ImportBatch.Status.COMMITTED,
        )

        self.assertIsNone(
            batch.committed_at,
        )

    def test_second_commit_attempt_is_rejected(self):
        batch = self.create_validated_batch()

        ImportBatchService.commit(
            batch
        )

        batch.refresh_from_db()

        with self.assertRaises(ValidationError):
            ImportBatchService.commit(
                batch
            )
    def test_concurrent_commit_executes_handler_only_once(self):
        batch = self.create_validated_batch()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
        ) as commit_mock:

            first_result = ImportBatchService.commit(
                batch
            )

            with self.assertRaises(ValidationError):
                ImportBatchService.commit(
                    batch
                )

        commit_mock.assert_called_once()

        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.COMMITTED,
        )

        self.assertIsNotNone(
            batch.committed_at,
        )

    def test_commit_re_reads_batch_before_executing_handler(self):
        batch = self.create_validated_batch()

        with patch.object(
            FakeAnswersImportHandler,
            "commit",
        ) as commit_mock:

            # Pass a stale object whose status is still VALIDATED.
            stale_batch = ImportBatch.objects.get(
                pk=batch.pk
            )

            # Simulate another transaction/request having already
            # committed the batch in the database.
            ImportBatch.objects.filter(
                pk=batch.pk
            ).update(
                status=ImportBatch.Status.COMMITTED,
                committed_at=timezone.now(),
            )

            with self.assertRaisesMessage(
                ValidationError,
                "This batch has already been committed.",
            ):
                ImportBatchService.commit(
                    stale_batch
                )

        # The handler must NOT execute because commit()
        # re-reads the current database state.
        commit_mock.assert_not_called()

        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.COMMITTED,
        )

    def test_commit_rolls_back_destination_database_write(self):
        from apps.modules.models import Module
        batch = self.create_validated_batch()

        ImportHandlerRegistry.clear()

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            TestDestinationCommitHandler,
        )

        destination_code = f"rollback-test-{batch.pk}"

        self.assertFalse(
            Module.objects.filter(
                code=destination_code
            ).exists()
        )

        with self.assertRaisesMessage(
            RuntimeError,
            "Destination write failed after database write",
        ):
            ImportBatchService.commit(batch)

        # Destination-side database write must be rolled back.
        self.assertFalse(
            Module.objects.filter(
                code=destination_code
            ).exists()
        )

        # ImportBatch state must also be rolled back.
        batch.refresh_from_db()

        self.assertEqual(
            batch.status,
            ImportBatch.Status.VALIDATED,
        )

        self.assertIsNone(
            batch.committed_at,
        )

        # ImportRow state must remain unchanged.
        row = batch.rows.get()

        self.assertEqual(
            row.status,
            ImportRow.Status.VALID,
        )
# ============================================================================
# API tests
# ============================================================================


class ImportBatchAPITests(
    ImportTestMixin,
    TestCase,
):
    """Focused API authorization and preview coverage."""

    def setUp(self):
        self.uploader = self.create_user(
            username="uploader",
        )

        self.other_user = self.create_user(
            username="other_user",
        )

        self.superuser = self.create_user(
            username="superuser",
            is_staff=True,
            is_superuser=True,
        )

        self.client = APIClient()

        ImportHandlerRegistry.clear()

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            FakeAnswersImportHandler,
        )

    def tearDown(self):
        ImportHandlerRegistry.clear()

    def test_unauthenticated_access_rejected(self):
        batch = self.create_batch_directly(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-detail",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_uploader_can_inspect_their_batch(self):
        batch = self.create_batch_directly(
            user=self.uploader,
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-detail",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(batch.pk),
        )

    def test_unrelated_normal_user_cannot_inspect_batch(self):
        batch = self.create_batch_directly(
            user=self.uploader,
        )

        self.client.force_authenticate(
            user=self.other_user,
        )

        response = self.client.get(
            reverse(
                "import-batch-detail",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_superuser_can_inspect_batch(self):
        batch = self.create_batch_directly(
            user=self.uploader,
        )

        self.client.force_authenticate(
            user=self.superuser,
        )

        response = self.client.get(
            reverse(
                "import-batch-detail",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(batch.pk),
        )

    def test_batch_preview_response_shape_is_stable(self):
        batch = self.create_batch_directly(
            user=self.uploader,
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                },
                {
                    "row_number": 3,
                    "raw_data": {
                        "facility_code": "FAC-002",
                        "quantity": 20,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                },
            ],
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-detail",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "id",
                "import_type",
                "file_name",
                "file_path",
                "module_code",
                "org_node",
                "reporting_period",
                "status",
                "total_rows",
                "valid_rows",
                "error_rows",
                "uploaded_at",
                "committed_at",
            },
        )

        rows_response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            )
        )

        self.assertEqual(
            rows_response.status_code,
            200,
        )

        # Rows endpoint is paginated.
        self.assertEqual(
            set(rows_response.data.keys()),
            {
                "count",
                "next",
                "previous",
                "results",
            },
        )

        self.assertEqual(
            rows_response.data["count"],
            2,
        )

        self.assertIsNone(
            rows_response.data["next"],
        )

        self.assertIsNone(
            rows_response.data["previous"],
        )

        self.assertEqual(
            len(rows_response.data["results"]),
            2,
        )

        self.assertEqual(
            set(rows_response.data["results"][0].keys()),
            {
                "id",
                "batch",
                "row_number",
                "raw_data",
                "status",
                "errors",
            },
        )

    def test_unsupported_concrete_import_handler_returns_clear_error(self,):
        ImportHandlerRegistry.clear()

        batch = self.create_batch_directly(
            user=self.uploader,
            import_type=ImportBatch.ImportType.DATAPOINTS,
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.post(
            reverse(
                "import-batch-validate",
                kwargs={
                    "id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "import_type",
            response.data,
        )

        self.assertIn(
            "No import handler is registered",
            str(response.data),
        )

    def test_upload_without_production_handler_never_commits(self):
        ImportHandlerRegistry.clear()

        user = self.uploader

        uploaded_file = self.create_excel_file(
            rows=[
                {
                    "facility_code": "FAC-001",
                    "quantity": 10,
                }
            ]
        )

        self.client.force_authenticate(user=user)

        upload_response = self.client.post(
            reverse("import-batch-upload"),
            {
                "file": uploaded_file,
                "import_type": ImportBatch.ImportType.ANSWERS,
            },
            format="multipart",
        )

        self.assertEqual(upload_response.status_code, 201)

        batch_id = upload_response.data["id"]

        batch = ImportBatch.objects.get(pk=batch_id)

        self.assertEqual(
            batch.status,
            ImportBatch.Status.UPLOADED,
        )

        validate_response = self.client.post(
            reverse(
                "import-batch-validate",
                kwargs={"id": batch_id},
            )
        )

        self.assertEqual(
            validate_response.status_code,
            400,
        )

        self.assertIn(
            "No import handler is registered",
            str(validate_response.data),
        )

        batch.refresh_from_db()

        self.assertNotEqual(
            batch.status,
            ImportBatch.Status.COMMITTED,
        )

    def test_unrelated_normal_user_cannot_inspect_batch_rows(self):
        owner = self.create_user()
        other_user = self.create_user()

        batch = self.create_batch_directly(
            user=owner,
        )

        self.client.force_authenticate(
            user=other_user,
        )

        response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_upload_accepts_and_persists_org_node_and_reporting_period(self):
        company = Company.objects.create(
            company_name="Test Company",
            company_code="TEST001",
            contact_person="Test User",
            email="test@example.com",
            mobile_number="9876543210",
        )

        org_node = OrgNode.objects.create(
            company=company,
            node_type="BUSINESS_UNIT",
            code="TEST-ORG",
            name="Test Organization Node",
        )

        reporting_period = ReportingPeriod.objects.create(
            name="FY 2026",
            period_type="ANNUAL",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
        )

        uploaded_file = self.create_excel_file()

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.post(
            reverse("import-batch-upload"),
            {
                "file": uploaded_file,
                "import_type": ImportBatch.ImportType.ANSWERS,
                "org_node": str(org_node.pk),
                "reporting_period": str(reporting_period.pk),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        batch = ImportBatch.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            batch.org_node_id,
            org_node.pk,
        )

        self.assertEqual(
            batch.reporting_period_id,
            reporting_period.pk,
        )

        self.assertEqual(
            response.data["org_node"],
            org_node.pk,
        )

        self.assertEqual(
            response.data["reporting_period"],
            reporting_period.pk,
        )

    def test_upload_rejects_unknown_org_node(self):
        uploaded_file = self.create_excel_file()

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.post(
            reverse("import-batch-upload"),
            {
                "file": uploaded_file,
                "import_type": ImportBatch.ImportType.ANSWERS,
                "org_node": str(uuid.uuid4()),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            ImportBatch.objects.exists()
        )

    def test_upload_rejects_unknown_reporting_period(self):
        uploaded_file = self.create_excel_file()

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.post(
            reverse("import-batch-upload"),
            {
                "file": uploaded_file,
                "import_type": ImportBatch.ImportType.ANSWERS,
                "reporting_period": str(uuid.uuid4()),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            ImportBatch.objects.exists()
        )

    def test_batch_rows_are_paginated(self):
        batch = self.create_batch_directly(
            user=self.uploader,
            rows=[
                {
                    "row_number": index + 2,
                    "raw_data": {
                        "facility_code": f"FAC-{index + 1:03d}",
                        "quantity": index + 1,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                }
                for index in range(25)
            ],
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            25,
        )

        self.assertEqual(
            len(response.data["results"]),
            20,
        )

        self.assertIsNotNone(
            response.data["next"],
        )


    def test_batch_rows_can_be_filtered_by_status(self):
        batch = self.create_batch_directly(
            user=self.uploader,
            rows=[
                {
                    "row_number": 2,
                    "raw_data": {
                        "facility_code": "FAC-001",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                },
                {
                    "row_number": 3,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 10,
                    },
                    "status": ImportRow.Status.ERROR,
                    "errors": {
                        "facility_code": [
                            "This field is required."
                        ]
                    },
                },
                {
                    "row_number": 4,
                    "raw_data": {
                        "facility_code": "",
                        "quantity": 20,
                    },
                    "status": ImportRow.Status.ERROR,
                    "errors": {
                        "facility_code": [
                            "This field is required."
                        ]
                    },
                },
            ],
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            ),
            {
                "status": ImportRow.Status.ERROR,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        self.assertEqual(
            len(response.data["results"]),
            2,
        )

        for row in response.data["results"]:
            self.assertEqual(
                row["status"],
                ImportRow.Status.ERROR,
            )


    def test_batch_rows_reject_invalid_status_filter(self):
        batch = self.create_batch_directly(
            user=self.uploader,
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            ),
            {
                "status": "INVALID_STATUS",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "status",
            response.data,
        )


    def test_batch_rows_support_custom_page_size(self):
        batch = self.create_batch_directly(
            user=self.uploader,
            rows=[
                {
                    "row_number": index + 2,
                    "raw_data": {
                        "facility_code": f"FAC-{index + 1:03d}",
                        "quantity": index + 1,
                    },
                    "status": ImportRow.Status.VALID,
                    "errors": {},
                }
                for index in range(10)
            ],
        )

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.get(
            reverse(
                "import-batch-rows",
                kwargs={
                    "batch_id": batch.pk,
                },
            ),
            {
                "page_size": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            10,
        )

        self.assertEqual(
            len(response.data["results"]),
            5,
        )