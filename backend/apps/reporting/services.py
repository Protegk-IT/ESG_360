from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.data_capture.models import (
    AnswerTableCell,
    AnswerTableRow,
    DataRequest,
    SubmissionStatus,
)
from apps.datapoints.models import Datapoint, DatapointDataType

from .models import (
    ReportRun,
    FrameworkSnapshot,
    SnapshotNode,
    SnapshotMapping,
)


def freeze_report_run(report_run):
    """
    Freeze the current M7 framework structure for a ReportRun.

    Flow:

        ReportRun
            |
            | framework_version
            v
        FrameworkVersion
            |
            +--> Framework
            |
            +--> FrameworkNode
                    |
                    +--> DatapointMapping
                            |
                            +--> Datapoint

    The live M7 data is copied into immutable M8 snapshot records.

    The complete operation is transactional.

    If any part fails, the entire snapshot creation is rolled back.
    """

    if not isinstance(report_run, ReportRun):
        raise ValidationError(
            "freeze_report_run requires a ReportRun instance."
        )

    # --------------------------------------------------------------
    # 1. Reject re-freezing
    # --------------------------------------------------------------

    if report_run.is_frozen:
        raise ValidationError(
            "This report run has already been frozen."
        )

    if report_run.company_id is None:
        raise ValidationError(
            "A report run must have a company scope before it can be frozen."
        )

    # --------------------------------------------------------------
    # 2. Lock the ReportRun
    # --------------------------------------------------------------

    with transaction.atomic():

        report_run = (
            ReportRun.objects
            .select_for_update()
            .select_related(
                "framework_version",
                "framework_version__framework",
                "reporting_period",
            )
            .get(pk=report_run.pk)
        )

        # ----------------------------------------------------------
        # 3. Check again after acquiring the database lock
        # ----------------------------------------------------------

        if report_run.is_frozen:
            raise ValidationError(
                "This report run has already been frozen."
            )

        framework_version = report_run.framework_version
        framework = framework_version.framework
        frozen_at = timezone.now()

        # ----------------------------------------------------------
        # 4. Create the framework snapshot
        # ----------------------------------------------------------

        snapshot = FrameworkSnapshot.objects.create(
            report_run=report_run,
            source_framework_id=framework.id,
            source_framework_version_id=framework_version.id,
            framework_code=framework.code,
            framework_name=framework.name,
            version_code=framework_version.version_code,
            version_name=framework_version.version_name,
            frozen_at=frozen_at,
        )

        # ----------------------------------------------------------
        # 5. Read the live M7 framework nodes
        # ----------------------------------------------------------

        nodes = (
            framework_version.nodes
            .select_related("parent")
            .prefetch_related(
                "datapoint_mappings",
                "datapoint_mappings__datapoint",
            )
            .order_by(
                "path",
                "display_order",
                "code",
                "id",
            )
        )

        # ----------------------------------------------------------
        # 6. Create SnapshotNodes
        # ----------------------------------------------------------

        node_map = {}

        for node in nodes:
            snapshot_node = SnapshotNode.objects.create(
                snapshot=snapshot,
                source_node_id=node.id,
                code=node.code,
                title=node.title,
                description=node.description,
                instructions=node.instructions,
                node_type=node.node_type,
                display_order=node.display_order,
                depth=node.depth,
                path=node.path,
                response_format=node.response_format,
                is_answerable=node.is_answerable,
                is_core=node.is_core,
                is_active=node.is_active,
                metadata={},
            )

            node_map[node.id] = snapshot_node

        # ----------------------------------------------------------
        # 7. Establish parent relationships
        # ----------------------------------------------------------

        for node in nodes:

            if node.parent_id is None:
                continue

            snapshot_node = node_map[node.id]
            snapshot_parent = node_map.get(node.parent_id)

            if snapshot_parent is None:
                raise ValidationError(
                    (
                        "Framework snapshot cannot be created "
                        "because a node's parent is missing from "
                        "the selected framework version."
                    )
                )

            SnapshotNode.objects.filter(
                pk=snapshot_node.pk
            ).update(
                parent=snapshot_parent
            )

        # ----------------------------------------------------------
        # 8. Create SnapshotMappings
        # ----------------------------------------------------------

        for node in nodes:

            snapshot_node = node_map[node.id]

            mappings = sorted(
                node.datapoint_mappings.all(),
                key=lambda mapping: (
                    mapping.is_primary is not True,
                    mapping.datapoint.code,
                    mapping.id,
                ),
            )

            for display_order, mapping in enumerate(mappings):

                datapoint = mapping.datapoint

                SnapshotMapping.objects.create(
                    snapshot_node=snapshot_node,
                    source_mapping_id=mapping.id,
                    source_datapoint_id=datapoint.id,
                    canonical_datapoint_code=datapoint.code,
                    mapping_type=mapping.mapping_type,
                    aggregation=mapping.aggregation,
                    transform_expression=(
                        mapping.transform_expression
                    ),
                    is_primary=mapping.is_primary,
                    confidence=mapping.confidence,
                    mapping_note=mapping.mapping_note,
                    reviewed_at=mapping.reviewed_at,
                    display_order=display_order,
                    metadata={},
                )

        # ----------------------------------------------------------
        # 9. Mark ReportRun as frozen
        # ----------------------------------------------------------

        report_run.status = ReportRun.Status.FROZEN
        report_run.snapshot_frozen_at = frozen_at

        report_run.save(
            update_fields=[
                "status",
                "snapshot_frozen_at",
                "updated_at",
            ]
        )

        # ----------------------------------------------------------
        # 10. Return the completed frozen ReportRun
        # ----------------------------------------------------------

        return report_run


class CapturedValueProvider:
    """Provide approved M5 values without mutating M5 records."""

    SCALAR_FIELDS = {
        DatapointDataType.DECIMAL: "decimal_value",
        DatapointDataType.INTEGER: "integer_value",
        DatapointDataType.TEXT: "text_value",
        DatapointDataType.LONG_TEXT: "text_value",
        DatapointDataType.BOOLEAN: "boolean_value",
        DatapointDataType.SELECT: "selected_option",
        DatapointDataType.DATE: "date_value",
    }

    @staticmethod
    def _person(user):
        if user is None:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "name": user.get_full_name() or user.username,
        }

    @staticmethod
    def _unit(unit):
        if unit is None:
            return None
        return {
            "id": unit.id,
            "code": unit.code,
            "name": unit.name,
        }

    @classmethod
    def _typed_value(cls, record, definition):
        if definition.data_type == DatapointDataType.TABLE:
            rows = []
            answer = record.submission.answer
            for row in answer.table_rows.all():
                cells = []
                for cell in row.cells.all():
                    field_name = cls.SCALAR_FIELDS.get(cell.column.data_type)
                    value = getattr(cell, field_name, None) if field_name else None
                    if cell.column.data_type == DatapointDataType.SELECT:
                        option = cell.selected_option
                        value = (
                            {"id": option.id, "code": option.code, "label": option.label}
                            if option else None
                        )
                    cells.append({
                        "column_id": cell.column_id,
                        "column_code": cell.column.code,
                        "column_label": cell.column.label,
                        "data_type": cell.column.data_type,
                        "value": value,
                        "unit": cls._unit(cell.unit),
                    })
                rows.append({
                    "id": row.id,
                    "definition_row": (
                        {
                            "id": row.definition_row_id,
                            "code": row.definition_row.code,
                            "label": row.definition_row.label,
                        }
                        if row.definition_row else None
                    ),
                    "label": row.label,
                    "display_order": row.display_order,
                    "cells": cells,
                })
            return rows

        field_name = cls.SCALAR_FIELDS.get(definition.data_type)
        value = getattr(record.submission.answer, field_name, None) if field_name else None
        if definition.data_type in {DatapointDataType.TEXT, DatapointDataType.LONG_TEXT} and value == "":
            return None
        if definition.data_type == DatapointDataType.SELECT:
            option = record.submission.answer.selected_option
            return (
                {"id": option.id, "code": option.code, "label": option.label}
                if option else None
            )
        return value

    @classmethod
    def _record(cls, record, definition):
        answer = getattr(record.submission, "answer", None)
        value = cls._typed_value(record, definition) if answer else None
        resolved = value is not None and (definition.data_type != DatapointDataType.TABLE or value != [])
        return {
            "status": "RESOLVED" if resolved else "UNRESOLVED",
            "data_type": definition.data_type,
            "data_request_id": record.id,
            "submission_id": record.submission.id,
            "answer_id": answer.id if answer else None,
            "org_node_id": record.org_node_id,
            "org_node_name": record.org_node.name if record.org_node else None,
            "value": value,
            "unit": cls._unit(answer.unit if answer else None),
            "provenance": {
                "source_type": "CAPTURED",
                "approved_by": cls._person(record.submission.approved_by),
                "approved_at": record.submission.approved_at,
                "entered_by": cls._person(answer.entered_by if answer else None),
            },
        }

    @classmethod
    def resolve(cls, mappings, *, reporting_period, company):
        """Resolve frozen UUIDs; use frozen codes only for legacy snapshots.

        A SnapshotMapping written by M8 freeze has ``source_datapoint_id``.
        It is the historical identity and survives later M4 code changes.
        Snapshots without that value use the frozen code as a compatibility
        fallback only.
        """
        source_ids = {
            mapping.source_datapoint_id for mapping in mappings
            if mapping.source_datapoint_id is not None
        }
        legacy_codes = {
            mapping.canonical_datapoint_code for mapping in mappings
            if mapping.source_datapoint_id is None
        }
        definitions_by_id = {
            datapoint.id: datapoint
            for datapoint in Datapoint.objects.filter(id__in=source_ids)
        }
        definitions_by_legacy_code = {
            datapoint.code: datapoint
            for datapoint in Datapoint.objects.filter(code__in=legacy_codes)
        }
        table_cells = Prefetch(
            "cells",
            queryset=AnswerTableCell.objects.select_related(
                "column", "unit", "selected_option"
            ).order_by("column__display_order", "column__code", "id"),
        )
        table_rows = Prefetch(
            "submission__answer__table_rows",
            queryset=AnswerTableRow.objects.select_related(
                "definition_row"
            ).prefetch_related(table_cells).order_by("display_order", "created_at", "id"),
        )
        requests = (
            DataRequest.objects.filter(
                datapoint_id__in=source_ids,
                reporting_period=reporting_period,
                org_node__company=company,
                submission__status=SubmissionStatus.APPROVED,
            )
            .select_related(
                "datapoint", "org_node", "submission", "submission__approved_by",
                "submission__answer", "submission__answer__unit",
                "submission__answer__entered_by", "submission__answer__selected_option",
            )
            .prefetch_related(table_rows)
            .order_by("datapoint_id", "org_node__path", "org_node__name", "org_node__id", "id")
        )
        legacy_requests = DataRequest.objects.none()
        if legacy_codes:
            legacy_requests = (
                DataRequest.objects.filter(
                    datapoint__code__in=legacy_codes,
                    reporting_period=reporting_period,
                    org_node__company=company,
                    submission__status=SubmissionStatus.APPROVED,
                )
                .select_related(
                    "datapoint", "org_node", "submission", "submission__approved_by",
                    "submission__answer", "submission__answer__unit",
                    "submission__answer__entered_by", "submission__answer__selected_option",
                )
                .prefetch_related(table_rows)
                .order_by("datapoint__code", "org_node__path", "org_node__name", "org_node__id", "id")
            )
        values_by_identity = {("id", source_id): [] for source_id in source_ids}
        values_by_identity.update({("code", code): [] for code in legacy_codes})
        for record in requests:
            definition = definitions_by_id.get(record.datapoint_id, record.datapoint)
            values_by_identity[("id", record.datapoint_id)].append(cls._record(record, definition))
        for record in legacy_requests:
            definition = definitions_by_legacy_code.get(record.datapoint.code, record.datapoint)
            values_by_identity[("code", record.datapoint.code)].append(cls._record(record, definition))
        return values_by_identity, definitions_by_id, definitions_by_legacy_code


class ReportValueResolver:
    """Resolve frozen mappings through the approved captured-value provider."""

    @classmethod
    def build_dataset(cls, report_run):
        """
        Build the deterministic reporting dataset for a frozen
        ReportRun.

        The frozen M8 snapshot determines report ordering.

        Approved M5 submissions provide captured values.

        M6 calculated values are intentionally outside this resolver.
        """

        if not isinstance(report_run, ReportRun):
            raise ValidationError(
                "build_dataset requires a ReportRun instance."
            )

        # ----------------------------------------------------------
        # Reporting resolution only applies to frozen reports.
        # ----------------------------------------------------------

        if not report_run.is_frozen:
            raise ValidationError(
                "Report values can only be resolved for "
                "a frozen report run."
            )

        if report_run.company_id is None:
            raise ValidationError(
                "A report run must have a company scope to resolve values."
            )

        # ----------------------------------------------------------
        # Locate the frozen framework snapshot.
        # ----------------------------------------------------------

        try:
            snapshot = FrameworkSnapshot.objects.get(
                report_run=report_run,
            )
        except FrameworkSnapshot.DoesNotExist as exc:
            raise ValidationError(
                "A frozen report run must have a framework snapshot."
            ) from exc

        # ----------------------------------------------------------
        # IMPORTANT:
        #
        # M8 snapshot ordering controls report ordering.
        #
        # We do not order the report according to current M7
        # structures or current M5 structures.
        #
        # OrgNode ordering is only used inside one mapping when
        # several approved organizational values exist.
        # ----------------------------------------------------------

        mappings = list(
            SnapshotMapping.objects
            .filter(
                snapshot_node__snapshot=snapshot,
            )
            .select_related(
                "snapshot_node",
            )
            .order_by(
                "snapshot_node__path",
                "snapshot_node__display_order",
                "snapshot_node__code",
                "snapshot_node__id",
                "display_order",
                "canonical_datapoint_code",
                "id",
            )
        )

        values_by_identity, definitions_by_id, definitions_by_legacy_code = CapturedValueProvider.resolve(
            mappings,
            reporting_period=report_run.reporting_period,
            company=report_run.company,
        )
        dataset = []

        for mapping in mappings:
            if mapping.source_datapoint_id is not None:
                identity = ("id", mapping.source_datapoint_id)
                definition = definitions_by_id.get(mapping.source_datapoint_id)
            else:
                identity = ("code", mapping.canonical_datapoint_code)
                definition = definitions_by_legacy_code.get(mapping.canonical_datapoint_code)
            resolved_values = values_by_identity.get(identity, [])
            if not resolved_values:
                resolved_values = [{
                    "status": "UNRESOLVED",
                    "data_type": definition.data_type if definition else None,
                    "data_request_id": None,
                    "submission_id": None,
                    "answer_id": None,
                    "org_node_id": None,
                    "org_node_name": None,
                    "value": None,
                    "unit": None,
                    "provenance": {"source_type": "CAPTURED"},
                }]

            for resolved in resolved_values:

                dataset.append(
                    {
                        "snapshot_node_id": (
                            mapping.snapshot_node_id
                        ),
                        "snapshot_node_code": (
                            mapping.snapshot_node.code
                        ),
                        "snapshot_mapping_id": mapping.id,
                        "source_datapoint_id": (
                            mapping.source_datapoint_id
                        ),
                        "canonical_datapoint_code": (
                            mapping.canonical_datapoint_code
                        ),
                        **resolved,
                    }
                )

        return dataset
