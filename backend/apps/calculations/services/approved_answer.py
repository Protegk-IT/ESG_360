from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.data_capture.authorization import has_scoped_permission
from apps.data_capture.models import Answer, SubmissionStatus
from apps.datapoints.models import DatapointDataType

from apps.calculations.models import (
    CalculationResult,
    CalculationResultStatus,
    CalculationRule,
)
from apps.calculations.services.calculations import CalculationService
from apps.calculations.services.factor_selection import FactorSelectionService


class ApprovedAnswerCalculationService:
    """
    Calculates an approved M5 numeric Answer using the M6
    factor-selection and calculation services.

    This service does not persist CalculationResult.
    """

    SUPPORTED_DATA_TYPES = {
        DatapointDataType.DECIMAL,
        DatapointDataType.INTEGER,
    }

    @staticmethod
    def _ensure_actor_can_access_answer(actor, answer):
        if actor is None or getattr(actor, "is_superuser", False):
            return

        org_node_id = answer.submission.data_request.org_node_id
        if any(
            has_scoped_permission(actor, permission_code, org_node_id)
            for permission_code in ("data.manage", "data.approve")
        ):
            return

        raise PermissionDenied(
            "You do not have permission to calculate this answer in the current org scope."
        )

    @classmethod
    def calculate(
        cls,
        *,
        answer,
        calculation_date,
        geography=None,
        actor,
    ):
        answer = cls._load_answer(answer)
        cls._ensure_actor_can_access_answer(actor, answer)

        # ---------------------------------------------------------
        # APPROVED M5 ANSWER VALIDATION
        # ---------------------------------------------------------

        cls._validate_submission(answer)

        # ---------------------------------------------------------
        # DATAPOINT VALIDATION
        # ---------------------------------------------------------

        cls._validate_datapoint(answer)

        # ---------------------------------------------------------
        # GET NUMERIC INPUT
        # ---------------------------------------------------------

        quantity = cls._get_quantity(answer)
        quantity_unit = cls._get_quantity_unit(answer)

        # ---------------------------------------------------------
        # FIND CALCULATION RULE
        # ---------------------------------------------------------

        rule = cls._get_calculation_rule(answer)

        activity_key = rule.rule_metadata.get("activity_key")

        if not activity_key:
            raise ValidationError(
                {
                    "calculation_rule": (
                        "Calculation rule does not define an activity_key."
                    )
                }
            )

        # ---------------------------------------------------------
        # SELECT EMISSION FACTOR
        # ---------------------------------------------------------

        factor = FactorSelectionService.select_factor(
            activity_key=activity_key,
            calculation_date=calculation_date,
            geography=geography,
        )

        # ---------------------------------------------------------
        # PERFORM CALCULATION
        # ---------------------------------------------------------

        calculation = CalculationService.calculate(
            quantity=quantity,
            quantity_unit=quantity_unit,
            factor=factor,
            calculation_date=calculation_date,
            geography=geography,
        )

        # ---------------------------------------------------------
        # RETURN COMPLETE CALCULATION CONTEXT
        # ---------------------------------------------------------

        return {
            "answer": answer,
            "calculation_rule": rule,
            "activity_key": activity_key,
            "factor": factor,
            "calculation_date": calculation_date,
            "geography": geography,
            "actor": actor,
            **calculation,
        }

    # =============================================================
    # PRIVATE VALIDATION / LOOKUP METHODS
    # =============================================================

    @staticmethod
    def _load_answer(answer):
        return (
            Answer.objects
            .select_related(
                "submission",
                "submission__data_request",
                "submission__data_request__datapoint",
                "submission__data_request__org_node",
                "submission__data_request__reporting_period",
                "unit",
            )
            .get(pk=answer.pk)
        )

    @staticmethod
    def _validate_submission(answer):
        if answer.submission.status != SubmissionStatus.APPROVED:
            raise ValidationError(
                {
                    "answer": (
                        "Calculation is only allowed for an "
                        "approved submission."
                    )
                }
            )

    @classmethod
    def _validate_datapoint(cls, answer):
        if answer.datapoint.data_type not in cls.SUPPORTED_DATA_TYPES:
            raise ValidationError(
                {
                    "answer": (
                        "Only DECIMAL and INTEGER answers are "
                        "supported for M6 calculations."
                    )
                }
            )

    @staticmethod
    def _get_quantity(answer):
        if answer.datapoint.data_type == DatapointDataType.DECIMAL:
            quantity = answer.decimal_value
        else:
            quantity = answer.integer_value

        if quantity is None:
            raise ValidationError(
                {
                    "answer": "The approved numeric answer has no value."
                }
            )

        return Decimal(str(quantity))

    @staticmethod
    def _get_quantity_unit(answer):
        if answer.unit is None:
            raise ValidationError(
                {
                    "unit": (
                        "A unit is required for an M6 calculation."
                    )
                }
            )

        return answer.unit

    @staticmethod
    def _get_calculation_rule(answer):
        rules = list(
            CalculationRule.objects.filter(
                datapoint=answer.datapoint,
                is_active=True,
            )
        )

        if not rules:
            raise ValidationError(
                {
                    "calculation_rule": (
                        "No active calculation rule exists "
                        "for this datapoint."
                    )
                }
            )

        if len(rules) > 1:
            raise ValidationError(
                {
                    "calculation_rule": (
                        "Multiple active calculation rules exist "
                        "for this datapoint."
                    )
                }
            )

        return rules[0]


