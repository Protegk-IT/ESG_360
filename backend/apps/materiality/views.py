from django.db import models

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import (
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
)

from .serializers import (
    TopicCategorySerializer,
    MaterialTopicSerializer,
    MaterialSubTopicSerializer,
)


class TopicCategoryListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List all ESG categories.

    POST:
        Create a new ESG category.
    """

    serializer_class = TopicCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TopicCategory.objects.all().order_by(
            "display_order",
            "name",
        )


class MaterialTopicListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List global topics and topics belonging
        to the authenticated user's company.

    POST:
        Create a material topic.
    """

    serializer_class = MaterialTopicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = MaterialTopic.objects.select_related(
            "category",
            "company",
        )

        company = getattr(user, "company", None)

        if company:
            queryset = queryset.filter(
                models.Q(company__isnull=True)
                | models.Q(company=company)
            )
        else:
            queryset = queryset.filter(
                company__isnull=True
            )

        category_id = self.request.query_params.get(
            "category"
        )

        if category_id:
            queryset = queryset.filter(
                category_id=category_id
            )

        search = self.request.query_params.get(
            "search"
        )

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )

        is_active = self.request.query_params.get(
            "is_active"
        )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset.order_by(
            "category__display_order",
            "display_order",
            "code",
        )


class MaterialSubTopicListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List subtopics visible to the authenticated
        user's company.

    POST:
        Create a subtopic.
    """

    serializer_class = MaterialSubTopicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = MaterialSubTopic.objects.select_related(
            "topic",
            "topic__category",
            "topic__company",
        )

        company = getattr(user, "company", None)

        if company:
            queryset = queryset.filter(
                models.Q(topic__company__isnull=True)
                | models.Q(topic__company=company)
            )
        else:
            queryset = queryset.filter(
                topic__company__isnull=True
            )

        topic_id = self.request.query_params.get(
            "topic"
        )

        if topic_id:
            queryset = queryset.filter(
                topic_id=topic_id
            )

        category_id = self.request.query_params.get(
            "category"
        )

        if category_id:
            queryset = queryset.filter(
                topic__category_id=category_id
            )

        search = self.request.query_params.get(
            "search"
        )

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )

        is_active = self.request.query_params.get(
            "is_active"
        )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset.order_by(
            "topic__category__display_order",
            "topic__display_order",
            "display_order",
            "name",
        )