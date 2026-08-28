from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.accounts.services.rbac import RBACService
from apps.data_capture.authorization import has_scoped_permission
from apps.data_capture.models import (
    Answer,
    DataRequest,
    DataRequestStatus,
    SubmissionStatus,
)
from apps.data_capture.services.lifecycle import (
    DataCaptureLifecycleService,
)
from apps.data_capture.services.campaigns import (
    CollectionCampaignService,
)
from apps.data_capture.validation import validate_typed_value
from apps.datapoints.models import (
    Datapoint,
    DatapointDataType,
    DatapointOption,
    Unit,
)
from apps.imports.handlers import ImportHandler
from apps.organizations.models import OrgNode
from apps.periods.models import Status as PeriodStatus


class AnswersImportHandler(ImportHandler):
    """
    Production handler for the canonical M5 Answers import.

    Validation is read-only with respect to M5 business records.
    Destination Answer writes happen only during commit().
    """

    SUPPORTED_TYPES = {
        DatapointDataType.DECIMAL,
        DatapointDataType.INTEGER,
        DatapointDataType.TEXT,
        DatapointDataType.LONG_TEXT,
        DatapointDataType.BOOLEAN,
        DatapointDataType.SELECT,
        DatapointDataType.DATE,
    }

    TRUE_VALUES = {
        "true",
        "yes",
        "y",
        "1",
    }

    FALSE_VALUES = {
        "false",
        "no",
        "n",
        "0",
    }

    def validate_row(self, raw_data, *, batch=None):
        """
        Validate one canonical Answers import row.

        No M5 destination records are created or updated here.
        """

        normalized = dict(raw_data)
        errors = {}

        if batch is None:
            return normalized, {
                "batch": "Import batch context is required."
            }

        # ---------------------------------------------------------
        # 1. datapoint_code
        # ---------------------------------------------------------

        datapoint_code = self._clean_string(
            raw_data.get("datapoint_code")
        )

        if not datapoint_code:
            errors["datapoint_code"] = (
                "datapoint_code is required."
            )
            return normalized, errors

        datapoint = (
            Datapoint.objects
            .select_related(
                "module",
                "unit_family",
                "default_unit",
            )
            .filter(
                code=datapoint_code,
                is_active=True,
            )
            .first()
        )

        if datapoint is None:
            errors["datapoint_code"] = (
                "Active canonical datapoint was not found."
            )
            return normalized, errors

        if datapoint.data_type == DatapointDataType.TABLE:
            errors["datapoint_code"] = (
                "TABLE datapoints are not supported by "
                "the ANSWERS import."
            )
            return normalized, errors

        if datapoint.data_type not in self.SUPPORTED_TYPES:
            errors["datapoint_code"] = (
                f"Unsupported datapoint type: "
                f"{datapoint.data_type}."
            )
            return normalized, errors

        # ---------------------------------------------------------
        # 2. Batch module must match datapoint module
        # ---------------------------------------------------------

        if (
            batch.module_code
            and batch.module_code != datapoint.module.code
        ):
            errors["datapoint_code"] = (
                "Datapoint does not belong to the "
                "import batch module."
            )

        # ---------------------------------------------------------
        # 3. ReportingPeriod
        # ---------------------------------------------------------

        reporting_period = batch.reporting_period

        if reporting_period is None:
            errors["reporting_period"] = (
                "ANSWERS import requires an ImportBatch "
                "ReportingPeriod."
            )
        elif not reporting_period.is_active:
            errors["reporting_period"] = (
                "ReportingPeriod is inactive."
            )
        elif reporting_period.status != PeriodStatus.OPEN:
            errors["reporting_period"] = (
                "ReportingPeriod is locked or closed."
            )

        # ---------------------------------------------------------
        # 4. OrgNode
        # ---------------------------------------------------------

        org_node = self._resolve_org_node(
            raw_data.get("org_node_code"),
            batch,
            errors,
        )

        if org_node is not None:
            try:
                CollectionCampaignService._validate_collection_level(
                    datapoint,
                    org_node,
                )
            except ValidationError as exc:
                errors.update(
                    self._validation_error_dict(
                        exc,
                        "org_node",
                    )
                )

        # ---------------------------------------------------------
        # 5. Authorization / DataRequest / Submission
        # ---------------------------------------------------------

        data_request = None
        submission = None

        if (
            reporting_period is not None
            and org_node is not None
        ):
            # -----------------------------------------------------
            # 5a. Target-scope authorization
            # -----------------------------------------------------

            if not self._uploader_can_import_scope(
                batch.uploaded_by,
                org_node,
            ):
                errors["authorization"] = (
                    "Uploader is not authorized to import "
                    "into this OrgNode."
                )

            # -----------------------------------------------------
            # 5b. DataRequest / Submission
            # -----------------------------------------------------

            data_request = (
                DataRequest.objects
                .select_related(
                    "datapoint",
                    "org_node",
                    "reporting_period",
                    "submission",
                    "assignee",
                )
                .filter(
                    datapoint=datapoint,
                    org_node=org_node,
                    reporting_period=reporting_period,
                )
                .first()
            )

            if data_request is None:
                errors["data_request"] = (
                    "No matching DataRequest exists for "
                    "this datapoint, OrgNode and "
                    "ReportingPeriod."
                )
            else:
                if data_request.status != DataRequestStatus.OPEN:
                    errors["data_request"] = (
                        "DataRequest is not open for editing."
                    )

                submission = getattr(
                    data_request,
                    "submission",
                    None,
                )

                if submission is None:
                    errors["submission"] = (
                        "DataRequest has no current Submission."
                    )
                elif submission.status != SubmissionStatus.DRAFT:
                    errors["submission"] = (
                        "Only DRAFT submissions may be "
                        "populated by ANSWERS import."
                    )

                # -------------------------------------------------
                # 6. DataRequest-level authorization
                # -------------------------------------------------

                if not self._uploader_can_import(
                    batch.uploaded_by,
                    data_request,
                ):
                    errors["authorization"] = (
                        "Uploader is not authorized to import "
                        "into this DataRequest."
                    )
                
        # ---------------------------------------------------------
        # 7. Unit
        # ---------------------------------------------------------

        unit = self._resolve_unit(
            raw_data.get("unit_code"),
            datapoint,
            errors,
        )

        # ---------------------------------------------------------
        # 8. Value
        # ---------------------------------------------------------

        normalized_value = None

        try:
            normalized_value = self._normalize_value(
                raw_data.get("value"),
                datapoint.data_type,
            )
        except ValidationError as exc:
            errors.update(
                self._validation_error_dict(
                    exc,
                    "value",
                )
            )

        # ---------------------------------------------------------
        # 9. SELECT option
        # ---------------------------------------------------------

        selected_option = None

        if (
            datapoint.data_type
            == DatapointDataType.SELECT
            and normalized_value is not None
        ):
            selected_option = self._resolve_select_option(
                normalized_value,
                datapoint,
            )

            if selected_option is None:
                errors["value"] = (
                    "Value does not resolve to an "
                    "active option for this datapoint."
                )

        # ---------------------------------------------------------
        # 10. Reuse M5 typed-value validation
        # ---------------------------------------------------------

        if submission is not None and not errors:
            answer = Answer(
                submission=submission,
                entered_by=batch.uploaded_by,
                unit=unit,
            )

            self._apply_typed_value(
                answer,
                datapoint.data_type,
                normalized_value,
                selected_option,
            )

            try:
                validate_typed_value(
                    answer,
                    definition=datapoint,
                )
            except ValidationError as exc:
                errors.update(
                    self._validation_error_dict(
                        exc,
                        "value",
                    )
                )

        # ---------------------------------------------------------
        # 11. Store canonical normalized values only.
        # ---------------------------------------------------------

        if not errors:
            normalized["datapoint_code"] = datapoint.code
            normalized["value"] = self._json_value(
                normalized_value
            )

            if unit is not None:
                normalized["unit_code"] = unit.code
            else:
                normalized["unit_code"] = None

            if org_node is not None:
                normalized["org_node_code"] = org_node.code

        return normalized, errors

    def validate_batch(self, rows):
        """
        Reject duplicate datapoint + OrgNode rows in the same workbook.

        The first occurrence is accepted.
        Any later occurrence is rejected as a duplicate.
        """

        seen = {}

        for row in rows.order_by("row_number"):
            if row.status == "ERROR":
                continue

            data = row.raw_data

            datapoint_code = data.get("datapoint_code")
            org_node_code = data.get("org_node_code")

            key = (
                datapoint_code,
                org_node_code,
            )

            if key in seen:
                first_row = seen[key]

                row.errors = {
                    **(row.errors or {}),
                    "duplicate": (
                        "Duplicate ANSWERS row for the same "
                        "datapoint and OrgNode in this workbook. "
                        f"First occurrence is row {first_row}."
                    ),
                }

                row.status = "ERROR"

                row.save(
                    update_fields=[
                        "errors",
                        "status",
                    ]
                )

            else:
                seen[key] = row.row_number

    def commit(self, batch):
        """
        Persist validated ANSWERS rows into the canonical M5 Answer records.

        Validation must already have completed successfully before this
        method is called. Destination writes happen only here.

        ImportBatchService.commit() provides the surrounding transaction,
        so any failure rolls back all Answer writes and the ImportBatch
        lifecycle changes.
        """

        rows = (
            batch.rows
            .filter(status="VALID")
            .order_by("row_number")
        )

        for row in rows:
            data = row.raw_data

            datapoint_code = data["datapoint_code"]
            org_node_code = data["org_node_code"]
            value = data.get("value")
            unit_code = data.get("unit_code")

            datapoint = (
                Datapoint.objects
                .select_related("default_unit")
                .get(
                    code=datapoint_code,
                    is_active=True,
                )
            )

            org_node = OrgNode.objects.get(
                code=org_node_code,
                is_active=True,
            )

            reporting_period = batch.reporting_period
            if reporting_period is None:
                raise ValidationError(
                    "ANSWERS import requires an ImportBatch ReportingPeriod."
                )

            if not reporting_period.is_active:
                raise ValidationError(
                    "ReportingPeriod is inactive."
                )

            if reporting_period.status != PeriodStatus.OPEN:
                raise ValidationError(
                    "ReportingPeriod is locked or closed."
                )

            data_request = (
                DataRequest.objects
                .select_for_update()
                .select_related(
                    "datapoint",
                    "org_node",
                    "reporting_period",
                    "submission",
                    "assignee",
                )
                .get(
                    datapoint=datapoint,
                    org_node=org_node,
                    reporting_period=reporting_period,
                )
            )

            # Re-check authorization at commit time.
            # Authorization may have changed after validation.
            if not self._uploader_can_import(
                batch.uploaded_by,
                data_request,
            ):
                raise ValidationError(
                    {
                        "authorization": (
                            f"Uploader is not authorized to import "
                            f"into the DataRequest for row "
                            f"{row.row_number}."
                        )
                    }
                )

            submission = data_request.submission

            if submission is None:
                raise ValidationError(
                    f"DataRequest for row {row.row_number} "
                    "has no current Submission."
                )

            if submission.status != SubmissionStatus.DRAFT:
                raise ValidationError(
                    f"Submission for row {row.row_number} "
                    "is not editable."
                )

            unit = None

            if unit_code:
                unit = (
                    Unit.objects
                    .select_related("family")
                    .filter(
                        code=unit_code,
                        is_active=True,
                    )
                    .first()
                )

                if unit is None:
                    raise ValidationError(
                        f"Active canonical unit was not found for "
                        f"row {row.row_number}."
                    )

                if datapoint.unit_family_id is None:
                    raise ValidationError(
                        f"Datapoint for row {row.row_number} "
                        "does not accept a unit."
                    )

                if unit.family_id != datapoint.unit_family_id:
                    raise ValidationError(
                        f"Unit for row {row.row_number} does not belong "
                        "to the datapoint unit family."
                    )

            elif datapoint.unit_family_id is not None:
                raise ValidationError(
                    f"unit_code is required for row {row.row_number}."
                )

            data_type = datapoint.data_type

            # Build the typed value expected by the canonical M5 service.
            values = {
                "decimal_value": None,
                "integer_value": None,
                "text_value": "",
                "boolean_value": None,
                "selected_option": None,
                "date_value": None,
                "unit": unit,
            }

            if data_type == DatapointDataType.DECIMAL:
                values["decimal_value"] = Decimal(str(value))

            elif data_type == DatapointDataType.INTEGER:
                values["integer_value"] = int(value)

            elif data_type in {
                DatapointDataType.TEXT,
                DatapointDataType.LONG_TEXT,
            }:
                values["text_value"] = str(value)

            elif data_type == DatapointDataType.BOOLEAN:
                values["boolean_value"] = self._coerce_boolean(value)

            elif data_type == DatapointDataType.SELECT:
                selected_option = self._resolve_select_option(
                    value,
                    datapoint,
                )

                if selected_option is None:
                    raise ValidationError(
                        f"Value for row {row.row_number} does not resolve "
                        "to an active option for this datapoint."
                    )
                values["selected_option"] = selected_option

            elif data_type == DatapointDataType.DATE:
                values["date_value"] = self._coerce_date(value)

            else:
                raise ValidationError(
                    f"Unsupported datapoint type for row "
                    f"{row.row_number}: {data_type}"
                )

            answer=DataCaptureLifecycleService.save_scalar_answer(
                submission,
                actor=batch.uploaded_by,
                **values,
            )
            row.answer = answer
            row.save(update_fields=["answer"])

    # =============================================================
    # Helpers
    # =============================================================

    @staticmethod
    def _resolve_select_option(
        value,
        datapoint,
    ):
        return (
            DatapointOption.objects
            .filter(
                datapoint=datapoint,
                code=str(value).strip(),
                is_active=True,
            )
            .first()
        )

    @staticmethod
    def _coerce_boolean(value):
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()

        if normalized in AnswersImportHandler.TRUE_VALUES:
            return True

        if normalized in AnswersImportHandler.FALSE_VALUES:
            return False

        raise ValidationError(
            "Value must be a valid boolean."
        )


    @staticmethod
    def _coerce_date(value):
        from datetime import date, datetime

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                "Value must be a valid ISO date."
            ) from exc
    @staticmethod
    def _clean_string(value):
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    @staticmethod
    def _validation_error_dict(exc, default_key):
        if default_key == "value":
            if hasattr(exc, "message_dict"):
                messages = []

                for value in exc.message_dict.values():
                    if isinstance(value, (list, tuple)):
                        messages.extend(value)
                    else:
                        messages.append(value)

                return {
                    "value": messages
                }

            return {
                "value": exc.messages
            }

        if hasattr(exc, "message_dict"):
            return {
                key: value
                for key, value in exc.message_dict.items()
            }

        return {
            default_key: exc.messages
        }

    @staticmethod
    def _resolve_org_node(
        org_node_code,
        batch,
        errors,
    ):
        if batch.org_node_id:
            if not org_node_code:
                return batch.org_node

            if (
                batch.org_node.code
                != str(org_node_code).strip()
            ):
                errors["org_node_code"] = (
                    "org_node_code conflicts with the "
                    "ImportBatch OrgNode."
                )
                return None

            return batch.org_node

        code = (
            str(org_node_code).strip()
            if org_node_code is not None
            else ""
        )

        if not code:
            errors["org_node_code"] = (
                "org_node_code is required when the "
                "ImportBatch has no fixed OrgNode."
            )
            return None

        matches = (
            OrgNode.objects
            .filter(
                code=code,
                is_active=True,
            )
        )

        if matches.count() != 1:
            errors["org_node_code"] = (
                "org_node_code must resolve to exactly "
                "one active OrgNode."
            )
            return None

        return matches.first()

    @staticmethod
    def _resolve_unit(
        unit_code,
        datapoint,
        errors,
    ):
        code = (
            str(unit_code).strip()
            if unit_code is not None
            else ""
        )

        if datapoint.unit_family_id:
            if not code:
                errors["unit_code"] = (
                    "unit_code is required for this "
                    "datapoint."
                )
                return None

            unit = (
                Unit.objects
                .select_related("family")
                .filter(
                    code=code,
                    is_active=True,
                )
                .first()
            )

            if unit is None:
                errors["unit_code"] = (
                    "Active canonical unit was not found."
                )
                return None

            if unit.family_id != datapoint.unit_family_id:
                errors["unit_code"] = (
                    "Unit does not belong to the "
                    "datapoint unit family."
                )
                return None

            return unit

        if code:
            errors["unit_code"] = (
                "This datapoint does not accept a unit."
            )

        return None

    @classmethod
    def _normalize_value(
        cls,
        value,
        data_type,
    ):
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if value == "":
                return None

        if data_type == DatapointDataType.DECIMAL:
            try:
                return Decimal(str(value))
            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ) as exc:
                raise ValidationError(
                    {"value": "Value must be a valid decimal."}
                ) from exc

        if data_type == DatapointDataType.INTEGER:
            try:
                decimal_value = Decimal(str(value))
            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ) as exc:
                raise ValidationError(
                    {"value": "Value must be a valid integer."}
                ) from exc

            if decimal_value != decimal_value.to_integral_value():
                raise ValidationError(
                    {"value": "Value must be a whole integer."}
                )

            return int(decimal_value)

        if data_type in {
            DatapointDataType.TEXT,
            DatapointDataType.LONG_TEXT,
        }:
            return str(value)

        if data_type == DatapointDataType.BOOLEAN:
            if isinstance(value, bool):
                return value

            normalized = str(value).strip().lower()

            if normalized in cls.TRUE_VALUES:
                return True

            if normalized in cls.FALSE_VALUES:
                return False

            raise ValidationError(
                {
                    "value": (
                        "Boolean value must be one of "
                        "true/false, yes/no, y/n or 1/0."
                    )
                }
            )

        if data_type == DatapointDataType.SELECT:
            return str(value).strip()

        if data_type == DatapointDataType.DATE:
            if isinstance(value, datetime):
                return value.date()

            if isinstance(value, date):
                return value

            try:
                return date.fromisoformat(
                    str(value).strip()
                )
            except ValueError as exc:
                raise ValidationError(
                    {
                        "value": (
                            "Date must use ISO format "
                            "YYYY-MM-DD."
                        )
                    }
                ) from exc

        raise ValidationError(
            {
                "value": (
                    f"Unsupported datapoint type: "
                    f"{data_type}."
                )
            }
        )

    @staticmethod
    def _apply_typed_value(
        answer,
        data_type,
        value,
        selected_option,
    ):
        if value is None:
            return

        if data_type == DatapointDataType.DECIMAL:
            answer.decimal_value = value

        elif data_type == DatapointDataType.INTEGER:
            answer.integer_value = value

        elif data_type in {
            DatapointDataType.TEXT,
            DatapointDataType.LONG_TEXT,
        }:
            answer.text_value = value

        elif data_type == DatapointDataType.BOOLEAN:
            answer.boolean_value = value

        elif data_type == DatapointDataType.SELECT:
            answer.selected_option = selected_option

        elif data_type == DatapointDataType.DATE:
            answer.date_value = value

    @staticmethod
    def _json_value(value):
        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, (date, datetime)):
            return value.isoformat()

        return value

    @staticmethod
    def _uploader_can_import_scope(user, org_node):
        if user.is_superuser:
            return True

        if has_scoped_permission(
            user,
            "data.manage",
            org_node.id,
        ):
            return True

        return has_scoped_permission(
            user,
            "data.enter",
            org_node.id,
        )
    @staticmethod
    def _uploader_can_import(user, data_request):
        if user.is_superuser:
            return True

        org_node = data_request.org_node

        # Managers may import when their existing data.manage
        # capability covers the target OrgNode.
        if has_scoped_permission(
            user,
            "data.manage",
            org_node.id,
        ):
            return True

        # Entry capability is restricted to the assigned maker.
        if data_request.assignee_id != user.id:
            return False

        return has_scoped_permission(
            user,
            "data.enter",
            org_node.id,
        )