class CalculationResultService:
    """
    Persists the calculation produced by
    ApprovedAnswerCalculationService.

    Responsibilities:
    - create CalculationResult
    - preserve calculation provenance
    - version repeated calculations
    - mark the previous result as SUPERSEDED

    It does not perform the actual emission calculation.
    """

    @staticmethod
    def ensure_access(actor, *, answer=None, result=None):
        if actor is None or getattr(actor, "is_superuser", False):
            return

        if answer is not None:
            org_node_id = answer.submission.data_request.org_node_id
        elif result is not None:
            org_node_id = result.org_node_id
        else:
            return

        if any(
            has_scoped_permission(actor, permission_code, org_node_id)
            for permission_code in ("data.manage", "data.approve")
        ):
            return

        raise PermissionDenied(
            "You do not have permission to access this calculation result in the current org scope."
        )

    @classmethod
    def get_for_user(cls, *, user, result_id):
        result = CalculationResult.objects.select_related(
            "answer__submission__data_request__datapoint",
            "answer__submission__data_request__org_node",
            "answer__submission__data_request__reporting_period",
            "calculation_rule",
            "emission_factor",
            "emission_factor__source",
            "input_unit",
            "output_unit",
            "calculated_by",
            "datapoint",
            "org_node",
            "reporting_period",
            "answer",
            "submission",
            "data_request",
        ).get(pk=result_id)
        cls.ensure_access(user, result=result)
        return result

    @classmethod
    @transaction.atomic
    def persist(
        cls,
        *,
        calculation,
        actor,
    ):
        answer = calculation["answer"]
        rule = calculation["calculation_rule"]
        factor = calculation["factor"]
        cls.ensure_access(actor, answer=answer)

        # ---------------------------------------------------------
        # APPROVED ANSWER BOUNDARY
        # ---------------------------------------------------------

        if answer.submission.status != SubmissionStatus.APPROVED:
            raise ValidationError(
                {
                    "answer": (
                        "Only an approved M5 answer can produce "
                        "a persisted calculation result."
                    )
                }
            )

        # ---------------------------------------------------------
        # SOURCE M5 CONTEXT
        # ---------------------------------------------------------

        submission = answer.submission
        data_request = submission.data_request

        # ---------------------------------------------------------
        # DETERMINE NEXT VERSION
        # ---------------------------------------------------------

        latest_result = (
            CalculationResult.objects
            .filter(answer=answer)
            .order_by("-calculation_version")
            .first()
        )

        if latest_result is None:
            calculation_version = 1
        else:
            calculation_version = (
                latest_result.calculation_version + 1
            )

        # ---------------------------------------------------------
        # SUPERSEDE PREVIOUS CURRENT RESULT
        # ---------------------------------------------------------

        if latest_result is not None:
            CalculationResult.objects.filter(
                answer=answer,
                status=CalculationResultStatus.CURRENT,
            ).update(
                status=CalculationResultStatus.SUPERSEDED,
            )
            latest_result.status = CalculationResultStatus.SUPERSEDED

        # ---------------------------------------------------------
        # CREATE RESULT + PROVENANCE SNAPSHOT
        # ---------------------------------------------------------

        result = CalculationResult.objects.create(
            # -----------------------------------------------------
            # M5 SOURCE
            # -----------------------------------------------------

            answer=answer,
            submission=submission,
            data_request=data_request,

            # -----------------------------------------------------
            # M4 / ORGANIZATION CONTEXT
            # -----------------------------------------------------

            datapoint=answer.datapoint,
            org_node=data_request.org_node,
            reporting_period=data_request.reporting_period,

            # -----------------------------------------------------
            # M6 RULE / FACTOR
            # -----------------------------------------------------

            calculation_rule=rule,
            emission_factor=factor,

            # -----------------------------------------------------
            # INPUT SNAPSHOT
            # -----------------------------------------------------

            input_quantity=calculation["input_quantity"],
            input_unit=calculation["input_unit"],
            normalized_quantity=calculation["normalized_quantity"],

            # -----------------------------------------------------
            # FACTOR / SOURCE SNAPSHOT
            # -----------------------------------------------------

            factor_value=factor.factor_value,
            factor_code=factor.code,
            factor_source_code=factor.source.code,
            factor_source_name=factor.source.name,
            factor_source_version=factor.source.version,
            factor_source_reference=factor.source.source_reference,

            # -----------------------------------------------------
            # CALCULATION CONTEXT
            # -----------------------------------------------------

            activity_key=calculation["activity_key"],
            geography=calculation.get("geography") or "",
            calculation_date=calculation["calculation_date"],

            # -----------------------------------------------------
            # CALCULATED RESULT
            # -----------------------------------------------------

            calculated_value=calculation["calculated_value"],
            output_unit=calculation["output_unit"],

            # -----------------------------------------------------
            # VERSION / STATUS
            # -----------------------------------------------------

            status=CalculationResultStatus.CURRENT,
            calculation_version=calculation_version,

            # -----------------------------------------------------
            # ACTOR
            # -----------------------------------------------------

            calculated_by=actor,
        )

        return result