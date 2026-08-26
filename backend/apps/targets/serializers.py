from rest_framework import serializers

from apps.accounts.models import User
from apps.datapoints.models import Datapoint, Unit, UnitFamily
from apps.materiality.models import AssessmentTopic, MaterialSubTopic, MaterialTopic
from apps.organizations.models import OrgNode
from apps.periods.models import ReportingPeriod
from .models import Goal, KPI, KPIInitiative, Target


class GoalSerializer(serializers.ModelSerializer):
    material_topic_name = serializers.CharField(source="material_topic.name", read_only=True)
    material_subtopic_name = serializers.CharField(source="material_subtopic.name", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    kpi_count = serializers.IntegerField(read_only=True, default=0)
    class Meta:
        model = Goal
        fields = ("id", "name", "description", "material_topic", "material_topic_name", "material_subtopic", "material_subtopic_name", "source_assessment_topic", "owner", "owner_name", "status", "created_by", "kpi_count", "created_at", "updated_at")
        read_only_fields = ("created_by",)


class KPISerializer(serializers.ModelSerializer):
    datapoint_code = serializers.CharField(source="datapoint.code", read_only=True)
    datapoint_label = serializers.CharField(source="datapoint.label", read_only=True)
    unit_family_name = serializers.CharField(source="unit_family.name", read_only=True)
    default_unit_code = serializers.CharField(source="default_unit.code", read_only=True)
    default_unit_name = serializers.CharField(source="default_unit.name", read_only=True)
    class Meta:
        model = KPI
        fields = ("id", "goal", "code", "name", "description", "metric_source_type", "datapoint", "datapoint_code", "datapoint_label", "metric_code", "unit_family", "unit_family_name", "default_unit", "default_unit_code", "default_unit_name", "direction", "aggregation", "display_order", "is_active", "created_at", "updated_at")


class TargetSerializer(serializers.ModelSerializer):
    org_node_name = serializers.CharField(source="org_node.name", read_only=True)
    baseline_period_name = serializers.CharField(source="baseline_period.name", read_only=True)
    baseline_unit_code = serializers.CharField(source="baseline_unit.code", read_only=True)
    target_period_name = serializers.CharField(source="target_period.name", read_only=True)
    target_unit_code = serializers.CharField(source="target_unit.code", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    class Meta:
        model = Target
        fields = ("id", "kpi", "org_node", "org_node_name", "baseline_period", "baseline_period_name", "baseline_value", "baseline_unit", "baseline_unit_code", "baseline_source", "target_period", "target_period_name", "target_value", "target_unit", "target_unit_code", "target_type", "change_percentage", "owner", "owner_name", "status", "basis", "source_reference", "methodology", "rationale", "created_by", "created_at", "updated_at")
        read_only_fields = ("created_by",)


class InitiativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPIInitiative
        fields = ("id", "kpi", "name", "description", "org_node", "owner", "status", "due_date", "anticipated_impact", "created_at", "updated_at")


class GoalWriteSerializer(GoalSerializer):
    material_topic = serializers.PrimaryKeyRelatedField(queryset=MaterialTopic.objects.filter(is_active=True), required=False, allow_null=True)
    material_subtopic = serializers.PrimaryKeyRelatedField(queryset=MaterialSubTopic.objects.filter(is_active=True), required=False, allow_null=True)
    source_assessment_topic = serializers.PrimaryKeyRelatedField(queryset=AssessmentTopic.objects.all(), required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), required=False, allow_null=True)


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


class InitiativeWriteSerializer(InitiativeSerializer):
    org_node = serializers.PrimaryKeyRelatedField(queryset=OrgNode.objects.filter(is_active=True), required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), required=False, allow_null=True)
