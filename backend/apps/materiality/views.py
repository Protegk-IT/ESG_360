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
    Stakeholder,
    StakeholderGroup,
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
    Survey,
    ScaleDefinition,
    ScaleOption,
    SurveyQuestion,
)

from .serializers import (
    
    MaterialityAssessmentSerializer,
    StakeholderGroupSerializer,
    StakeholderSerializer,
    TopicCategorySerializer,
    MaterialTopicSerializer,
    MaterialSubTopicSerializer,
    SelectAssessmentTopicsSerializer,
    SurveySerializer,
    ScaleDefinitionSerializer,
    ScaleOptionSerializer,
    SurveyQuestionSerializer,
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

    def get_serializer_class(self):
        if self.action == "groups":
            return StakeholderGroupSerializer

        if self.action == "stakeholders":
            return StakeholderSerializer

        if self.action == "topics":
            return AssessmentTopicSerializer

        if self.action == "select_topics":
            return SelectAssessmentTopicsSerializer

        return MaterialityAssessmentSerializer

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
    

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="groups",
    )
    def groups(self, request, pk=None):
        assessment = self.get_object()

        if request.method == "GET":
            groups = StakeholderGroup.objects.filter(
                assessment=assessment
            )

            serializer = StakeholderGroupSerializer(
                groups,
                many=True,
            )

            return Response(serializer.data)

        serializer = StakeholderGroupSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(
            assessment=assessment
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
    detail=True,
    methods=["get", "post"],
    url_path="stakeholders",
)
    def stakeholders(self, request, pk=None):

        assessment = self.get_object()

        if request.method == "GET":

            stakeholders = Stakeholder.objects.filter(
                group__assessment=assessment
            ).select_related("group")

            serializer = StakeholderSerializer(
                stakeholders,
                many=True,
            )

            return Response(serializer.data)

        serializer = StakeholderSerializer(
            data=request.data,
            context={
                "assessment": assessment,
            },
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
    )

    @action(
        detail=True,
        methods=["post"],
        url_path="stakeholders/import",
    )
    def import_stakeholders(self, request, pk=None):

        # -----------------------------------------
        # 1. Get assessment
        # -----------------------------------------

        assessment = self.get_object()

        # -----------------------------------------
        # 2. Get uploaded file
        # -----------------------------------------

        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            raise ValidationError({
                "file": "Please upload a CSV file."
            })

        if not uploaded_file.name.lower().endswith(".csv"):
            raise ValidationError({
                "file": "Only CSV files are supported."
            })

        # -----------------------------------------
        # 3. Read CSV
        # -----------------------------------------

        try:
            decoded_file = uploaded_file.read().decode(
                "utf-8-sig"
            )
        except UnicodeDecodeError:
            raise ValidationError({
                "file": "CSV file must be UTF-8 encoded."
            })

        reader = csv.DictReader(
            io.StringIO(decoded_file)
        )

        if not reader.fieldnames:
            raise ValidationError({
                "file": "CSV file must contain headers."
            })

        # -----------------------------------------
        # 4. Validate required columns
        # -----------------------------------------

        required_columns = {
            "group",
            "name",
            "email",
        }

        csv_columns = {
            column.strip().lower()
            for column in reader.fieldnames
            if column
        }

        missing_columns = required_columns - csv_columns

        if missing_columns:
            raise ValidationError({
                "file": (
                    "Missing required columns: "
                    + ", ".join(sorted(missing_columns))
                )
            })

        rows = list(reader)

        if not rows:
            raise ValidationError({
                "file": "CSV file does not contain any data."
            })

        # -----------------------------------------
        # 5. Create stakeholders
        # -----------------------------------------

        created_stakeholders = []

        with transaction.atomic():

            for row_number, row in enumerate(
                rows,
                start=2,
            ):

                # Normalize column names
                row = {
                    key.strip().lower(): value
                    for key, value in row.items()
                    if key
                }

                group_id = row.get("group")
                name = row.get("name")
                email = row.get("email")

                organisation = (
                    row.get("organisation") or ""
                )

                designation = (
                    row.get("designation") or ""
                )

                # ---------------------------------
                # Basic row validation
                # ---------------------------------

                if not group_id:
                    raise ValidationError({
                        "row": row_number,
                        "group": "Group is required."
                    })

                if not name:
                    raise ValidationError({
                        "row": row_number,
                        "name": "Name is required."
                    })

                if not email:
                    raise ValidationError({
                        "row": row_number,
                        "email": "Email is required."
                    })

                email = str(email).strip()

                # ---------------------------------
                # Duplicate check
                # ---------------------------------

                if Stakeholder.objects.filter(
                    group_id=group_id,
                    email__iexact=email,
                ).exists():

                    raise ValidationError({
                        "row": row_number,
                        "email": (
                            "A stakeholder with this email "
                            "already exists in this group."
                        )
                    })

                # ---------------------------------
                # Serializer validation
                # ---------------------------------

                serializer = StakeholderSerializer(
                    data={
                        "group": group_id,
                        "name": str(name).strip(),
                        "email": email,
                        "organisation": str(
                            organisation
                        ).strip(),
                        "designation": str(
                            designation
                        ).strip(),
                    },
                    context={
                        "assessment": assessment,
                    },
                )

                if not serializer.is_valid():

                    raise ValidationError({
                        "row": row_number,
                        "errors": serializer.errors,
                    })

                stakeholder = serializer.save()

                created_stakeholders.append(
                    stakeholder
                )

        # -----------------------------------------
        # 6. Response
        # -----------------------------------------

        return Response(
            {
                "message": (
                    f"{len(created_stakeholders)} "
                    "stakeholders imported successfully."
                ),
                "count": len(created_stakeholders),
            },
            status=status.HTTP_201_CREATED,
        )


    @action(detail=True,methods=["get", "patch"],url_path="survey",)
    def survey(self, request, pk=None):

        assessment = self.get_object()

        survey = Survey.objects.filter(
            assessment=assessment
        ).first()

        if not survey:
            raise ValidationError(
                "Survey has not been generated for this assessment."
            )

        if request.method == "GET":
            serializer = SurveySerializer(survey)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # PATCH
        serializer = SurveySerializer(
            survey,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True,methods=["get", "post"],url_path="scales",)
    def scales(self, request, pk=None):
        assessment = self.get_object()
        if request.method == "GET":
            scales = ScaleDefinition.objects.filter(
                models.Q(assessment=assessment)
                | models.Q(assessment__isnull=True)
            ).prefetch_related("options")

            serializer = ScaleDefinitionSerializer(
                scales,
                many=True,
            )

            return Response(serializer.data)

        serializer = ScaleDefinitionSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        scale = serializer.save(
            assessment=assessment
        )
        return Response(
            ScaleDefinitionSerializer(scale).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True,methods=["get", "post"],url_path=r"scales/(?P<scale_id>[^/.]+)/options",)
    def scale_options(
        self,
        request,
        pk=None,
        scale_id=None,
    ):

        assessment = self.get_object()

        scale = ScaleDefinition.objects.filter(
            pk=scale_id
        ).filter(
            models.Q(assessment=assessment)
            | models.Q(assessment__isnull=True)
        ).first()

        if not scale:
            raise ValidationError(
                "Scale does not belong to this assessment."
            )

        if request.method == "GET":

            options = ScaleOption.objects.filter(
                scale=scale
            )

            serializer = ScaleOptionSerializer(
                options,
                many=True,
            )

            return Response(serializer.data)

        serializer = ScaleOptionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        option = serializer.save(
            scale=scale
        )

        return Response(
            ScaleOptionSerializer(option).data,
            status=status.HTTP_201_CREATED,
        )


    @action(detail=True, methods=["get", "post"], url_path="survey/questions",)
    def survey_questions(self,request,pk=None,):

        assessment = self.get_object()

        survey = Survey.objects.filter(
            assessment=assessment
        ).first()

        if not survey:
            raise ValidationError(
                "Survey has not been created for this assessment."
            )

        if request.method == "GET":

            questions = (
                SurveyQuestion.objects
                .filter(survey=survey)
                .select_related(
                    "assessment_topic",
                    "scale",
                )
                .order_by("display_order")
            )

            serializer = SurveyQuestionSerializer(
                questions,
                many=True,
            )

            return Response(serializer.data)

        serializer = SurveyQuestionSerializer(
            data=request.data,
            context={
                "survey": survey,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        question = serializer.save(
            survey=survey
        )

        return Response(
            SurveyQuestionSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="survey/generate",
    )
    @transaction.atomic
    def generate_survey(self, request, pk=None):
        """
        Generate the survey for an assessment.

        The survey is generated from:
        1. The sub-topics selected in AssessmentTopic.
        2. The assessment mode.
        3. The predefined question templates from the project document.
        4. The already configured/seeded scale definitions.

        SINGLE mode:
            - IMPACT
            - STAKEHOLDER_IMPORTANCE

        DOUBLE mode:
            - IMPACT
            - FINANCIAL

        Questions are created in SurveyQuestion so that they can
        later be edited by the ESG manager.
        """

        # =========================================================
        # 1. GET ASSESSMENT
        # =========================================================

        assessment = self.get_object()

        # =========================================================
        # 2. CHECK WHETHER SURVEY ALREADY EXISTS
        # =========================================================

        if Survey.objects.filter(
            assessment=assessment
        ).exists():

            raise ValidationError(
                "A survey has already been generated "
                "for this assessment."
            )

        # =========================================================
        # 3. GET INCLUDED SUB-TOPICS
        # =========================================================

        assessment_topics = (
            AssessmentTopic.objects
            .filter(
                assessment=assessment,
                is_included=True,
            )
            .select_related(
                "subtopic",
                "subtopic__topic",
                "subtopic__topic__category",
            )
            .order_by(
                "display_order",
            )
        )

        if not assessment_topics.exists():

            raise ValidationError(
                "Cannot generate survey because no "
                "sub-topics have been selected."
            )

        # =========================================================
        # 4. DETERMINE QUESTIONS FROM ASSESSMENT MODE
        # =========================================================

        if assessment.mode == "SINGLE":

            dimensions = [
                "IMPACT",
                "STAKEHOLDER_IMPORTANCE",
            ]

        elif assessment.mode == "DOUBLE":

            dimensions = [
                "IMPACT",
                "FINANCIAL",
            ]

        else:

            raise ValidationError(
                "Invalid assessment mode."
            )

        # =========================================================
        # 5. GET SCALES
        # =========================================================
        #
        # Scales/options must already exist.
        #
        # The generation endpoint does NOT create scale options.
        #
        # First look for an assessment-specific scale.
        # If none exists, use the seeded global scale.
        # =========================================================

        scales = {}

        for dimension in dimensions:

            scale = (
                ScaleDefinition.objects
                .filter(
                    assessment=assessment,
                    dimension=dimension,
                )
                .first()
            )

            if not scale:

                scale = (
                    ScaleDefinition.objects
                    .filter(
                        assessment__isnull=True,
                        dimension=dimension,
                    )
                    .first()
                )

            if not scale:

                raise ValidationError(
                    f"No scale has been configured "
                    f"for {dimension}."
                )

            scales[dimension] = scale

        # =========================================================
        # 6. CREATE SURVEY
        # =========================================================

        survey = Survey.objects.create(
            assessment=assessment,
            title=f"{assessment.name} Survey",
            status="DRAFT",
        )

        # =========================================================
        # 7. GENERATE QUESTIONS
        # =========================================================

        company_name = assessment.company.name

        questions = []

        display_order = 1

        for assessment_topic in assessment_topics:

            subtopic_name = (
                assessment_topic.subtopic.name
            )

            for dimension in dimensions:

                # -------------------------------------------------
                # IMPACT
                # -------------------------------------------------

                if dimension == "IMPACT":

                    question_text = (
                        f"How significantly does "
                        f"{company_name} affect "
                        f"{subtopic_name} through its operations?"
                    )

                # -------------------------------------------------
                # STAKEHOLDER IMPORTANCE
                # -------------------------------------------------

                elif dimension == "STAKEHOLDER_IMPORTANCE":

                    question_text = (
                        f"How important is "
                        f"{subtopic_name} to you in your "
                        f"relationship with {company_name}?"
                    )

                # -------------------------------------------------
                # FINANCIAL
                # -------------------------------------------------

                elif dimension == "FINANCIAL":

                    question_text = (
                        f"How much could "
                        f"{subtopic_name} affect "
                        f"{company_name}'s costs, revenue "
                        f"or ability to operate?"
                    )

                questions.append(
                    SurveyQuestion(
                        survey=survey,
                        assessment_topic=assessment_topic,
                        scale=scales[dimension],
                        dimension=dimension,
                        question_text=question_text,
                        display_order=display_order,
                        is_required=True,
                    )
                )

                display_order += 1

        # =========================================================
        # 8. SAVE ALL GENERATED QUESTIONS
        # =========================================================

        SurveyQuestion.objects.bulk_create(
            questions
        )

        # =========================================================
        # 9. SURVEY LENGTH WARNING
        # =========================================================

        subtopic_count = assessment_topics.count()
        question_count = len(questions)

        warning = None

        if subtopic_count > 20:

            estimated_minutes = (
                question_count * 15 + 59
            ) // 60

            warning = (
                f"{subtopic_count} sub-topics will produce "
                f"{question_count} questions and an estimated "
                f"{estimated_minutes} minute survey. "
                f"Consider reducing the shortlist."
            )

        # =========================================================
        # 10. RESPONSE
        # =========================================================

        response_data = {
            "message": "Survey generated successfully.",
            "survey_id": survey.id,
            "mode": assessment.mode,
            "subtopic_count": subtopic_count,
            "question_count": question_count,
        }

        if warning:
            response_data["warning"] = warning

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )