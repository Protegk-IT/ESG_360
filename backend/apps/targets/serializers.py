from rest_framework import serializers

from apps.accounts.models import User
from apps.companies.models import Company
from apps.datapoints.models import Datapoint, Unit, UnitFamily
from apps.materiality.models import AssessmentTopic, MaterialSubTopic, MaterialTopic
from apps.organizations.models import OrgNode
from apps.periods.models import ReportingPeriod
from .models import Goal, KPI, KPIInitiative, Target


class GoalSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    can_manage = serializers.BooleanField(read_only=True, default=False)
    material_topic_name = serializers.CharField(source="material_topic.name", read_only=True)
    material_subtopic_name = serializers.CharField(source="material_subtopic.name", read_only=True)
    owner_name = serializers.SerializerMethodField()
    source_assessment_topic_name = serializers.CharField(source="source_assessment_topic.subtopic.name", read_only=True)
    source_assessment_id = serializers.UUIDField(source="source_assessment_topic.assessment_id", read_only=True)
    source_assessment_topic_topic = serializers.UUIDField(source="source_assessment_topic.subtopic.topic_id", read_only=True)
    source_assessment_topic_subtopic = serializers.UUIDField(source="source_assessment_topic.subtopic_id", read_only=True)
    kpi_count = serializers.IntegerField(read_only=True, default=0)
    class Meta:
        model = Goal
        fields = ("id", "company", "company_name", "name", "description", "material_topic", "material_topic_name", "material_subtopic", "material_subtopic_name", "source_assessment_topic", "source_assessment_topic_name", "source_assessment_id", "source_assessment_topic_topic", "source_assessment_topic_subtopic", "owner", "owner_name", "status", "created_by", "kpi_count", "can_manage", "created_at", "updated_at")
        read_only_fields = ("created_by",)

    def get_owner_name(self, obj):
        return str(obj.owner) if obj.owner_id else None


class KPISerializer(serializers.ModelSerializer):
    can_manage = serializers.BooleanField(read_only=True, default=False)
    datapoint_code = serializers.CharField(source="datapoint.code", read_only=True)
    datapoint_label = serializers.CharField(source="datapoint.label", read_only=True)
    unit_family_name = serializers.CharField(source="unit_family.name", read_only=True)
    default_unit_code = serializers.CharField(source="default_unit.code", read_only=True)
    default_unit_name = serializers.CharField(source="default_unit.name", read_only=True)
    class Meta:
        model = KPI
        fields = ("id", "goal", "code", "name", "description", "metric_source_type", "datapoint", "datapoint_code", "datapoint_label", "metric_code", "unit_family", "unit_family_name", "default_unit", "default_unit_code", "default_unit_name", "direction", "aggregation", "display_order", "is_active", "can_manage", "created_at", "updated_at")


