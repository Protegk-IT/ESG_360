import os
import tempfile
import uuid
from datetime import date, datetime
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from apps.organizations.models import OrgNode
from apps.companies.models import Company
from openpyxl import Workbook
from django.db import close_old_connections
from rest_framework.test import APIClient
from apps.data_capture.models import DataRequest, Submission
from apps.accounts.models import Permission, Role, UserRoleAssignment
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import (
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
)
from apps.imports.answers import AnswersImportHandler
from apps.modules.models import Module
from apps.periods.models import (
    PeriodType,
    ReportingPeriod,
    Status as PeriodStatus,
)

from apps.imports.handlers import (
    ImportHandlerRegistry,
    ImportHandler
)
from apps.imports.models import ImportBatch, ImportRow
from apps.imports.parser import ExcelParser, ImportFileError
from apps.imports.services import (
    ImportBatchService,
    ImportUploadService,
)
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError

from apps.data_capture.models import (
    Answer,
    DataRequest,
    DataRequestStatus,
    SubmissionStatus,
)
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    DatapointOption,
    Unit,
    UnitFamily,
)

User = get_user_model()

class FakeAnswersImportHandler(ImportHandler):
    """
    Test-only handler for validating the generic
    import-batch infrastructure.
    """

    def validate_row(self, raw_data,*, batch=None):
        errors = {}

        facility_code = raw_data.get("facility_code")
        quantity = raw_data.get("quantity")

        if not facility_code:
            errors["facility_code"] = [
                "Facility code is required."
            ]

        if quantity is None:
            errors["quantity"] = [
                "Quantity is required."
            ]
        elif quantity < 0:
            errors["quantity"] = [
                "Quantity cannot be negative."
            ]

        return raw_data, errors

    def commit(self, batch):
        return None

