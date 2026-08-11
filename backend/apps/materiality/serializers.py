from decimal import Decimal

from rest_framework import serializers

from .models import (
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
    MaterialityAssessment,
    AssessmentTopic,
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



# Serilizer for Materilaity Assesmnet  total 3 serilizers
# CURD for Materiality Assesment but only C,R for  assesment topic
# we have one special serilizer for bulk-read and create assesment material topic

from rest_framework import serializers

from .models import AssessmentTopic


class MaterialityAssessmentSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    approved_by = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = MaterialityAssessment
        fields = [
            "id",
            "company",
            "name",
            "financial_year",
            "period_start",
            "period_end",
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

    def validate(self, attrs):
        period_start = attrs.get(
            "period_start",
            getattr(self.instance, "period_start", None),
        )

        period_end = attrs.get(
            "period_end",
            getattr(self.instance, "period_end", None),
        )

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

        if period_start and period_end:
            if period_start > period_end:
                raise serializers.ValidationError({
                    "period_end": (
                        "Period end date must be greater than "
                        "or equal to period start date."
                    )
                })

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



class AssessmentTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentTopic
        fields = [
            "id",
            "assessment",
            "subtopic",
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