class TargetSerializer(serializers.ModelSerializer):
    can_manage = serializers.BooleanField(read_only=True, default=False)
    org_node_name = serializers.CharField(source="org_node.name", read_only=True)
    baseline_period_name = serializers.CharField(source="baseline_period.name", read_only=True)
    baseline_unit_code = serializers.CharField(source="baseline_unit.code", read_only=True)
    target_period_name = serializers.CharField(source="target_period.name", read_only=True)
    target_unit_code = serializers.CharField(source="target_unit.code", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    class Meta:
        model = Target
        fields = ("id", "kpi", "org_node", "org_node_name", "baseline_period", "baseline_period_name", "baseline_value", "baseline_unit", "baseline_unit_code", "baseline_source", "target_period", "target_period_name", "target_value", "target_unit", "target_unit_code", "target_type", "change_percentage", "owner", "owner_name", "status", "basis", "source_reference", "methodology", "rationale", "created_by", "can_manage", "created_at", "updated_at")
        read_only_fields = ("created_by",)


class InitiativeSerializer(serializers.ModelSerializer):
    can_manage = serializers.BooleanField(read_only=True, default=False)
    kpi_name = serializers.CharField(source="kpi.name", read_only=True)
    org_node_name = serializers.CharField(source="org_node.name", read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = KPIInitiative
        fields = ("id", "kpi", "kpi_name", "name", "description", "org_node", "org_node_name", "owner", "owner_name", "status", "due_date", "anticipated_impact", "can_manage", "created_at", "updated_at")

    def get_owner_name(self, obj):
        return str(obj.owner) if obj.owner_id else None


class GoalWriteSerializer(GoalSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.filter(is_active=True), required=False)
    material_topic = serializers.PrimaryKeyRelatedField(queryset=MaterialTopic.objects.filter(is_active=True), required=False, allow_null=True)
    material_subtopic = serializers.PrimaryKeyRelatedField(queryset=MaterialSubTopic.objects.filter(is_active=True), required=False, allow_null=True)
    source_assessment_topic = serializers.PrimaryKeyRelatedField(queryset=AssessmentTopic.objects.all(), required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), required=False, allow_null=True)

    def validate(self, attrs):
        """Keep optional Materiality provenance internally coherent.

        An assessment topic is provenance, not an alternate source of truth.
        When it is chosen without explicit Topic/Subtopic values, derive those
        optional links from the canonical AssessmentTopic.  Explicit values
        must agree; this prevents a goal silently retaining unrelated context
        after a user changes its Material Topic.
        """
        # A corrective migration leaves legacy Goals nullable. Allow their
        # first explicit tenant assignment, but never move an established Goal
        # (and its KPI/Target history) between Companies.
        if self.instance and self.instance.company_id and "company" in attrs and attrs["company"].pk != self.instance.company_id:
            raise serializers.ValidationError({"company": "Goal company is immutable once the Goal is created."})
        source = attrs.get("source_assessment_topic", getattr(self.instance, "source_assessment_topic", None))
        topic_provided = "material_topic" in attrs
        subtopic_provided = "material_subtopic" in attrs
        topic = attrs.get("material_topic", getattr(self.instance, "material_topic", None))
        subtopic = attrs.get("material_subtopic", getattr(self.instance, "material_subtopic", None))

        if source:
            source_topic = source.subtopic.topic
            source_subtopic = source.subtopic
            if topic is None and not topic_provided:
                attrs["material_topic"] = source_topic
                topic = source_topic
            if subtopic is None and not subtopic_provided:
                attrs["material_subtopic"] = source_subtopic
                subtopic = source_subtopic
            if topic and topic.pk != source_topic.pk:
                raise serializers.ValidationError({"source_assessment_topic": "Assessment-topic provenance must match the selected material topic."})
            if subtopic and subtopic.pk != source_subtopic.pk:
                raise serializers.ValidationError({"source_assessment_topic": "Assessment-topic provenance must match the selected material subtopic."})
        if subtopic and topic and subtopic.topic_id != topic.pk:
            raise serializers.ValidationError({"material_subtopic": "The material subtopic must belong to the selected material topic."})
        return attrs


class KPIWriteSerializer(KPISerializer):
    datapoint = serializers.PrimaryKeyRelatedField(queryset=Datapoint.objects.filter(is_active=True), required=False, allow_null=True)
    unit_family = serializers.PrimaryKeyRelatedField(queryset=UnitFamily.objects.all(), required=False, allow_null=True)
    default_unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.filter(is_active=True), required=False, allow_null=True)


class TargetWriteSerializer(TargetSerializer):
    org_node = serializers.PrimaryKeyRelatedField(queryset=OrgNode.objects.filter(is_active=True), required=False, allow_null=True)
    baseline_period = serializers.PrimaryKeyRelatedField(queryset=ReportingPeriod.objects.all())
    target_period = serializers.PrimaryKeyRelatedField(queryset=ReportingPeriod.objects.all())
    baseline_unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.filter(is_active=True), required=False, allow_null=True)
    target_unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.filter(is_active=True), required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), required=False, allow_null=True)
    baseline_value = serializers.DecimalField(max_digits=24, decimal_places=8, required=False)
    baseline_unit = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.filter(is_active=True), required=False, allow_null=True)

    def validate(self, attrs):
        from .services.progress import KPIValueProvider, convert_value
        target = self.instance
        kpi = attrs.get("kpi", target.kpi if target else None)
        period = attrs.get("baseline_period", target.baseline_period if target else None)
        org_node = attrs.get("org_node", target.org_node if target else None)
        baseline_source = attrs.get("baseline_source", target.baseline_source if target else None)
        if baseline_source == "SYSTEM_DATA":
            actual = KPIValueProvider.actual_for(kpi, period, org_node)
            if actual.status != "AVAILABLE" or actual.value is None:
                raise serializers.ValidationError({"baseline_source": "No approved system value exists for this KPI, company, scope, and baseline period."})
            unit = attrs.get("baseline_unit", target.baseline_unit if target else None) or kpi.default_unit
            value = convert_value(actual.value, actual.unit_id, unit.id if unit else None)
            if value is None:
                raise serializers.ValidationError({"baseline_unit": "The approved system value cannot be converted to the selected baseline unit."})
            attrs["baseline_value"] = value
            attrs["baseline_unit"] = unit
        elif not target and "baseline_value" not in attrs:
            raise serializers.ValidationError({"baseline_value": "Reference baselines require a value and provenance."})
        return attrs


class InitiativeWriteSerializer(InitiativeSerializer):
    # The parent KPI comes from the nested URL.  Moving an initiative to a
    # different KPI through a generic PATCH would break its Goal context.
    kpi = serializers.PrimaryKeyRelatedField(read_only=True)
    org_node = serializers.PrimaryKeyRelatedField(queryset=OrgNode.objects.filter(is_active=True), required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), required=False, allow_null=True)
