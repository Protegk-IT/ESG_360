from decimal import Decimal

from rest_framework import serializers

from .models import (
    Stakeholder,
    StakeholderGroup,
    SurveyResponse,
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
    MaterialityAssessment,
    AssessmentTopic,
    Survey,
    ScaleDefinition,
    ScaleOption,
    SurveyQuestion,
    SurveyInvitation,
    SurveyResponse,
    InternalScore,
    ScoreRun,
    ScoreRunTopic,
)
from .services.assessment_progress import (
    get_assessment_progress,
    get_assessment_current_step,
    get_assessment_current_step_url,
    is_assessment_completed,
)


class TopicCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicCategory
        fields = [
            "id",
            "code",
            "name",
            "display_order",
        ]
        read_only_fields = [
            "id",
        ]


class MaterialTopicSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = MaterialTopic
        fields = [
            "id",
            "category",
            "category_name",
            "company",
            "code",
            "name",
            "description",
            "display_order",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "code",
            "category_name",
        ]

    def validate_name(self, value):
        """
        Prevent duplicate topic names inside the same category.
        """

        category_id = self.initial_data.get("category")

        if not category_id:
            return value.strip()

        queryset = MaterialTopic.objects.filter(
            category_id=category_id,
            name__iexact=value.strip(),
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A topic with this name already exists "
                "in this category."
            )

        return value.strip()


class MaterialSubTopicSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(
        source="topic.name",
        read_only=True,
    )

    topic_code = serializers.IntegerField(
        source="topic.code",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="topic.category.name",
        read_only=True,
    )

    class Meta:
        model = MaterialSubTopic
        fields = [
            "id",
            "topic",
            "topic_name",
            "topic_code",
            "category_name",
            "code",
            "name",
            "description",
            "display_order",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "code",
            "topic_name",
            "topic_code",
            "category_name",
        ]

    def validate_name(self, value):
        """
        Prevent duplicate subtopic names inside the same topic.
        """

        topic_id = self.initial_data.get("topic")

        if not topic_id:
            return value.strip()

        queryset = MaterialSubTopic.objects.filter(
            topic_id=topic_id,
            name__iexact=value.strip(),
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A sub-topic with this name already exists "
                "in this topic."
            )

        return value.strip()

#Reporting Period

from apps.periods.models import ReportingPeriod


class ReportingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingPeriod
        fields = [
            "id",
            "name",
            "period_type",
            "start_date",
            "end_date",
            "status",
            "is_baseline_year",
        ]




# Serilizer for Materilaity Assesmnet  total 3 serilizers
# CURD for Materiality Assesment but only C,R for  assesment topic
# we have one special serilizer for bulk-read and create assesment material topic

from rest_framework import serializers

from .models import AssessmentTopic


class MaterialityAssessmentSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(
        read_only=True
    )
    reporting_period_details = ReportingPeriodSerializer(
        source="reporting_period",
        read_only=True,
    )

    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    approved_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )


    progress_percentage = serializers.SerializerMethodField()

    current_step = serializers.SerializerMethodField()

    is_assessment_completed = serializers.SerializerMethodField()

    current_step_url = serializers.SerializerMethodField()

    class Meta:
        model = MaterialityAssessment
        fields = [
            "id",
            "company",
            "name",
            "reporting_period",
            "reporting_period_details",
            "mode",
            "status",
            "primary_threshold",
            "secondary_threshold",
            "scale_min",
            "scale_max",
            "internal_blend_weight",
            "is_locked",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            "progress_percentage",
            "current_step",
            "is_assessment_completed",
            "current_step_url",
        ]

        read_only_fields = [
            "id",
            "company",
            "status",
            "is_locked",
            "created_by",
            "approved_by",
            "approved_at",
            "created_at",
            
        ]

    def validate_reporting_period(self, reporting_period):

        if not reporting_period.is_active:
            raise serializers.ValidationError(
                "This reporting period is inactive."
            )

        if reporting_period.status != "OPEN":
            raise serializers.ValidationError(
                "Only OPEN reporting periods can be used for a new assessment."
            )

        return reporting_period

    def validate(self, attrs):

        scale_min = attrs.get(
            "scale_min",
            getattr(self.instance, "scale_min", 1),
        )

        scale_max = attrs.get(
            "scale_max",
            getattr(self.instance, "scale_max", 5),
        )

        blend_weight = attrs.get(
            "internal_blend_weight",
            getattr(
                self.instance,
                "internal_blend_weight",
                Decimal("0.50"),
            ),
        )


        if scale_min >= scale_max:
            raise serializers.ValidationError({
                "scale_max": (
                    "Scale maximum must be greater than "
                    "scale minimum."
                )
            })

        if not (
            Decimal("0.00")
            <= blend_weight
            <= Decimal("1.00")
        ):
            raise serializers.ValidationError({
                "internal_blend_weight": (
                    "Internal blend weight must be between "
                    "0.00 and 1.00."
                )
            })

        return attrs

    def get_progress_percentage(self, obj):
        return get_assessment_progress(obj)

    def get_current_step(self, obj):
        return get_assessment_current_step(obj)

    def get_is_assessment_completed(self, obj):
        return is_assessment_completed(obj)

    def get_current_step_url(self, obj):
        return get_assessment_current_step_url(obj)

    

    def update(self, instance, validated_data):
        if instance.is_locked:
            raise serializers.ValidationError(
                "This assessment is locked and cannot be modified."
            )

        # Mode must not change once topics have been selected.
        #
        # AssessmentTopic will be implemented next.
        # Once it exists, this check will determine whether
        # any topics are already selected.
        if "mode" in validated_data:
            if instance.status != "DRAFT":
                raise serializers.ValidationError({
                    "mode": (
                        "Assessment mode cannot be changed "
                        "after topic selection has started."
                    )
                })

        return super().update(instance, validated_data)


class MaterialityReportingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingPeriod
        fields = [
            "id",
            "name",
            "period_type",
            "start_date",
            "end_date",
            "status",
        ]   



from rest_framework import serializers

from apps.materiality.models import AssessmentTopic


class SelectAssessmentTopicsSerializer(serializers.Serializer):
    subtopic_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )

class AssessmentTopicSerializer(serializers.ModelSerializer):
    subtopic_name = serializers.CharField(
        source="subtopic.name",
        read_only=True,
    )

    topic_name = serializers.CharField(
        source="subtopic.topic.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="subtopic.topic.category.name",
        read_only=True,
    )

    class Meta:
        model = AssessmentTopic
        fields = [
            "id",
            "assessment",
            "subtopic",
            "subtopic_name",
            "topic_name",
            "category_name",
            "is_included",
            "display_order",
            "primary_score",
            "secondary_score",
            "classification",
            "is_override",
            "override_reason",
            "override_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "override_by",
            "created_at",
            "updated_at",
        ]


class StakeholderGroupSerializer(serializers.ModelSerializer):

    assessment = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = StakeholderGroup

        fields = [
            "id",
            "assessment",
            "name",
            "description",
            "weight",
            "is_internal",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "assessment",
            "created_at",
        ]

    def validate_weight(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Weight cannot be negative."
            )

        if value > 100:
            raise serializers.ValidationError(
                "Weight cannot be greater than 100."
            )

        return value
    

class StakeholderSerializer(serializers.ModelSerializer):

    group = serializers.PrimaryKeyRelatedField(
        queryset=StakeholderGroup.objects.all()
    )

    group_name = serializers.CharField(
        source="group.name",
        read_only=True,
    )

    class Meta:
        model = Stakeholder

        fields = [
            "id",
            "group",
            "group_name",
            "name",
            "email",
            "organisation",
            "designation",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "group_name",
            "created_at",
        ]

    def validate_group(self, group):
        assessment = self.context.get("assessment")

        if assessment and group.assessment_id != assessment.id:
            raise serializers.ValidationError(
                "Stakeholder group does not belong to this assessment."
            )

        return group    




class SurveySerializer(serializers.ModelSerializer):

    assessment = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = Survey

        fields = [
            "id",
            "assessment",
            "title",
            "intro_text",
            "closing_text",
            "opens_at",
            "closes_at",
            "status",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "assessment",
            "status",
            "created_at",
        ]

    def validate(self, attrs):
        opens_at = attrs.get("opens_at")
        closes_at = attrs.get("closes_at")

        if opens_at and closes_at:
            if opens_at >= closes_at:
                raise serializers.ValidationError({
                    "closes_at": (
                        "Closing time must be greater than "
                        "opening time."
                    )
                })

        return attrs



class ScaleDefinitionSerializer(serializers.ModelSerializer):

    assessment = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = ScaleDefinition

        fields = [
            "id",
            "assessment",
            "dimension",
            "name",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "assessment",
            "created_at",
        ]



class ScaleOptionSerializer(serializers.ModelSerializer):

    scale = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = ScaleOption

        fields = [
            "id",
            "scale",
            "value",
            "label",
            "description",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "scale",
            "created_at",
        ]

    def validate_value(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Scale value cannot be negative."
            )

        return value
    

    
class SurveyQuestionSerializer(serializers.ModelSerializer):
    survey = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    assessment_topic_name = serializers.CharField(
        source="assessment_topic.subtopic.name",
        read_only=True,
    )

    scale_name = serializers.CharField(
        source="scale.name",
        read_only=True,
    )

    class Meta:
        model = SurveyQuestion

        fields = [
            "id",
            "survey",
            "assessment_topic",
            "assessment_topic_name",
            "scale",
            "scale_name",
            "dimension",
            "question_text",
            "help_text",
            "display_order",
            "is_required",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "survey",
            "assessment_topic_name",
            "scale_name",
            "created_at",
        ]

    def validate(self, attrs):
        survey = self.context.get("survey")

        assessment_topic = attrs.get("assessment_topic")
        scale = attrs.get("scale")

        # ---------------------------------------------
        # AssessmentTopic must belong to this survey's
        # assessment.
        # ---------------------------------------------
        if survey and assessment_topic:
            if (
                assessment_topic.assessment_id
                != survey.assessment_id
            ):
                raise serializers.ValidationError({
                    "assessment_topic": (
                        "Assessment topic does not belong "
                        "to this survey's assessment."
                    )
                })

        # ---------------------------------------------
        # Scale must either be:
        #
        # 1. A global scale
        # OR
        # 2. A scale belonging to this assessment.
        # ---------------------------------------------
        if survey and scale:
            if (
                scale.assessment_id is not None
                and scale.assessment_id
                != survey.assessment_id
            ):
                raise serializers.ValidationError({
                    "scale": (
                        "Scale does not belong to this "
                        "assessment."
                    )
                })

            # Make sure dimension matches scale dimension.
            if scale.dimension != attrs.get("dimension"):
                raise serializers.ValidationError({
                    "dimension": (
                        "Question dimension must match "
                        "the selected scale dimension."
                    )
                })

        return attrs  


class SurveyInvitationSerializer(serializers.ModelSerializer):
    stakeholder_name = serializers.CharField(
        source="stakeholder.name",
        read_only=True,
    )

    stakeholder_email = serializers.EmailField(
        source="stakeholder.email",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = SurveyInvitation

        fields = [
            "id",
            "survey",
            "stakeholder",
            "stakeholder_name",
            "stakeholder_email",
            "token",
            "sent_at",
            "first_opened_at",
            "submitted_at",
            "status",
            "status_display",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "token",
            "sent_at",
            "first_opened_at",
            "submitted_at",
            "status",
            "created_at",
        ]


class SurveyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyResponse

        fields = [
            "id",
            "invitation",
            "question",
            "value",
            "comment",
            "answered_at",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "answered_at",
            "created_at",
        ]

    def validate(self, attrs):
        invitation = attrs.get("invitation")
        question = attrs.get("question")

        if invitation and question:
            if question.survey_id != invitation.survey_id:
                raise serializers.ValidationError({
                    "question": (
                        "This question does not belong to "
                        "the invitation's survey."
                    )
                })

        return attrs    
    


class InternalScoreSerializer(serializers.ModelSerializer):
    """
    Internal expert scoring (§6.2), double mode only.
    Written the same way StakeholderSerializer.validate_group works —
    ownership of the parent object is checked against a context value
    the view supplies, not re-derived here.
    """
 
    assessment_topic_name = serializers.CharField(
        source="assessment_topic.subtopic.name",
        read_only=True,
    )
 
    class Meta:
        model = InternalScore
        fields = [
            "id",
            "assessment_topic",
            "assessment_topic_name",
            "impact_type",
            "scale",
            "scope",
            "irremediability",
            "likelihood",
            "financial_magnitude",
            "financial_likelihood",
            "rationale",
            "scored_by",
            "scored_at",
        ]
        read_only_fields = [
            "id",
            "assessment_topic_name",
            "scored_by",
            "scored_at",
        ]
 
    def validate_assessment_topic(self, assessment_topic):
        assessment = self.context.get("assessment")
 
        if assessment and assessment_topic.assessment_id != assessment.id:
            raise serializers.ValidationError(
                "This sub-topic does not belong to this assessment."
            )
 
        return assessment_topic
 
    def validate(self, attrs):
        impact_type = attrs.get(
            "impact_type",
            getattr(self.instance, "impact_type", None),
        )
 
        likelihood = attrs.get(
            "likelihood",
            getattr(self.instance, "likelihood", None),
        )
 
        if impact_type == "POTENTIAL" and likelihood is None:
            raise serializers.ValidationError({
                "likelihood": (
                    "Likelihood is required when impact_type is POTENTIAL."
                )
            })
 
        return attrs
 
 
class ScoreRunTopicSerializer(serializers.ModelSerializer):
    subtopic_code = serializers.CharField(
        source="assessment_topic.subtopic.code",
        read_only=True,
    )
 
    subtopic_name = serializers.CharField(
        source="assessment_topic.subtopic.name",
        read_only=True,
    )
 
    category_code = serializers.CharField(
        source="assessment_topic.subtopic.topic.category.code",
        read_only=True,
    )
 
    class Meta:
        model = ScoreRunTopic
        fields = [
            "id",
            "assessment_topic",
            "subtopic_code",
            "subtopic_name",
            "category_code",
            "primary_score",
            "secondary_score",
            "classification",
            "is_override",
            "override_reason",
            "group_breakdown"
        ]
        read_only_fields = fields
 
 
class ScoreRunSerializer(serializers.ModelSerializer):
    topic_results = ScoreRunTopicSerializer(
        many=True,
        read_only=True,
    )
 
    class Meta:
        model = ScoreRun
        fields = [
            "id",
            "assessment",
            "mode",
            "thresholds_snapshot",
            "group_weights_snapshot",
            "response_count",
            "invited_count",
            "method_version",
            "run_by",
            "run_at",
            "topic_results",
        ]
        read_only_fields = fields
 
 
class ScoreRunListSerializer(serializers.ModelSerializer):
    """Lighter version for the score-run history list — no nested topics."""
 
    class Meta:
        model = ScoreRun
        fields = [
            "id",
            "mode",
            "response_count",
            "invited_count",
            "method_version",
            "run_by",
            "run_at",
        ]
        read_only_fields = fields
 
 
SINGLE_CLASSIFICATIONS = {
    "MATERIAL",
    "MONITOR",
    "NOT_MATERIAL",
}
 
DOUBLE_CLASSIFICATIONS = {
    "DOUBLE_MATERIAL",
    "IMPACT_MATERIAL",
    "FINANCIAL_MATERIAL",
    "NOT_MATERIAL",
}
 
 
class AssessmentTopicOverrideSerializer(serializers.ModelSerializer):
    """Manual classification override (§6.5)."""
 
    class Meta:
        model = AssessmentTopic
        fields = [
            "classification",
            "override_reason",
        ]
 
    def validate_override_reason(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "override_reason must be at least 20 characters — an "
                "auditor will ask why this topic was reclassified."
            )
 
        return value
 
    def validate_classification(self, value):
        mode = self.instance.assessment.mode
 
        allowed = (
            SINGLE_CLASSIFICATIONS
            if mode == "SINGLE"
            else DOUBLE_CLASSIFICATIONS
        )
 
        if value not in allowed:
            raise serializers.ValidationError(
                f"'{value}' is not valid for {mode} mode. "
                f"Expected one of: {sorted(allowed)}."
            )
 
        return value
 
    def save(self, **kwargs):
        self.instance.is_override = True
 
        self.instance.override_by = (
            self.context["request"].user
        )
 
        return super().save(**kwargs)