class TestDestinationCommitHandler(ImportHandler):
    """
    Test-only handler that performs a real database write and then
    raises an exception.

    The purpose is to verify that ImportBatchService.commit()
    rolls back destination-side database writes together with
    the batch transaction.
    """

    @staticmethod
    def validate_row(data,*,batch=None):
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
            result = list(self.parser.parse(path))
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
            result = list(self.parser.parse(path))
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
            result = list(self.parser.parse(path))
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
                list(self.parser.parse(path))
        finally:
            if os.path.exists(path):
                os.unlink(path)

        with self.assertRaises(ImportFileError):
            list(self.parser.parse(
                "does-not-exist.xlsx"
            ))

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
            result = list(self.parser.parse(path))
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

        result = list(self.parser.parse(uploaded_file))

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

    def test_file_like_object_must_have_xlsx_extension(self):
        uploaded_file = SimpleUploadedFile(
            "import_test.csv",
            b"facility_code,quantity\nFAC-001,10",
            content_type="text/csv",
        )

        with self.assertRaisesMessage(
            ImportFileError,
            "Unsupported file type. Only .xlsx files are supported.",
        ):
            list(self.parser.parse(uploaded_file))


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
            list(self.parser.parse(oversized_file))
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

    def test_upload_rejects_inactive_org_node(self):
        company = Company.objects.create(
            company_name="Inactive Node Company",
            company_code="INACT001",
            contact_person="Test User",
            email="inactive@example.com",
            mobile_number="9876543210",
        )

        org_node = OrgNode.objects.create(
            company=company,
            node_type="BUSINESS_UNIT",
            code="INACTIVE-ORG",
            name="Inactive Organization Node",
            is_active=False,
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
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "org_node",
            response.data,
        )

        self.assertIn(
            "inactive",
            str(response.data).lower(),
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

    def test_upload_rejects_inactive_reporting_period(self):
        reporting_period = ReportingPeriod.objects.create(
            name="Inactive FY 2026",
            period_type="ANNUAL",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_active=False,
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
                "reporting_period": str(reporting_period.pk),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "reporting_period",
            response.data,
        )

        self.assertIn(
            "inactive",
            str(response.data).lower(),
        )

        self.assertFalse(
            ImportBatch.objects.exists()
        )

    def test_upload_allows_missing_optional_context(self):
        uploaded_file = self.create_excel_file()

        self.client.force_authenticate(
            user=self.uploader,
        )

        response = self.client.post(
            reverse("import-batch-upload"),
            {
                "file": uploaded_file,
                "import_type": ImportBatch.ImportType.ANSWERS,
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

        self.assertIsNone(
            batch.org_node_id
        )

        self.assertIsNone(
            batch.reporting_period_id
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


class AnswersImportHandlerTests(TestCase):
    """
    Production ANSWERS import handler tests.

    Covers:
    - canonical datapoint validation
    - scalar datatype validation
    - unit validation
    - OrgNode/reporting-period context
    - DataRequest/submission lifecycle
    - authorization/scope
    - duplicate rows
    - validation read-only behavior
    - commit behavior
    - existing draft update/idempotency
    - transaction rollback
    - second commit protection
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="answers-import-user",
            password="TestPassword123!",
        )

        self.company = Company.objects.create(
            company_name="Answers Import Test Company",
            company_code="ANS-TEST",
            contact_person="Test User",
            mobile_number="9999999999",
            email="answers@example.com",
        )

        self.org_node = OrgNode.objects.get(
            company=self.company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        )

        enter = Permission.objects.create(
            code="data.enter",
            name="Enter data",
            module_code="data",
            action="EDIT",
        )

        submit = Permission.objects.create(
            code="data.submit",
            name="Submit data",
            module_code="data",
            action="APPROVE",
        )

        capture_role = Role.objects.create(
            role_code="answers-import-capture",
            role_name="Answers Import Capture",
        )

        capture_role.permissions.add(enter, submit)

        UserRoleAssignment.objects.create(
            user=self.user,
            role=capture_role,
            org_node=self.org_node,
        )

        self.module = Module.objects.create(
            code="energy",
            name="Energy",
            is_enabled=True,
        )

        self.other_module = Module.objects.create(
            code="water",
            name="Water",
            is_enabled=True,
        )

        self.category = DatapointCategory.objects.create(
            code="ENERGY_CATEGORY",
            name="Energy Category",
            module=self.module,
            is_active=True,
        )

        self.reporting_period = ReportingPeriod.objects.create(
            name="FY 2026",
            period_type=PeriodType.ANNUAL,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=PeriodStatus.OPEN,
            is_active=True,
        )

        self.batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=self.user,
        )

        self.handler = AnswersImportHandler()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def create_datapoint(
        self,
        *,
        code="ENERGY_TOTAL",
        data_type=DatapointDataType.DECIMAL,
        module=None,
        is_active=True,
        collection_level=CollectionLevel.ANY,
        unit_family=None,
        default_unit=None,
        validation_metadata=None,
        is_required=False,
    ):
        if module is None:
            module = self.module

        category = self.category

        if module != self.module:
            category = DatapointCategory.objects.create(
                code=f"{module.code.upper()}_CATEGORY",
                name=f"{module.name} Category",
                module=module,
                is_active=True,
            )

        return Datapoint.objects.create(
            code=code,
            category=category,
            module=module,
            label=code,
            data_type=data_type,
            collection_level=collection_level,
            frequency=CollectionFrequency.ANNUAL,
            is_required=is_required,
            is_active=is_active,
            unit_family=unit_family,
            default_unit=default_unit,
            validation_metadata=validation_metadata or {},
        )

    def create_request(self, datapoint, *, assignee=None):
        return DataCaptureLifecycleService.create_request(
            actor=self.user,
            datapoint=datapoint,
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            assignee=assignee or self.user,
        )

    def validate(self, row, batch=None):
        return self.handler.validate_row(
            row,
            batch=batch or self.batch,
        )

    def add_import_row(
        self,
        raw_data,
        *,
        row_number,
        batch=None,
        status=ImportRow.Status.VALID,
    ):
        return ImportRow.objects.create(
            batch=batch or self.batch,
            row_number=row_number,
            raw_data=raw_data,
            status=status,
        )

    def validate_batch(self, batch=None):
        batch = batch or self.batch
        return ImportBatchService.validate_batch(batch)

    def commit_batch(self, batch=None):
        batch = batch or self.batch
        return ImportBatchService.commit(batch)

    def create_energy_units(self):
        family = UnitFamily.objects.create(
            code="ENERGY",
            name="Energy",
        )

        kwh = Unit.objects.create(
            family=family,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        mwh = Unit.objects.create(
            family=family,
            code="MWH",
            name="Megawatt-hour",
            factor_to_base=Decimal("1000"),
        )

        return family, kwh, mwh

    # ------------------------------------------------------------------
    # Datapoint validation
    # ------------------------------------------------------------------

    def test_active_canonical_datapoint_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_TOTAL",
            data_type=DatapointDataType.DECIMAL,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            normalized["datapoint_code"],
            datapoint.code,
        )
        self.assertEqual(
            normalized["org_node_code"],
            self.org_node.code,
        )

    def test_unknown_datapoint_is_rejected(self):
        normalized, errors = self.validate(
            {
                "datapoint_code": "DOES_NOT_EXIST",
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("datapoint_code", errors)

    def test_inactive_datapoint_is_rejected(self):
        datapoint = self.create_datapoint(
            code="INACTIVE_ENERGY",
            data_type=DatapointDataType.DECIMAL,
            is_active=False,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("datapoint_code", errors)

    def test_table_datapoint_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_TABLE",
            data_type=DatapointDataType.TABLE,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "some value",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("datapoint_code", errors)
        self.assertIn(
            "TABLE",
            str(errors["datapoint_code"]).upper(),
        )

    def test_datapoint_from_wrong_module_is_rejected(self):
        datapoint = self.create_datapoint(
            code="WATER_TOTAL",
            data_type=DatapointDataType.DECIMAL,
            module=self.other_module,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("datapoint_code", errors)

    def test_batch_without_module_code_does_not_reject_matching_datapoint(self):
        datapoint = self.create_datapoint(
            code="NO_BATCH_MODULE",
            data_type=DatapointDataType.DECIMAL,
        )

        self.create_request(datapoint)

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=None,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertNotIn("datapoint_code", errors)

    def test_datapoint_module_mismatch_returns_expected_error(self):
        datapoint = self.create_datapoint(
            code="WATER_MODULE_DATAPOINT",
            data_type=DatapointDataType.DECIMAL,
            module=self.other_module,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("datapoint_code", errors)
        self.assertEqual(
            errors["datapoint_code"],
            "Datapoint does not belong to the import batch module.",
        )
    # ------------------------------------------------------------------
    # Datatype/value validation
    # ------------------------------------------------------------------

    def test_decimal_value_is_normalized(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DECIMAL",
            data_type=DatapointDataType.DECIMAL,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            normalized["value"],
            "125.50",
        )

    def test_invalid_decimal_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DECIMAL",
            data_type=DatapointDataType.DECIMAL,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "abc",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_decimal_validation_metadata_is_enforced(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DECIMAL_LIMIT",
            data_type=DatapointDataType.DECIMAL,
            validation_metadata={
                "min": 0,
                "max": 1000,
            },
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "1500",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_decimal_validation_metadata_accepts_valid_value(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DECIMAL_LIMIT",
            data_type=DatapointDataType.DECIMAL,
            validation_metadata={
                "min": 0,
                "max": 1000,
            },
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "999.99",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})

    def test_integer_value_is_normalized(self):
        datapoint = self.create_datapoint(
            code="ENERGY_INTEGER",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(normalized["value"], 125)

    def test_fractional_integer_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_INTEGER",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.5",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_integer_validation_metadata_is_enforced(self):
        datapoint = self.create_datapoint(
            code="ENERGY_INTEGER_LIMIT",
            data_type=DatapointDataType.INTEGER,
            validation_metadata={
                "min": 0,
                "max": 100,
            },
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "101",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_text_value_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_TEXT",
            data_type=DatapointDataType.TEXT,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "  Renewable energy  ",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            normalized["value"],
            "Renewable energy",
        )

    def test_long_text_value_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_LONG_TEXT",
            data_type=DatapointDataType.LONG_TEXT,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "Long narrative answer",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})

    def test_boolean_yes_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_BOOLEAN",
            data_type=DatapointDataType.BOOLEAN,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "yes",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertTrue(normalized["value"])

    def test_boolean_no_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_BOOLEAN",
            data_type=DatapointDataType.BOOLEAN,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "no",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertFalse(normalized["value"])

    def test_invalid_boolean_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_BOOLEAN",
            data_type=DatapointDataType.BOOLEAN,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "maybe",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_date_value_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DATE",
            data_type=DatapointDataType.DATE,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "2026-08-26",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            normalized["value"],
            date(2026, 8, 26).isoformat(),
        )

    def test_invalid_date_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_DATE",
            data_type=DatapointDataType.DATE,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "26/08/2026",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------

    def test_select_with_active_option_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENERGY_SOURCE",
            data_type=DatapointDataType.SELECT,
        )

        DatapointOption.objects.create(
            datapoint=datapoint,
            code="GRID",
            label="Grid",
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "GRID",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(normalized["value"], "GRID")

    def test_select_with_unknown_option_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_SOURCE",
            data_type=DatapointDataType.SELECT,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "UNKNOWN",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    def test_inactive_select_option_is_rejected(self):
        datapoint = self.create_datapoint(
            code="ENERGY_SOURCE",
            data_type=DatapointDataType.SELECT,
        )

        DatapointOption.objects.create(
            datapoint=datapoint,
            code="GRID",
            label="Grid",
            is_active=False,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "GRID",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("value", errors)

    # ------------------------------------------------------------------
    # Unit validation
    # ------------------------------------------------------------------

    def test_required_unit_is_accepted_from_same_family(self):
        family, kwh, mwh = self.create_energy_units()

        datapoint = self.create_datapoint(
            code="ENERGY_WITH_UNIT",
            data_type=DatapointDataType.DECIMAL,
            unit_family=family,
            default_unit=kwh,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "unit_code": "MWH",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            normalized["unit_code"],
            "MWH",
        )

    def test_required_unit_is_rejected_when_missing(self):
        family, kwh, mwh = self.create_energy_units()

        datapoint = self.create_datapoint(
            code="ENERGY_WITH_UNIT",
            data_type=DatapointDataType.DECIMAL,
            unit_family=family,
            default_unit=kwh,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("unit_code", errors)

    def test_inactive_unit_is_rejected(self):
        family, kwh, mwh = self.create_energy_units()

        mwh.is_active = False
        mwh.save(update_fields=["is_active", "updated_at"])

        datapoint = self.create_datapoint(
            code="ENERGY_WITH_UNIT",
            data_type=DatapointDataType.DECIMAL,
            unit_family=family,
            default_unit=kwh,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "unit_code": "MWH",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("unit_code", errors)

    def test_incompatible_unit_family_is_rejected(self):
        energy_family, kwh, mwh = self.create_energy_units()

        mass_family = UnitFamily.objects.create(
            code="MASS",
            name="Mass",
        )

        Unit.objects.create(
            family=mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        datapoint = self.create_datapoint(
            code="ENERGY_WITH_UNIT",
            data_type=DatapointDataType.DECIMAL,
            unit_family=energy_family,
            default_unit=kwh,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "unit_code": "KG",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("unit_code", errors)

    def test_commit_rechecks_unit_family(self):
        energy_family, kwh, mwh = self.create_energy_units()

        mass_family = UnitFamily.objects.create(
            code="COMMIT_MASS",
            name="Commit Mass",
        )

        kg = Unit.objects.create(
            family=mass_family,
            code="COMMIT_KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        datapoint = self.create_datapoint(
            code="COMMIT_UNIT_FAMILY",
            data_type=DatapointDataType.DECIMAL,
            unit_family=energy_family,
            default_unit=kwh,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "100",
                "unit_code": "MWH",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()

        # Change the unit relationship after validation.
        mwh.family = mass_family
        mwh.save(
            update_fields=["family", "updated_at"]
        )

        with self.assertRaises(ValidationError):
            self.commit_batch()

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )

    # ------------------------------------------------------------------
    # Reporting period
    # ------------------------------------------------------------------

    def test_missing_reporting_period_is_rejected(self):
        datapoint = self.create_datapoint()

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=self.org_node,
            reporting_period=None,
            module_code=self.module.code,
            uploaded_by=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertIn("reporting_period", errors)

    def test_inactive_reporting_period_is_rejected(self):
        datapoint = self.create_datapoint()

        self.reporting_period.is_active = False
        self.reporting_period.save(
            update_fields=["is_active", "updated_at"]
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("reporting_period", errors)

    def test_locked_reporting_period_is_rejected(self):
        datapoint = self.create_datapoint()

        self.reporting_period.status = PeriodStatus.LOCKED
        self.reporting_period.save(
            update_fields=["status", "updated_at"]
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("reporting_period", errors)

    def test_commit_rechecks_reporting_period_lock(self):
        datapoint = self.create_datapoint(
            code="COMMIT_PERIOD_RECHECK",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()

        self.reporting_period.status = PeriodStatus.LOCKED
        self.reporting_period.save(
            update_fields=["status", "updated_at"]
        )

        with self.assertRaises(ValidationError):
            self.commit_batch()

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )

        self.batch.refresh_from_db()

        self.assertNotEqual(
            self.batch.status,
            ImportBatch.Status.COMMITTED,
        )

    def test_commit_rejects_select_option_that_becomes_inactive(self):
        datapoint = self.create_datapoint(
            code="COMMIT_SELECT_INACTIVE",
            data_type=DatapointDataType.SELECT,
        )

        option = DatapointOption.objects.create(
            datapoint=datapoint,
            code="GRID",
            label="Grid",
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "GRID",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()

        option.is_active = False
        option.save(update_fields=["is_active", "updated_at"])

        with self.assertRaises(ValidationError):
            self.commit_batch()

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )
    # ------------------------------------------------------------------
    # OrgNode/context
    # ------------------------------------------------------------------

    def test_conflicting_org_node_code_is_rejected(self):
        datapoint = self.create_datapoint()

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": "WRONG-NODE",
            }
        )

        self.assertIn("org_node_code", errors)

    

    def test_batch_without_org_node_requires_row_org_node_code(self):
        datapoint = self.create_datapoint()

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=None,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            uploaded_by=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
            },
            batch=batch,
        )

        self.assertIn("org_node_code", errors)

    def test_batch_without_org_node_rejects_cross_scope_row_org_node(self):
        other_company = Company.objects.create(
            company_name="Other Company",
            company_code="OTHER-ROW-SCOPE",
            contact_person="Other User",
            mobile_number="7777777777",
            email="other-row@example.com",
        )

        other_org_node = OrgNode.objects.get(
            company=other_company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        )

        datapoint = self.create_datapoint(
            code="ROW_CROSS_SCOPE",
            data_type=DatapointDataType.INTEGER,
        )

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=None,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": other_org_node.code,
            },
            batch=batch,
        )

        self.assertIn("authorization", errors)

    def test_collection_level_mismatch_is_rejected(self):
        datapoint = self.create_datapoint(
            code="FACILITY_ONLY",
            data_type=DatapointDataType.INTEGER,
            collection_level=CollectionLevel.FACILITY,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("org_node", errors)
    # ------------------------------------------------------------------
    # DataRequest / Submission
    # ------------------------------------------------------------------

    def test_missing_data_request_is_rejected(self):
        datapoint = self.create_datapoint()

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("data_request", errors)

    def test_closed_data_request_is_rejected(self):
        datapoint = self.create_datapoint()

        request = self.create_request(datapoint)

        DataCaptureLifecycleService.submit(
            request.submission,
            actor=self.user,
        )

        reviewer = User.objects.create_user(
            username="answers-import-reviewer",
            password="TestPassword123!",
        )

        DataCaptureLifecycleService.approve(
            request.submission,
            actor=reviewer,
        )

        request.refresh_from_db()

        self.assertEqual(
            request.status,
            DataRequestStatus.COMPLETED,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("data_request", errors)

    def test_import_cannot_update_approved_submission(self):
        datapoint = self.create_datapoint(
            code="APPROVED_PROTECTED",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=self.user,
            integer_value=10,
        )

        DataCaptureLifecycleService.submit(
            request.submission,
            actor=self.user,
        )

        reviewer = User.objects.create_user(
            username="approved-reviewer",
            password="TestPassword123!",
        )

        DataCaptureLifecycleService.approve(
            request.submission,
            actor=reviewer,
        )

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "999",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "999",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("data_request", errors)

    def test_submitted_submission_is_rejected(self):
        datapoint = self.create_datapoint(
            code="SUBMITTED_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        submission = request.submission

        DataCaptureLifecycleService.save_scalar_answer(
            submission,
            actor=self.user,
            integer_value=10,
        )

        DataCaptureLifecycleService.submit(
            submission,
            actor=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertIn("submission", errors)

    # ------------------------------------------------------------------
    # Validation must not write Answer
    # ------------------------------------------------------------------

    def test_validation_does_not_create_answer(self):
        datapoint = self.create_datapoint(
            code="VALIDATION_ONLY",
            data_type=DatapointDataType.DECIMAL,
        )

        request = self.create_request(datapoint)

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertEqual(errors, {})

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )

    # ------------------------------------------------------------------
    # Duplicate rows
    # ------------------------------------------------------------------

    def test_duplicate_rows_in_same_batch_are_rejected(self):
        datapoint = self.create_datapoint(
            code="DUPLICATE_IMPORT",
            data_type=DatapointDataType.DECIMAL,
        )

        self.create_request(datapoint)

        batch = self.batch

        row1 = self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
            batch=batch,
        )

        row2 = self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "20",
                "org_node_code": self.org_node.code,
            },
            row_number=3,
            batch=batch,
        )

        result = self.validate_batch(batch)

        row1.refresh_from_db()
        row2.refresh_from_db()
        batch.refresh_from_db()

        self.assertEqual(
            row1.status,
            ImportRow.Status.ERROR,
        )
        self.assertEqual(
            row2.status,
            ImportRow.Status.ERROR,
        )
        self.assertIn("duplicate", row1.errors)
        self.assertIn("duplicate", row2.errors)
        self.assertEqual(
            batch.status,
            ImportBatch.Status.FAILED,
        )

    # ------------------------------------------------------------------
    # Commit: DECIMAL
    # ------------------------------------------------------------------

    def test_commit_creates_decimal_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_DECIMAL",
            data_type=DatapointDataType.DECIMAL,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "125.50",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()

        self.batch.refresh_from_db()

        self.assertEqual(
            self.batch.status,
            ImportBatch.Status.VALIDATED,
        )

        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.decimal_value,
            Decimal("125.50"),
        )

        request.submission.refresh_from_db()

        self.assertEqual(
            request.submission.status,
            SubmissionStatus.DRAFT,
        )

        self.batch.refresh_from_db()

        self.assertEqual(
            self.batch.status,
            ImportBatch.Status.COMMITTED,
        )

    # ------------------------------------------------------------------
    # Commit: INTEGER
    # ------------------------------------------------------------------

    def test_commit_creates_integer_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_INTEGER",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "125",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.integer_value,
            125,
        )

    # ------------------------------------------------------------------
    # Commit: TEXT/LONG_TEXT
    # ------------------------------------------------------------------

    def test_commit_creates_text_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_TEXT",
            data_type=DatapointDataType.TEXT,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "Energy consumption note",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.text_value,
            "Energy consumption note",
        )

    def test_commit_creates_long_text_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_LONG_TEXT",
            data_type=DatapointDataType.LONG_TEXT,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "Long narrative answer",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.text_value,
            "Long narrative answer",
        )

    # ------------------------------------------------------------------
    # Commit: BOOLEAN
    # ------------------------------------------------------------------

    def test_commit_creates_boolean_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_BOOLEAN",
            data_type=DatapointDataType.BOOLEAN,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "yes",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertTrue(answer.boolean_value)

    # ------------------------------------------------------------------
    # Commit: SELECT
    # ------------------------------------------------------------------

    def test_commit_creates_select_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_SELECT",
            data_type=DatapointDataType.SELECT,
        )

        option = DatapointOption.objects.create(
            datapoint=datapoint,
            code="GRID",
            label="Grid",
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "GRID",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.selected_option_id,
            option.id,
        )

    # ------------------------------------------------------------------
    # Commit: DATE
    # ------------------------------------------------------------------

    def test_commit_creates_date_draft_answer(self):
        datapoint = self.create_datapoint(
            code="COMMIT_DATE",
            data_type=DatapointDataType.DATE,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "2026-08-26",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        self.assertEqual(
            answer.date_value,
            date(2026,8,26),
        )

    # ------------------------------------------------------------------
    # Existing draft / idempotency
    # ------------------------------------------------------------------

    def test_commit_updates_existing_draft_without_duplicate_answer(self):
        datapoint = self.create_datapoint(
            code="UPDATE_EXISTING",
            data_type=DatapointDataType.DECIMAL,
        )

        request = self.create_request(datapoint)

        existing_answer = DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=self.user,
            decimal_value=Decimal("10.00"),
        )

        self.assertEqual(
            Answer.objects.filter(
                submission=request.submission
            ).count(),
            1,
        )

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "25.50",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        request.submission.refresh_from_db()

        self.assertEqual(
            Answer.objects.filter(
                submission=request.submission
            ).count(),
            1,
        )

        existing_answer.refresh_from_db()

        self.assertEqual(
            existing_answer.decimal_value,
            Decimal("25.50"),
        )

    def test_later_import_updates_existing_draft_without_duplicate_answer(self):
        datapoint = self.create_datapoint(
            code="LATER_IMPORT_UPDATE",
            data_type=DatapointDataType.DECIMAL,
        )

        request = self.create_request(datapoint)

        existing_answer = DataCaptureLifecycleService.save_scalar_answer(
            request.submission,
            actor=self.user,
            decimal_value=Decimal("10.00"),
        )

        first_batch = self.batch

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "20.00",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
            batch=first_batch,
        )

        self.validate_batch(first_batch)
        self.commit_batch(first_batch)

        second_batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers-second.xlsx",
            file_path="imports/answers-second.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=self.user,
        )

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "30.00",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
            batch=second_batch,
        )

        self.validate_batch(second_batch)
        self.commit_batch(second_batch)

        existing_answer.refresh_from_db()

        self.assertEqual(
            existing_answer.decimal_value,
            Decimal("30.00"),
        )

        self.assertEqual(
            Answer.objects.filter(
                submission=request.submission
            ).count(),
            1,
        )
    # ------------------------------------------------------------------
    # DRAFT-only lifecycle
    # ------------------------------------------------------------------

    def test_commit_never_submits_draft_submission(self):
        datapoint = self.create_datapoint(
            code="DRAFT_ONLY",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "100",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        request.submission.refresh_from_db()

        self.assertEqual(
            request.submission.status,
            SubmissionStatus.DRAFT,
        )

    # ------------------------------------------------------------------
    # Second commit
    # ------------------------------------------------------------------

    def test_second_commit_of_same_batch_is_rejected(self):
        datapoint = self.create_datapoint(
            code="SECOND_COMMIT",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        self.batch.refresh_from_db()

        self.assertEqual(
            self.batch.status,
            ImportBatch.Status.COMMITTED,
        )

        with self.assertRaises(ValidationError):
            self.commit_batch()

    # ------------------------------------------------------------------
    # Commit rollback
    # ------------------------------------------------------------------

    def test_commit_rolls_back_all_answer_writes_when_later_row_fails(self):
        datapoint1 = self.create_datapoint(
            code="ROLLBACK_ONE",
            data_type=DatapointDataType.INTEGER,
        )

        datapoint2 = self.create_datapoint(
            code="ROLLBACK_TWO",
            data_type=DatapointDataType.INTEGER,
        )

        request1 = self.create_request(datapoint1)
        request2 = self.create_request(datapoint2)

        self.add_import_row(
            {
                "datapoint_code": datapoint1.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.add_import_row(
            {
                "datapoint_code": datapoint2.code,
                "value": "20",
                "org_node_code": self.org_node.code,
            },
            row_number=3,
        )

        self.validate_batch()

        original_save = (
            DataCaptureLifecycleService.save_scalar_answer
        )

        call_count = {"value": 0}

        def failing_save(submission, *, actor, **values):
            call_count["value"] += 1

            if call_count["value"] == 2:
                raise RuntimeError(
                    "Simulated second-row commit failure"
                )

            return original_save(
                submission,
                actor=actor,
                **values,
            )

        with patch.object(
            DataCaptureLifecycleService,
            "save_scalar_answer",
            side_effect=failing_save,
        ):
            with self.assertRaises(RuntimeError):
                self.commit_batch()

        self.assertFalse(
            Answer.objects.filter(
                submission=request1.submission
            ).exists()
        )

        self.assertFalse(
            Answer.objects.filter(
                submission=request2.submission
            ).exists()
        )

        self.batch.refresh_from_db()

        self.assertNotEqual(
            self.batch.status,
            ImportBatch.Status.COMMITTED,
        )

        self.assertIsNone(
            self.batch.committed_at,
        )

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def test_uploader_with_target_scope_and_data_manage_is_accepted(self):
        manager = User.objects.create_user(
            username="answers-import-manager",
            password="TestPassword123!",
        )

        manage_permission = Permission.objects.create(
            code="data.manage",
            name="Manage data",
            module_code="data",
            action="EDIT",
        )

        manager_role = Role.objects.create(
            role_code="answers-import-manager-role",
            role_name="Answers Import Manager",
        )

        manager_role.permissions.add(manage_permission)

        UserRoleAssignment.objects.create(
            user=manager,
            role=manager_role,
            org_node=self.org_node,
        )

        datapoint = self.create_datapoint(
            code="MANAGER_SCOPE_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers-manager.xlsx",
            file_path="imports/answers-manager.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=manager,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertNotIn("authorization", errors)

    def test_uploader_with_target_scope_and_data_enter_is_accepted(self):
        datapoint = self.create_datapoint(
            code="ENTER_SCOPE_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertNotIn("authorization", errors)

    def test_data_enter_user_cannot_import_unassigned_data_request(self):
        other_user = User.objects.create_user(
            username="unassigned-enter-user",
            password="TestPassword123!",
        )

        enter_permission = Permission.objects.get(
            code="data.enter",
        )

        enter_role = Role.objects.create(
            role_code="unassigned-enter-role",
            role_name="Unassigned Enter Role",
        )

        enter_role.permissions.add(enter_permission)

        UserRoleAssignment.objects.create(
            user=other_user,
            role=enter_role,
            org_node=self.org_node,
        )

        datapoint = self.create_datapoint(
            code="UNASSIGNED_ENTER_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(
            datapoint,
            assignee=self.user,
        )

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers-unassigned.xlsx",
            file_path="imports/answers-unassigned.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=other_user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertIn("authorization", errors)
    def test_assigned_data_enter_user_can_import_data_request(self):
        datapoint = self.create_datapoint(
            code="ASSIGNED_ENTER_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(
            datapoint,
            assignee=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            }
        )

        self.assertNotIn("authorization", errors)

    def test_superuser_can_import_regardless_of_scope_permissions(self):
        superuser = User.objects.create_superuser(
            username="answers-import-superuser",
            password="TestPassword123!",
            email="superuser@example.com",
        )

        datapoint = self.create_datapoint(
            code="SUPERUSER_IMPORT",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers-superuser.xlsx",
            file_path="imports/answers-superuser.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=superuser,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertNotIn("authorization", errors)
    def test_uploader_without_target_scope_is_rejected(self):
        unauthorized_user = User.objects.create_user(
            username="unauthorized-import-user",
            password="TestPassword123!",
        )

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=unauthorized_user,
        )

        datapoint = self.create_datapoint(
            code="UNAUTHORIZED",
            data_type=DatapointDataType.INTEGER,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertIn(
            "authorization",
            errors,
        )

    def test_commit_rechecks_authorization_after_validation(self):
        datapoint = self.create_datapoint(
            code="COMMIT_AUTH_RECHECK",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()

        # Remove the uploader's permission after validation.
        assignment = UserRoleAssignment.objects.get(
            user=self.user,
            org_node=self.org_node,
        )

        assignment.role.permissions.clear()

        with self.assertRaises(ValidationError):
            self.commit_batch()

        self.assertFalse(
            Answer.objects.filter(
                submission=request.submission
            ).exists()
        )

    def test_permission_and_scope_cannot_be_union_from_different_assignments(self):
        user = User.objects.create_user(
            username="split-assignment-user",
            password="TestPassword123!",
        )

        datapoint = self.create_datapoint(
            code="NON_UNION_SCOPE",
            data_type=DatapointDataType.INTEGER,
        )

        self.create_request(datapoint)

        # Assignment 1: has permission but no target scope.
        permission_role = Role.objects.create(
            role_code="permission-only-role",
            role_name="Permission Only Role",
        )

        enter_permission = Permission.objects.create(
            code="data.enter.nonunion",
            name="Enter data nonunion",
            module_code="data",
            action="EDIT",
        )

        permission_role.permissions.add(enter_permission)

        UserRoleAssignment.objects.create(
            user=user,
            role=permission_role,
            org_node=None,
        )

        # Assignment 2: has target scope but does not have the
        # required permission.
        scope_role = Role.objects.create(
            role_code="scope-only-role",
            role_name="Scope Only Role",
        )

        UserRoleAssignment.objects.create(
            user=user,
            role=scope_role,
            org_node=self.org_node,
        )

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=self.org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": self.org_node.code,
            },
            batch=batch,
        )

        self.assertIn("authorization", errors)

    def test_cross_scope_org_node_is_rejected(self):
        other_company = Company.objects.create(
            company_name="Other Company",
            company_code="OTHER-TEST",
            contact_person="Other User",
            mobile_number="8888888888",
            email="other@example.com",
        )

        other_org_node = OrgNode.objects.get(
            company=other_company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        )

        datapoint = self.create_datapoint(
            code="CROSS_SCOPE",
            data_type=DatapointDataType.INTEGER,
        )

        # Create the DataRequest directly so the test can construct a
        # cross-scope fixture. DataCaptureLifecycleService.create_request()
        # intentionally rejects this combination before the import
        # authorization check can be reached.
        request = DataRequest.objects.create(
            datapoint=datapoint,
            org_node=other_org_node,
            reporting_period=self.reporting_period,
            assignee=self.user,
            requested_by=self.user,
        )

        Submission.objects.create(
            data_request=request,
        )

        batch = ImportBatch.objects.create(
            import_type=ImportBatch.ImportType.ANSWERS,
            file_name="answers.xlsx",
            file_path="imports/answers.xlsx",
            org_node=other_org_node,
            reporting_period=self.reporting_period,
            module_code=self.module.code,
            status=ImportBatch.Status.UPLOADED,
            uploaded_by=self.user,
        )

        normalized, errors = self.validate(
            {
                "datapoint_code": datapoint.code,
                "value": "10",
                "org_node_code": other_org_node.code,
            },
            batch=batch,
        )

        self.assertIn("authorization", errors)

    def test_commit_retains_import_row_answer_provenance(self):
        datapoint = self.create_datapoint(
            code="PROVENANCE_TEST",
            data_type=DatapointDataType.INTEGER,
        )

        request = self.create_request(datapoint)

        row = self.add_import_row(
            {
                "datapoint_code": datapoint.code,
                "value": "42",
                "org_node_code": self.org_node.code,
            },
            row_number=2,
        )

        self.validate_batch()
        self.commit_batch()

        answer = Answer.objects.get(
            submission=request.submission
        )

        row.refresh_from_db()

        self.assertEqual(
            row.answer_id,
            answer.id,
        )

        self.assertEqual(
            row.batch_id,
            self.batch.id,
        )