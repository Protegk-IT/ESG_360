from django.db import models

from rest_framework import generics
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from apps.accounts.viewsets import RBACModelViewSet
from apps.accounts import viewsets
from apps.companies.models import Company

from .models import (
    AssessmentTopic,
    MaterialityAssessment,
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
)

from .serializers import (
    
    MaterialityAssessmentSerializer,
    TopicCategorySerializer,
    MaterialTopicSerializer,
    MaterialSubTopicSerializer,
    SelectAssessmentTopicsSerializer
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


from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets

from .models import MaterialityAssessment
from .serializers import MaterialityAssessmentSerializer
from django.db import transaction

from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company

from .models import (
    MaterialityAssessment,
    AssessmentTopic,
    MaterialSubTopic,
)

from .serializers import (
    MaterialityAssessmentSerializer,
    AssessmentTopicSerializer,
    SelectAssessmentTopicsSerializer,
)


class MaterialityAssessmentViewSet(viewsets.ModelViewSet):

    queryset = MaterialityAssessment.objects.all()

    serializer_class = MaterialityAssessmentSerializer

    permission_classes = [IsAuthenticated]

    # =========================================================
    # GET USER COMPANY
    # =========================================================

    def get_user_company(self):
        return Company.objects.filter(
            is_active=True
        ).first()

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):

        company = self.get_user_company()

        if not company:
            return MaterialityAssessment.objects.none()

        return (
            MaterialityAssessment.objects
            .filter(company=company)
            .select_related(
                "company",
                "created_by",
                "approved_by",
            )
        )

    # =========================================================
    # CREATE ASSESSMENT
    # =========================================================

    def perform_create(self, serializer):

        company = self.get_user_company()

        if not company:
            raise PermissionDenied(
                "No active company is configured."
            )

        serializer.save(
            company=company,
            created_by=self.request.user,
        )

    # =========================================================
    # GET SELECTED TOPICS FOR ASSESSMENT
    #
    # GET:
    # /api/materiality/assessments/<id>/topics/
    # =========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="topics",
    )
    def topics(self, request, pk=None):

        assessment = self.get_object()

        assessment_topics = (
            AssessmentTopic.objects
            .select_related(
                "assessment",
                "subtopic",
                "subtopic__topic",
                "subtopic__topic__category",
            )
            .filter(
                assessment=assessment,
                is_included=True,
            )
            .order_by(
                "display_order",
            )
        )

        serializer = AssessmentTopicSerializer(
            assessment_topics,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # BULK SELECT SUBTOPICS
    #
    # POST:
    # /api/materiality/assessments/<id>/select-topics/
    #
    # Body:
    # {
    #     "subtopic_ids": [
    #         "uuid1",
    #         "uuid2",
    #         "uuid3"
    #     ]
    # }
    # =========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="select-topics",
    )
    @transaction.atomic
    def select_topics(self, request, pk=None):

        assessment = self.get_object()

        serializer = SelectAssessmentTopicsSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        subtopic_ids = (
            serializer.validated_data[
                "subtopic_ids"
            ]
        )

        # =====================================================
        # GET VALID ACTIVE SUBTOPICS
        # =====================================================

        subtopics = (
            MaterialSubTopic.objects
            .select_related(
                "topic",
                "topic__category",
            )
            .filter(
                id__in=subtopic_ids,
                is_active=True,
            )
        )

        # =====================================================
        # VALIDATE ALL SUBTOPICS
        # =====================================================

        if (
            subtopics.count()
            != len(set(subtopic_ids))
        ):
            raise ValidationError({
                "subtopic_ids": (
                    "One or more subtopics are invalid."
                )
            })

        # =====================================================
        # REMOVE PREVIOUS SELECTIONS
        # =====================================================

        AssessmentTopic.objects.filter(
            assessment=assessment
        ).update(
            is_included=False
        )

        # =====================================================
        # CREATE / UPDATE SELECTED SUBTOPICS
        # =====================================================

        for index, subtopic in enumerate(
            subtopics
        ):

            AssessmentTopic.objects.update_or_create(
                assessment=assessment,
                subtopic=subtopic,
                defaults={
                    "is_included": True,
                    "display_order": index,
                },
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Subtopics selected successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )