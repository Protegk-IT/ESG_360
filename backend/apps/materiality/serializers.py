from rest_framework import serializers

from .models import (
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
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