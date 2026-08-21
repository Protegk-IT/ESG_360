from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.data_capture.models import (
    Answer,
    AnswerTableCell,
    AnswerTableRow,
    EvidenceFile,
    Submission,
    SubmissionEvent,
    SubmissionStatus,
)
from apps.data_capture.services.lifecycle import DataCaptureLifecycleService
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
    Unit,
    UnitFamily,
)
from apps.modules.models import ESGPillar, Module
from apps.organizations.models import OrgNode
from apps.periods.models import PeriodType, ReportingPeriod, Status as PeriodStatus


class DataCaptureDomainTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.requester = User.objects.create_user(username="requester", password="pass")
        cls.maker = User.objects.create_user(username="maker", password="pass")
        cls.reviewer = User.objects.create_user(username="reviewer", password="pass")
        cls.other_user = User.objects.create_user(username="other", password="pass")
        cls.company = Company.objects.create(
            company_name="Capture Co",
            company_code="CAP",
            contact_person="Capture Owner",
            email="owner@example.test",
            mobile_number="1234567890",
        )
        cls.org_node = OrgNode.objects.get(
            company=cls.company,
            node_type="LEGAL_ENTITY",
            parent__isnull=True,
        )
        cls.period = ReportingPeriod.objects.create(
            name="FY 2026",
            period_type=PeriodType.ANNUAL,
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
        )
        cls.module = Module.objects.create(code="energy", name="Energy", esg_pillar=ESGPillar.E)
        cls.category = DatapointCategory.objects.create(
            code="CAPTURE_ENERGY", name="Capture energy", module=cls.module
        )
        cls.energy_family = UnitFamily.objects.create(code="ENERGY", name="Energy")
        cls.kwh = Unit.objects.create(
            family=cls.energy_family, code="KWH", name="Kilowatt-hour", factor_to_base=Decimal("1"), is_base_unit=True
        )
        cls.mwh = Unit.objects.create(
            family=cls.energy_family, code="MWH", name="Megawatt-hour", factor_to_base=Decimal("1000")
        )
        enter = Permission.objects.create(
            code="data.enter", name="Enter data", module_code="data", action="EDIT"
        )
        submit = Permission.objects.create(
            code="data.submit", name="Submit data", module_code="data", action="APPROVE"
        )
        capture_role = Role.objects.create(role_code="capture", role_name="Capture")
        capture_role.permissions.add(enter, submit)
        UserRoleAssignment.objects.create(user=cls.maker, role=capture_role, org_node=cls.org_node)
        UserRoleAssignment.objects.create(user=cls.other_user, role=capture_role, org_node=cls.org_node)

    def datapoint(self, code, data_type, **kwargs):
        defaults = {
            "code": code,
            "category": self.category,
            "module": self.module,
            "label": code,
            "data_type": data_type,
            "collection_level": CollectionLevel.ORG_NODE,
            "frequency": CollectionFrequency.MONTHLY,
        }
        defaults.update(kwargs)
        return Datapoint.objects.create(**defaults)

    def request_for(self, datapoint, *, assignee=None):
        return DataCaptureLifecycleService.create_request(
            actor=self.requester,
            datapoint=datapoint,
            org_node=self.org_node,
            reporting_period=self.period,
            assignee=assignee or self.maker,
        )

    def test_request_derives_module_and_creates_durable_initial_history(self):
        request = self.request_for(self.datapoint("ENERGY_TOTAL", DatapointDataType.DECIMAL))

        self.assertEqual(request.module_code, "energy")
        self.assertEqual(request.events.count(), 2)
        self.assertEqual(request.submission.status, SubmissionStatus.DRAFT)
        self.assertEqual(
            list(request.submission.events.values_list("event_type", flat=True)),
            [SubmissionEvent.EventType.CREATED],
        )

    def test_request_rejects_inactive_definition_or_ineligible_assignee_and_status_bypass(self):
        inactive = self.datapoint("INACTIVE_CAPTURE", DatapointDataType.TEXT, is_active=False)
        with self.assertRaises(ValidationError):
            self.request_for(inactive)

        # Use real canonical codes on separate role assignments to prove that
        # assignment eligibility cannot union their scope or permissions.
        split_enter = Permission.objects.get(code="data.enter")
        split_submit = Permission.objects.get(code="data.submit")
        split_user = User.objects.create_user(username="split-capture", password="pass")
        enter_role = Role.objects.create(role_code="split-enter", role_name="Split enter")
        submit_role = Role.objects.create(role_code="split-submit", role_name="Split submit")
        enter_role.permissions.add(split_enter)
        submit_role.permissions.add(split_submit)
        UserRoleAssignment.objects.create(user=split_user, role=enter_role, org_node=self.org_node)
        UserRoleAssignment.objects.create(user=split_user, role=submit_role, org_node=self.org_node)
        with self.assertRaises(ValidationError):
            self.request_for(self.datapoint("INELIGIBLE_CAPTURE", DatapointDataType.TEXT), assignee=split_user)

        self.other_user.is_active = False
        self.other_user.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            self.request_for(self.datapoint("INACTIVE_ASSIGNEE", DatapointDataType.TEXT), assignee=self.other_user)

        request = self.request_for(self.datapoint("STATUS_GUARD", DatapointDataType.TEXT))
        request.status = "COMPLETED"
        with self.assertRaises(ValidationError):
            request.save()
        request.status = "OPEN"
        request.assignee = self.other_user
        with self.assertRaises(ValidationError):
            request.save()
        with self.assertRaises(ValidationError):
            request.submission.delete()
        answer = DataCaptureLifecycleService.save_scalar_answer(
            request.submission, actor=self.maker, text_value="Historical value"
        )
        with self.assertRaises(ValidationError):
            answer.delete()

    def test_dynamic_table_partial_row_update_preserves_existing_label(self):
        table = self.datapoint("DYNAMIC_UPDATE", DatapointDataType.TABLE, allow_dynamic_rows=True)
        column = DatapointTableColumn.objects.create(
            datapoint=table, code="NOTE", label="Note", data_type=DatapointDataType.TEXT, display_order=1
        )
        submission = self.request_for(table).submission
        row = DataCaptureLifecycleService.save_table_row(
            submission, actor=self.maker, label="Original label", display_order=1,
            cells=({"column": column, "text_value": "Initial"},),
        )
        DataCaptureLifecycleService.save_table_row(
            submission, actor=self.maker, row=row,
            cells=({"column": column, "text_value": "Updated"},),
        )
        row.refresh_from_db()
        self.assertEqual(row.label, "Original label")
        self.assertEqual(row.cells.get().text_value, "Updated")

    def test_decimal_and_select_answers_are_typed_and_definition_validated(self):
        decimal_datapoint = self.datapoint(
            "ENERGY_TOTAL", DatapointDataType.DECIMAL,
            unit_family=self.energy_family,
            default_unit=self.kwh,
            validation_metadata={"min": "0"},
        )
        submission = self.request_for(decimal_datapoint).submission
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission, actor=self.maker, decimal_value=Decimal("1.25"), unit=self.mwh
        )
        self.assertEqual(answer.decimal_value, Decimal("1.25"))
        self.assertEqual(answer.unit, self.mwh)

        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("-1"), unit=self.kwh
            )

        select_datapoint = self.datapoint("ENERGY_SOURCE", DatapointDataType.SELECT)
        grid = DatapointOption.objects.create(datapoint=select_datapoint, code="GRID", label="Grid")
        other_datapoint = self.datapoint("OTHER_SOURCE", DatapointDataType.SELECT)
        other = DatapointOption.objects.create(datapoint=other_datapoint, code="OTHER", label="Other")
        select_submission = self.request_for(select_datapoint).submission
        DataCaptureLifecycleService.save_scalar_answer(
            select_submission, actor=self.maker, selected_option=grid
        )
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                select_submission, actor=self.maker, selected_option=other
            )

    def test_every_scalar_type_uses_only_its_canonical_storage_field(self):
        select_datapoint = self.datapoint("SCALAR_SELECT", DatapointDataType.SELECT)
        option = DatapointOption.objects.create(
            datapoint=select_datapoint, code="YES", label="Yes"
        )
        cases = (
            (
                self.datapoint(
                    "SCALAR_DECIMAL",
                    DatapointDataType.DECIMAL,
                    unit_family=self.energy_family,
                    default_unit=self.kwh,
                ),
                {"decimal_value": Decimal("3.50")},
                "decimal_value",
            ),
            (
                self.datapoint(
                    "SCALAR_INTEGER",
                    DatapointDataType.INTEGER,
                    unit_family=self.energy_family,
                    default_unit=self.kwh,
                ),
                {"integer_value": 3},
                "integer_value",
            ),
            (
                self.datapoint("SCALAR_TEXT", DatapointDataType.TEXT),
                {"text_value": "Reference"},
                "text_value",
            ),
            (
                self.datapoint("SCALAR_LONG_TEXT", DatapointDataType.LONG_TEXT),
                {"text_value": "Longer supporting explanation."},
                "text_value",
            ),
            (
                self.datapoint("SCALAR_BOOLEAN", DatapointDataType.BOOLEAN),
                {"boolean_value": False},
                "boolean_value",
            ),
            (select_datapoint, {"selected_option": option}, "selected_option"),
            (
                self.datapoint("SCALAR_DATE", DatapointDataType.DATE),
                {"date_value": date(2026, 4, 1)},
                "date_value",
            ),
        )

        for datapoint, values, expected_field in cases:
            with self.subTest(data_type=datapoint.data_type):
                answer = DataCaptureLifecycleService.save_scalar_answer(
                    self.request_for(datapoint).submission,
                    actor=self.maker,
                    **values,
                )
                self.assertEqual(getattr(answer, expected_field), values[expected_field])
                if datapoint.data_type in {DatapointDataType.DECIMAL, DatapointDataType.INTEGER}:
                    self.assertEqual(answer.unit, self.kwh)

    def test_wrong_type_values_and_numeric_unit_metadata_are_rejected_in_drafts(self):
        mass_family = UnitFamily.objects.create(code="MASS", name="Mass")
        kg = Unit.objects.create(
            family=mass_family, code="KG", name="Kilogram", factor_to_base=Decimal("1"), is_base_unit=True
        )
        decimal = self.datapoint(
            "PRECISE_DECIMAL",
            DatapointDataType.DECIMAL,
            unit_family=self.energy_family,
            default_unit=self.kwh,
            validation_metadata={"min": "1", "max": "5", "decimal_places": 2},
        )
        submission = self.request_for(decimal).submission
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, text_value="wrong type"
            )
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("1.234")
            )
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("0.99"), unit=self.kwh
            )
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("2"), unit=kg
            )
        self.mwh.is_active = False
        self.mwh.save()
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("2"), unit=self.mwh
            )
        self.kwh.is_active = False
        self.kwh.save()
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(
                submission, actor=self.maker, decimal_value=Decimal("2")
            )

    def test_optional_blank_submission_is_allowed_but_required_blank_submission_is_not(self):
        optional = self.datapoint("OPTIONAL_TEXT", DatapointDataType.TEXT, is_required=False)
        DataCaptureLifecycleService.submit(self.request_for(optional).submission, actor=self.maker)

        required = self.datapoint("REQUIRED_TEXT", DatapointDataType.TEXT, is_required=True)
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.submit(self.request_for(required).submission, actor=self.maker)

    def test_table_answers_use_fixed_rows_and_typed_normalized_cells(self):
        table = self.datapoint("ENERGY_TABLE", DatapointDataType.TABLE)
        source = DatapointTableColumn.objects.create(
            datapoint=table, code="SOURCE", label="Source", data_type=DatapointDataType.TEXT, is_required=True, display_order=1
        )
        quantity = DatapointTableColumn.objects.create(
            datapoint=table, code="QUANTITY", label="Quantity", data_type=DatapointDataType.DECIMAL,
            unit_family=self.energy_family, default_unit=self.kwh, is_required=True, display_order=2
        )
        fixed_row = DatapointTableRow.objects.create(
            datapoint=table, code="GRID", label="Grid", display_order=1
        )
        submission = self.request_for(table).submission

        row = DataCaptureLifecycleService.save_table_row(
            submission,
            actor=self.maker,
            definition_row=fixed_row,
            display_order=1,
            cells=(
                {"column": source, "text_value": "Grid electricity"},
                {"column": quantity, "decimal_value": Decimal("250"), "unit": self.kwh},
            ),
        )
        self.assertEqual(row.cells.count(), 2)
        self.assertTrue(AnswerTableCell.objects.filter(row=row, decimal_value=Decimal("250")).exists())
        DataCaptureLifecycleService.submit(submission, actor=self.maker)

    def test_table_submission_requires_values_for_required_cells_and_column_metadata(self):
        table = self.datapoint("VALIDATED_TABLE", DatapointDataType.TABLE, is_required=True)
        quantity = DatapointTableColumn.objects.create(
            datapoint=table,
            code="QUANTITY",
            label="Quantity",
            data_type=DatapointDataType.DECIMAL,
            unit_family=self.energy_family,
            default_unit=self.kwh,
            is_required=True,
            validation_metadata={"min": "0", "decimal_places": 2},
            display_order=1,
        )
        fixed_row = DatapointTableRow.objects.create(
            datapoint=table, code="TOTAL", label="Total", display_order=1
        )
        submission = self.request_for(table).submission
        DataCaptureLifecycleService.save_table_row(
            submission,
            actor=self.maker,
            definition_row=fixed_row,
            display_order=99,
            cells=({"column": quantity},),
        )
        row = submission.answer.table_rows.get()
        self.assertEqual(row.display_order, fixed_row.display_order)
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.submit(submission, actor=self.maker)
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_table_row(
                submission,
                actor=self.maker,
                definition_row=fixed_row,
                display_order=1,
                cells=({"column": quantity, "text_value": "wrong type"},),
            )
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_table_row(
                submission,
                actor=self.maker,
                definition_row=fixed_row,
                display_order=1,
                cells=({"column": quantity, "decimal_value": Decimal("1.234"), "unit": self.kwh},),
            )
        DataCaptureLifecycleService.save_table_row(
            submission,
            actor=self.maker,
            definition_row=fixed_row,
            display_order=1,
            cells=({"column": quantity, "decimal_value": Decimal("1.23")},),
        )
        self.assertEqual(submission.answer.table_rows.get().cells.get().unit, self.kwh)
        DataCaptureLifecycleService.submit(submission, actor=self.maker)

    def test_dynamic_rows_are_allowed_only_when_the_datapoint_allows_them(self):
        fixed = self.datapoint("FIXED_TABLE", DatapointDataType.TABLE)
        fixed_submission = self.request_for(fixed).submission
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_table_row(
                fixed_submission, actor=self.maker, label="User row", display_order=1
            )

        dynamic = self.datapoint(
            "DYNAMIC_TABLE",
            DatapointDataType.TABLE,
            allow_dynamic_rows=True,
            validation_metadata={"min_rows": 2},
        )
        description = DatapointTableColumn.objects.create(
            datapoint=dynamic, code="DESCRIPTION", label="Description", data_type=DatapointDataType.TEXT, display_order=1
        )
        dynamic_submission = self.request_for(dynamic).submission
        row = DataCaptureLifecycleService.save_table_row(
            dynamic_submission,
            actor=self.maker,
            label="Supplier supplied row",
            display_order=1,
            cells=({"column": description, "text_value": "Supplier A"},),
        )
        self.assertIsNone(row.definition_row)
        self.assertEqual(row.label, "Supplier supplied row")
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.submit(dynamic_submission, actor=self.maker)
        DataCaptureLifecycleService.save_table_row(
            dynamic_submission,
            actor=self.maker,
            label="Supplier supplied row two",
            display_order=2,
            cells=({"column": description, "text_value": "Supplier B"},),
        )
        DataCaptureLifecycleService.submit(dynamic_submission, actor=self.maker)

    def test_table_rows_and_cells_protect_against_duplicate_and_cross_table_structure(self):
        table = self.datapoint("TABLE_ONE", DatapointDataType.TABLE, allow_dynamic_rows=True)
        column = DatapointTableColumn.objects.create(
            datapoint=table, code="TEXT", label="Text", data_type=DatapointDataType.TEXT, display_order=1
        )
        other_table = self.datapoint("TABLE_TWO", DatapointDataType.TABLE, allow_dynamic_rows=True)
        other_column = DatapointTableColumn.objects.create(
            datapoint=other_table, code="OTHER", label="Other", data_type=DatapointDataType.TEXT, display_order=1
        )
        submission = self.request_for(table).submission
        row = DataCaptureLifecycleService.save_table_row(
            submission,
            actor=self.maker,
            label="Dynamic row",
            display_order=1,
            cells=({"column": column, "text_value": "Value"},),
        )
        with self.assertRaises(ValidationError):
            AnswerTableRow.objects.create(answer=submission.answer, label="Duplicate order", display_order=1)
        with self.assertRaises(ValidationError):
            AnswerTableCell.objects.create(row=row, column=column, text_value="Duplicate")
        with self.assertRaises(ValidationError):
            AnswerTableCell.objects.create(row=row, column=other_column, text_value="Wrong table")
        with self.assertRaises(ValidationError):
            row.delete()
        with self.assertRaises(ValidationError):
            row.cells.get().delete()

    def test_submit_reject_reopen_resubmit_approve_preserves_history(self):
        datapoint = self.datapoint(
            "ENERGY_TOTAL", DatapointDataType.INTEGER, is_required=True
        )
        submission = self.request_for(datapoint).submission
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.submit(submission, actor=self.maker)

        DataCaptureLifecycleService.save_scalar_answer(submission, actor=self.maker, integer_value=12)
        DataCaptureLifecycleService.submit(submission, actor=self.maker)
        with self.assertRaises(PermissionDenied):
            DataCaptureLifecycleService.approve(submission, actor=self.maker)
        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.reject(submission, actor=self.reviewer, reason="")

        DataCaptureLifecycleService.reject(submission, actor=self.reviewer, reason="Please attach source detail.")
        submission.refresh_from_db()
        self.assertEqual(submission.rejection_reason, "Please attach source detail.")
        DataCaptureLifecycleService.reopen(submission, actor=self.reviewer, reason="Maker may correct the source.")
        DataCaptureLifecycleService.save_scalar_answer(submission, actor=self.maker, integer_value=13)
        DataCaptureLifecycleService.submit(submission, actor=self.maker)
        DataCaptureLifecycleService.approve(submission, actor=self.reviewer)
        submission.refresh_from_db()

        self.assertEqual(submission.status, SubmissionStatus.APPROVED)
        self.assertEqual(submission.data_request.status, "COMPLETED")
        self.assertEqual(submission.rejection_reason, "Please attach source detail.")
        self.assertEqual(
            list(submission.events.values_list("event_type", flat=True)),
            ["CREATED", "DRAFT_SAVED", "SUBMITTED", "REJECTED", "REOPENED", "DRAFT_SAVED", "SUBMITTED", "APPROVED"],
        )
        event = submission.events.first()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_locked_period_blocks_draft_and_transition_writes(self):
        datapoint = self.datapoint("LOCKED_TOTAL", DatapointDataType.INTEGER)
        submission = self.request_for(datapoint).submission
        self.period.status = PeriodStatus.LOCKED
        self.period.save()

        with self.assertRaises(ValidationError):
            DataCaptureLifecycleService.save_scalar_answer(submission, actor=self.maker, integer_value=1)

    def test_only_assignee_can_edit_and_status_cannot_bypass_service(self):
        datapoint = self.datapoint("ASSIGNED_TOTAL", DatapointDataType.INTEGER)
        submission = self.request_for(datapoint).submission
        with self.assertRaises(PermissionDenied):
            DataCaptureLifecycleService.save_scalar_answer(submission, actor=self.other_user, integer_value=1)

        submission.status = SubmissionStatus.SUBMITTED
        with self.assertRaises(ValidationError):
            submission.save()

    def test_table_values_cannot_change_after_submission(self):
        table = self.datapoint("LOCKED_TABLE", DatapointDataType.TABLE, is_required=True)
        column = DatapointTableColumn.objects.create(
            datapoint=table, code="VALUE", label="Value", data_type=DatapointDataType.TEXT,
            is_required=True, display_order=1,
        )
        definition_row = DatapointTableRow.objects.create(
            datapoint=table, code="ROW", label="Row", display_order=1
        )
        submission = self.request_for(table).submission
        row = DataCaptureLifecycleService.save_table_row(
            submission,
            actor=self.maker,
            definition_row=definition_row,
            cells=({"column": column, "text_value": "Initial"},),
        )
        DataCaptureLifecycleService.submit(submission, actor=self.maker)
        row.label = "Mutated"
        with self.assertRaises(ValidationError):
            row.save()
        cell = row.cells.get()
        cell.text_value = "Mutated"
        with self.assertRaises(ValidationError):
            cell.save()

    def test_scalar_answer_cannot_change_after_submission(self):
        datapoint = self.datapoint("LOCKED_SCALAR", DatapointDataType.TEXT, is_required=True)
        submission = self.request_for(datapoint).submission
        answer = DataCaptureLifecycleService.save_scalar_answer(
            submission, actor=self.maker, text_value="Original"
        )
        DataCaptureLifecycleService.submit(submission, actor=self.maker)
        answer.text_value = "Mutated"
        with self.assertRaises(ValidationError):
            answer.save()

    def test_evidence_is_storage_backed_and_validates_target_and_type(self):
        datapoint = self.datapoint("EVIDENCE_TOTAL", DatapointDataType.INTEGER)
        submission = self.request_for(datapoint).submission
        answer = DataCaptureLifecycleService.save_scalar_answer(submission, actor=self.maker, integer_value=1)
        evidence = EvidenceFile(
            submission=submission,
            answer=answer,
            file=SimpleUploadedFile("source.pdf", b"pdf", content_type="application/pdf"),
            original_filename="source.pdf",
            content_type="application/pdf",
            size=3,
            uploaded_by=self.maker,
        )
        evidence.full_clean()

        bad = EvidenceFile(
            submission=submission,
            file=SimpleUploadedFile("script.exe", b"x", content_type="application/octet-stream"),
            original_filename="script.exe",
            content_type="application/octet-stream",
            size=1,
            uploaded_by=self.maker,
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_reassignment_is_only_possible_while_the_submission_is_draft(self):
        datapoint = self.datapoint("REASSIGN_TOTAL", DatapointDataType.INTEGER)
        request = self.request_for(datapoint)
        DataCaptureLifecycleService.reassign_request(request, actor=self.requester, assignee=self.other_user, reason="Coverage")
        request.refresh_from_db()
        self.assertEqual(request.assignee, self.other_user)
        self.assertEqual(request.events.count(), 3)
