import uuid

from django.db import models
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError,NotFound

from apps.accounts.viewsets import RBACModelViewSet
from apps.accounts import viewsets
from apps.companies.models import Company
from django.utils import timezone
from django.conf import settings

from .services.survey_email import send_survey_invitation
from .services.scoring import run_scoring

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
    SurveyInvitation,
    SurveyResponse,
    InternalScore, 
    ScoreRun,
    ScoreRunTopic
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
    InternalScoreSerializer,
    ScoreRunSerializer,
    ScoreRunListSerializer,
    AssessmentTopicOverrideSerializer,
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
from apps.periods.models import ReportingPeriod

from .models import (
    MaterialityAssessment,
    AssessmentTopic,
    MaterialSubTopic,
)

from .serializers import (
    MaterialityAssessmentSerializer,
    AssessmentTopicSerializer,
    SelectAssessmentTopicsSerializer,
    MaterialityReportingPeriodSerializer,
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
        
        if self.action == "survey":
            return SurveySerializer
        
        if self.action == "scales":
            return ScaleDefinitionSerializer
        
        if self.action == "scale_options":
            return ScaleOptionSerializer
        
        if self.action == "survey_questions":
            return SurveyQuestionSerializer
        
        if self.action == "generate_survey":
            return SurveySerializer
        if self.action == "internal_scores":
            return InternalScoreSerializer

        if self.action == "run_score":
            return ScoreRunSerializer
 
        if self.action == "results":
            return ScoreRunSerializer
 
        if self.action == "override_topic":
            return AssessmentTopicOverrideSerializer
 
        if self.action == "score_runs":
            return ScoreRunListSerializer

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
                "reporting_period",
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


     #Reporting Period
    @action(
    detail=False,
    methods=["get"],
    url_path="reporting-periods",
    )
    def reporting_periods(self, request):

        periods = (
            ReportingPeriod.objects
            .filter(
                is_active=True,
                status="OPEN",
            )
            .order_by("-start_date")
        )

        serializer = MaterialityReportingPeriodSerializer(
            periods,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
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
    
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="scales",
    )
    @transaction.atomic
    def scales(self, request, pk=None):

        assessment = self.get_object()

        # =========================================================
        # GET
        # =========================================================

        if request.method == "GET":

            scales = (
                ScaleDefinition.objects
                .filter(
                    models.Q(assessment=assessment)
                    | models.Q(assessment__isnull=True)
                )
                .prefetch_related("options")
                .order_by(
                    "dimension",
                    "assessment",
                )
            )

            serializer = ScaleDefinitionSerializer(
                scales,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # =========================================================
        # POST
        # =========================================================

        serializer = ScaleDefinitionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        dimension = serializer.validated_data[
            "dimension"
        ]

        # =========================================================
        # 1. PREVENT DUPLICATE ASSESSMENT-SPECIFIC SCALE
        # =========================================================

        if ScaleDefinition.objects.filter(
            assessment=assessment,
            dimension=dimension,
        ).exists():

            raise ValidationError({
                "dimension": (
                    "A scale for this dimension already "
                    "exists for this assessment."
                )
            })

        # =========================================================
        # 2. GET GLOBAL SEEDED SCALE
        # =========================================================

        global_scale = (
            ScaleDefinition.objects
            .filter(
                assessment__isnull=True,
                dimension=dimension,
            )
            .prefetch_related("options")
            .first()
        )

        if not global_scale:
            raise ValidationError({
                "dimension": (
                    f"No default scale is configured "
                    f"for {dimension}."
                )
            })

        # =========================================================
        # 3. VALIDATE GLOBAL SCALE OPTIONS
        # =========================================================

        global_options = list(
            global_scale.options.all()
        )

        if not global_options:

            raise ValidationError({
                "dimension": (
                    f"The default {dimension} scale "
                    "has no configured options."
                )
            })

        # =========================================================
        # 4. CREATE ASSESSMENT-SPECIFIC SCALE
        # =========================================================

        scale = serializer.save(
            assessment=assessment
        )

        # =========================================================
        # 5. COPY GLOBAL OPTIONS
        # =========================================================

        ScaleOption.objects.bulk_create([
            ScaleOption(
                scale=scale,
                value=option.value,
                label=option.label,
                description=option.description,
            )
            for option in global_options
        ])

        # =========================================================
        # 6. RETURN SCALE WITH OPTIONS
        # =========================================================

        scale = (
            ScaleDefinition.objects
            .prefetch_related("options")
            .get(pk=scale.pk)
        )

        return Response(
            ScaleDefinitionSerializer(
                scale
            ).data,
            status=status.HTTP_201_CREATED,
        )

##### survey questions endpoint #######
    @action(
        detail=True,
        methods=["get","patch"],
        url_path="survey/questions",
    )
    def survey_questions(
        self,
        request,
        pk=None,
    ):

        assessment = self.get_object()

        survey = Survey.objects.filter(
            assessment=assessment
        ).first()

        if not survey:
            raise ValidationError(
                "Survey has not been created for this assessment."
            )

        questions = (
            SurveyQuestion.objects
            .filter(survey=survey)
            .select_related(
                "assessment_topic",
                "scale",
            )
            .order_by("display_order")
        )

        # -----------------------------------------
        # GET
        # -----------------------------------------

        if request.method == "GET":

            serializer = SurveyQuestionSerializer(
                questions,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------
        # PATCH
        # -----------------------------------------

        question_id = request.data.get("id")

        if not question_id:
            raise ValidationError({
                "id": "Question id is required."
            })

        question = questions.filter(
            id=question_id
        ).first()

        if not question:
            raise ValidationError({
                "id": "Question does not belong to this survey."
            })

        serializer = SurveyQuestionSerializer(
            question,
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

#### generate survey endpoint #######
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

        # =========================================================
# 5. GET VALID SCALES
# =========================================================

        scales = {}

        for dimension in dimensions:

            # -----------------------------------------------------
            # Prefer assessment-specific scale
            # -----------------------------------------------------

            scale = (
                ScaleDefinition.objects
                .filter(
                    assessment=assessment,
                    dimension=dimension,
                )
                .prefetch_related("options")
                .first()
            )

            # -----------------------------------------------------
            # If assessment-specific scale does not exist OR
            # has no options, use the seeded global scale.
            # -----------------------------------------------------

            if (
                not scale
                or not scale.options.exists()
            ):

                scale = (
                    ScaleDefinition.objects
                    .filter(
                        assessment__isnull=True,
                        dimension=dimension,
                    )
                    .prefetch_related("options")
                    .first()
                )

            # -----------------------------------------------------
            # No usable scale
            # -----------------------------------------------------

            if not scale:

                raise ValidationError(
                    f"No scale has been configured for {dimension}."
                )

            # -----------------------------------------------------
            # No options
            # -----------------------------------------------------

            if not scale.options.exists():

                raise ValidationError(
                    f"No options have been configured "
                    f"for the {dimension} scale."
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

        company_name = assessment.company.company_name if assessment.company else "the company"

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

    # ============================================================
    # SEND SURVEY INVITATIONS
    #
    # POST:
    # /api/materiality/assessments/<id>/survey/send/
    #
    # Body:
    # {
    #     "stakeholder_ids": [
    #         "uuid1",
    #         "uuid2"
    #     ]
    # }
    # ============================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="survey/send",
    )
    @transaction.atomic
    def send_survey(self, request, pk=None):

        # ========================================================
        # 1. GET ASSESSMENT
        # ========================================================

        assessment = self.get_object()

        # ========================================================
        # 2. GET SURVEY
        # ========================================================

        survey = Survey.objects.filter(
            assessment=assessment
        ).first()

        if not survey:
            raise ValidationError(
                "Survey has not been generated for this assessment."
            )

        # ========================================================
        # 3. GET STAKEHOLDER IDS
        # ========================================================

        stakeholder_ids = request.data.get(
            "stakeholder_ids"
        )

        if not stakeholder_ids:
            raise ValidationError({
                "stakeholder_ids": (
                    "At least one stakeholder must be selected."
                )
            })

        if not isinstance(stakeholder_ids, list):
            raise ValidationError({
                "stakeholder_ids": (
                    "stakeholder_ids must be a list."
                )
            })

        # Remove duplicate stakeholder IDs
        stakeholder_ids = list(
            dict.fromkeys(stakeholder_ids)
        )

        # ========================================================
        # 4. GET VALID STAKEHOLDERS
        # ========================================================

        stakeholders = (
            Stakeholder.objects
            .filter(
                id__in=stakeholder_ids,
                group__assessment=assessment,
            )
            .select_related("group")
        )

        # ========================================================
        # 5. VALIDATE STAKEHOLDERS
        # ========================================================

        if stakeholders.count() != len(
            stakeholder_ids
        ):
            raise ValidationError({
                "stakeholder_ids": (
                    "One or more stakeholders do not "
                    "belong to this assessment."
                )
            })

        # ========================================================
        # 6. CREATE / GET INVITATIONS
        # ========================================================

        invitations = []

        for stakeholder in stakeholders:

            invitation, created = (
                SurveyInvitation.objects.get_or_create(
                    survey=survey,
                    stakeholder=stakeholder,
                    defaults={
                        "status": "NOT_SENT",
                    },
                )
            )

            invitations.append(
                invitation
            )


        # ========================================================
        # 7. SEND EMAIL
        # ========================================================

        sent_invitations = []

        for invitation in invitations:

            send_survey_invitation(
                invitation
            )

            invitation.status = "SENT"
            invitation.sent_at = timezone.now()

            invitation.save(
                update_fields=[
                    "status",
                    "sent_at",
                ]
            )

            sent_invitations.append(
                invitation
            )

        # ========================================================
        # 8. BUILD RESPONSE
        # ========================================================

        invitation_data = []

        for invitation in sent_invitations:

            invitation_data.append({
                "id": invitation.id,

                "stakeholder_id": (
                    invitation.stakeholder.id
                ),

                "stakeholder_name": (
                    invitation.stakeholder.name
                ),

                "stakeholder_email": (
                    invitation.stakeholder.email
                ),

                "status": invitation.status,

                "sent_at": invitation.sent_at,

                "token": str(
                    invitation.token
                ),

                "survey_url": (
                    f"{settings.FRONTEND_URL}/survey/"
                    f"{invitation.token}/"
                ),
            })

        # ========================================================
        # 9. RESPONSE
        # ========================================================

        return Response(
            {
                "success": True,

                "message": (
                    "Survey invitations sent successfully."
                ),

                "survey_id": survey.id,

                "count": len(
                    sent_invitations
                ),

                "invitations": invitation_data,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================
# INTERNAL EXPERT SCORING — double mode only
#
# GET, PUT:
# /api/materiality/assessments/<id>/internal-scores/
#
# PUT body: a list of items, one per sub-topic:
# [
#     {
#         "assessment_topic": "uuid",
#         "impact_type": "ACTUAL",
#         "scale": 4,
#         "scope": 3,
#         "irremediability": 5,
#         "financial_magnitude": 3,
#         "financial_likelihood": 4,
#         "rationale": "..."
#     },
#     ...
# ]
# =============================================================

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="internal-scores",
    )
    def internal_scores(self, request, pk=None):

        assessment = self.get_object()

        if assessment.mode != "DOUBLE":
            raise ValidationError(
                "Internal scoring only applies to double-materiality "
                "assessments."
            )

        # =========================================================
        # GET
        # =========================================================

        if request.method == "GET":

            scores = (
                InternalScore.objects
                .filter(
                    assessment_topic__assessment=assessment
                )
                .select_related(
                    "assessment_topic",
                    "assessment_topic__subtopic",
                )
            )

            serializer = InternalScoreSerializer(
                scores,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # =========================================================
        # PUT — bulk upsert
        # =========================================================

        if assessment.is_locked:
            raise ValidationError(
                "This assessment is approved and locked."
            )

        items = request.data

        if not isinstance(items, list) or not items:
            raise ValidationError(
                "Expected a non-empty list of scores."
            )

        saved = []

        with transaction.atomic():

            for item in items:

                topic_id = item.get("assessment_topic")

                topic = (
                    AssessmentTopic.objects
                    .filter(
                        id=topic_id,
                        assessment=assessment,
                    )
                    .first()
                )

                if not topic:
                    raise ValidationError({
                        "assessment_topic": (
                            f"'{topic_id}' does not belong to this "
                            "assessment."
                        )
                    })

                instance = InternalScore.objects.filter(
                    assessment_topic=topic
                ).first()

                serializer = InternalScoreSerializer(
                    instance=instance,
                    data=item,
                    partial=bool(instance),
                    context={
                        "assessment": assessment,
                    },
                )

                serializer.is_valid(
                    raise_exception=True
                )

                serializer.save(
                    assessment_topic=topic,
                    scored_by=request.user,
                )

                saved.append(serializer.data)

        return Response(
            saved,
            status=status.HTTP_200_OK,
        )


    # =============================================================
    # RUN SCORING
    #
    # POST:
    # /api/materiality/assessments/<id>/score/
    # =============================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="score",
    )
    def run_score(self, request, pk=None):

        assessment = self.get_object()

        try:
            score_run = run_scoring(
                assessment,
                request.user,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                getattr(exc, "message", str(exc))
            )

        return Response(
            ScoreRunSerializer(score_run).data,
            status=status.HTTP_201_CREATED,
        )


    # =============================================================
    # RESULTS — latest score run
    #
    # GET:
    # /api/materiality/assessments/<id>/results/
    # =============================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="results",
    )
    def results(self, request, pk=None):

        assessment = self.get_object()

        latest_run = (
            ScoreRun.objects
            .filter(
                assessment=assessment
            )
            .order_by("-run_at")
            .prefetch_related(
                "topic_results__assessment_topic__subtopic__topic__category",
            )
            .first()
        )

        if not latest_run:
            return Response(
                {
                    "detail": "No score run yet for this assessment.",
                    "topic_results": [],
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            ScoreRunSerializer(latest_run).data,
            status=status.HTTP_200_OK,
        )


    # =============================================================
    # MANUAL OVERRIDE
    #
    # PATCH:
    # /api/materiality/assessments/<id>/topics/<topic_id>/override/
    # =============================================================

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"topics/(?P<topic_id>[^/.]+)/override",
    )
    def override_topic(
        self,
        request,
        pk=None,
        topic_id=None,
    ):

        assessment = self.get_object()

        if assessment.is_locked:
            raise ValidationError(
                "This assessment is approved and locked."
            )

        topic = (
            AssessmentTopic.objects
            .filter(
                id=topic_id,
                assessment=assessment,
            )
            .first()
        )

        if not topic:
            raise ValidationError(
                "This sub-topic does not belong to this assessment."
            )

        serializer = AssessmentTopicOverrideSerializer(
            instance=topic,
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


    # =============================================================
    # SCORE RUN HISTORY
    #
    # GET:
    # /api/materiality/assessments/<id>/score-runs/
    # =============================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="score-runs",
    )
    def score_runs(self, request, pk=None):

        assessment = self.get_object()

        runs = (
            ScoreRun.objects
            .filter(
                assessment=assessment
            )
            .order_by("-run_at")
        )

        serializer = ScoreRunListSerializer(
            runs,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )       
    


###### Public survey Api view ######

# ============================================================
# PUBLIC SURVEY
# ============================================================

GENERIC_SURVEY_ACCESS_ERROR = {
    "detail": "This survey link is invalid or has expired."
}


def get_public_survey_invitation(token, lock=False):
    """
    Resolve a public survey token to its SurveyInvitation.

    The token is the only credential required by the stakeholder.
    No login/JWT authentication is required.
    """

    # --------------------------------------------------------
    # 1. Validate UUID format
    # --------------------------------------------------------

    try:
        token_uuid = uuid.UUID(str(token))
    except (ValueError, TypeError, AttributeError):

        raise NotFound(
            GENERIC_SURVEY_ACCESS_ERROR
        )

    # --------------------------------------------------------
    # 2. Get invitation
    # --------------------------------------------------------

    queryset = (
        SurveyInvitation.objects
        .select_related(
            "survey",
            "survey__assessment",
            "stakeholder",
        )
    )

    # Lock the invitation when modifying it.
    if lock:
        queryset = queryset.select_for_update()

    invitation = (
        queryset
        .filter(token=token_uuid)
        .first()
    )

    # --------------------------------------------------------
    # 3. Invalid token
    # --------------------------------------------------------

    if not invitation:
        raise NotFound(
            GENERIC_SURVEY_ACCESS_ERROR
        )

    survey = invitation.survey
    now = timezone.now()

    # --------------------------------------------------------
    # 4. Survey closed
    # --------------------------------------------------------

    if survey.status == "CLOSED":

        raise NotFound(
            GENERIC_SURVEY_ACCESS_ERROR
        )

    # --------------------------------------------------------
    # 5. Survey has not opened yet
    # --------------------------------------------------------

    if (
        survey.opens_at
        and survey.opens_at > now
    ):

        raise NotFound(
            GENERIC_SURVEY_ACCESS_ERROR
        )

    # --------------------------------------------------------
    # 6. Survey has expired
    # --------------------------------------------------------

    if (
        survey.closes_at
        and survey.closes_at < now
    ):

        raise NotFound(
            GENERIC_SURVEY_ACCESS_ERROR
        )

    return invitation


def build_public_survey_response(invitation):
    """
    Build the survey payload required by the public frontend.

    Only responses belonging to this exact invitation are returned.
    """

    survey = invitation.survey

    # ========================================================
    # EXISTING RESPONSES FOR THIS INVITATION ONLY
    # ========================================================

    responses = {
        response.question_id: response
        for response in (
            SurveyResponse.objects
            .filter(
                invitation=invitation
            )
        )
    }

    # ========================================================
    # QUESTIONS
    # ========================================================

    questions = (
        SurveyQuestion.objects
        .filter(
            survey=survey
        )
        .select_related(
            "assessment_topic",
            "assessment_topic__subtopic",
            "assessment_topic__subtopic__topic",
            "assessment_topic__subtopic__topic__category",
            "scale",
        )
        .prefetch_related(
            "scale__options"
        )
        .order_by(
            "display_order"
        )
    )

    question_data = []

    for question in questions:

        saved_response = responses.get(
            question.id
        )

        assessment_topic = (
            question.assessment_topic
        )

        subtopic = (
            assessment_topic.subtopic
        )

        topic = subtopic.topic
        category = topic.category

        # ====================================================
        # QUESTION
        # ====================================================

        question_data.append(
            {
                "id": question.id,

                "assessment_topic": (
                    assessment_topic.id
                ),

                "category_name": (
                    category.name
                ),

                "topic_name": (
                    topic.name
                ),

                "subtopic_name": (
                    subtopic.name
                ),

                "dimension": (
                    question.dimension
                ),

                "question_text": (
                    question.question_text
                ),

                "help_text": (
                    question.help_text
                ),

                "display_order": (
                    question.display_order
                ),

                "is_required": (
                    question.is_required
                ),

                # ==========================================
                # SCALE
                # ==========================================

                "scale": {
                    "id": question.scale.id,

                    "dimension": (
                        question.scale.dimension
                    ),

                    "name": (
                        question.scale.name
                    ),

                    "options": [
                        {
                            "id": option.id,
                            "value": option.value,
                            "label": option.label,
                            "description": (
                                option.description
                            ),
                        }
                        for option
                        in question.scale.options.all()
                    ],
                },

                # ==========================================
                # PREVIOUSLY SAVED ANSWER
                # ==========================================

                "response": (
                    {
                        "id": saved_response.id,

                        "question": (
                            saved_response.question_id
                        ),

                        "value": (
                            saved_response.value
                        ),

                        "comment": (
                            saved_response.comment
                        ),

                        "answered_at": (
                            saved_response.answered_at
                        ),
                    }
                    if saved_response
                    else None
                ),
            }
        )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "success": True,

        "survey": {
            "id": survey.id,
            "title": survey.title,
            "intro_text": survey.intro_text,
            "closing_text": survey.closing_text,
            "status": survey.status,
            "opens_at": survey.opens_at,
            "closes_at": survey.closes_at,
        },

        "invitation": {
            "id": invitation.id,

            "status": (
                invitation.status
            ),

            "first_opened_at": (
                invitation.first_opened_at
            ),

            "submitted_at": (
                invitation.submitted_at
            ),

            "is_submitted": (
                invitation.status == "SUBMITTED"
            ),
        },

        "questions": question_data,
    }


# ============================================================
# GET PUBLIC SURVEY
# ============================================================


class PublicSurveyView(APIView):

    authentication_classes = []

    permission_classes = [
        AllowAny
    ]

    throttle_classes = [
        AnonRateThrottle
    ]

    def get(self, request, token):

        # ----------------------------------------------------
        # Get invitation
        # ----------------------------------------------------

        invitation = get_public_survey_invitation(
            token
        )

        # ----------------------------------------------------
        # Already submitted
        # ----------------------------------------------------

        if invitation.status == "SUBMITTED":

            return Response(
                {
                    "success": True,
                    "submitted": True,
                    "message": (
                        "This survey has already been submitted."
                    ),
                    "submitted_at": (
                        invitation.submitted_at
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------------------
        # First opening
        # ----------------------------------------------------

        if not invitation.first_opened_at:

            invitation.first_opened_at = (
                timezone.now()
            )

            invitation.status = "OPENED"

            invitation.save(
                update_fields=[
                    "first_opened_at",
                    "status",
                ]
            )

        # ----------------------------------------------------
        # Return survey
        # ----------------------------------------------------

        return Response(
            build_public_survey_response(
                invitation
            ),
            status=status.HTTP_200_OK,
        )


# ============================================================
# SAVE / UPDATE ANSWER
# ============================================================


class PublicSurveyAnswerView(APIView):

    authentication_classes = []

    permission_classes = [
        AllowAny
    ]

    throttle_classes = [
        AnonRateThrottle
    ]

    @transaction.atomic
    def post(self, request, token):

        # ----------------------------------------------------
        # Lock invitation while modifying response
        # ----------------------------------------------------

        invitation = get_public_survey_invitation(
            token,
            lock=True,
        )

        # ----------------------------------------------------
        # Cannot answer after submission
        # ----------------------------------------------------

        if invitation.status == "SUBMITTED":

            raise ValidationError(
                {
                    "detail": (
                        "This survey has already been submitted."
                    )
                }
            )

        # ----------------------------------------------------
        # Request data
        # ----------------------------------------------------

        question_id = request.data.get(
            "question"
        )

        value = request.data.get(
            "value"
        )

        comment = request.data.get(
            "comment",
            "",
        )

        # ----------------------------------------------------
        # Validate question
        # ----------------------------------------------------

        if not question_id:

            raise ValidationError(
                {
                    "question": (
                        "Question is required."
                    )
                }
            )

        # ----------------------------------------------------
        # Find question belonging to this survey
        # ----------------------------------------------------

        question = (
            SurveyQuestion.objects
            .select_related(
                "scale"
            )
            .filter(
                id=question_id,
                survey=invitation.survey,
            )
            .first()
        )

        if not question:

            raise ValidationError(
                {
                    "question": (
                        "Question does not belong "
                        "to this survey."
                    )
                }
            )

        # ----------------------------------------------------
        # Validate value exists
        # ----------------------------------------------------

        if value is None:

            raise ValidationError(
                {
                    "value": (
                        "Value is required."
                    )
                }
            )

        # ----------------------------------------------------
        # Convert value to integer
        # ----------------------------------------------------

        try:

            value = int(value)

        except (
            TypeError,
            ValueError,
        ):

            raise ValidationError(
                {
                    "value": (
                        "Value must be a number."
                    )
                }
            )

        # ----------------------------------------------------
        # Validate value against scale
        # ----------------------------------------------------

        valid_value = (
            ScaleOption.objects
            .filter(
                scale=question.scale,
                value=value,
            )
            .exists()
        )

        if not valid_value:

            raise ValidationError(
                {
                    "value": (
                        "Value is not valid for "
                        "this question's scale."
                    )
                }
            )

        # ----------------------------------------------------
        # Save / update response
        # ----------------------------------------------------

        response, created = (
            SurveyResponse.objects
            .update_or_create(
                invitation=invitation,
                question=question,
                defaults={
                    "value": value,
                    "comment": str(
                        comment
                    ).strip(),
                    "answered_at": (
                        timezone.now()
                    ),
                },
            )
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return Response(
            {
                "success": True,

                "id": response.id,

                "question": (
                    response.question_id
                ),

                "value": response.value,

                "comment": response.comment,

                "answered_at": (
                    response.answered_at
                ),
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


# ============================================================
# SUBMIT SURVEY
# ============================================================


class PublicSurveySubmitView(APIView):

    authentication_classes = []

    permission_classes = [
        AllowAny
    ]

    throttle_classes = [
        AnonRateThrottle
    ]

    @transaction.atomic
    def post(self, request, token):

        # ----------------------------------------------------
        # Lock invitation
        # ----------------------------------------------------

        invitation = get_public_survey_invitation(
            token,
            lock=True,
        )

        # ----------------------------------------------------
        # Already submitted
        # ----------------------------------------------------

        if invitation.status == "SUBMITTED":

            return Response(
                {
                    "success": True,
                    "submitted": True,
                    "message": (
                        "This survey has already been submitted."
                    ),
                    "submitted_at": (
                        invitation.submitted_at
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------------------
        # Required questions
        # ----------------------------------------------------

        required_question_ids = set(
            SurveyQuestion.objects
            .filter(
                survey=invitation.survey,
                is_required=True,
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        # ----------------------------------------------------
        # Answered required questions
        # ----------------------------------------------------

        answered_question_ids = set(
            SurveyResponse.objects
            .filter(
                invitation=invitation,
                question_id__in=(
                    required_question_ids
                ),
            )
            .values_list(
                "question_id",
                flat=True,
            )
        )

        # ----------------------------------------------------
        # Find missing questions
        # ----------------------------------------------------

        missing_question_ids = (
            required_question_ids
            - answered_question_ids
        )

        if missing_question_ids:

            return Response(
                {
                    "success": False,

                    "message": (
                        "All required questions must "
                        "be answered before submitting."
                    ),

                    "missing_question_ids": (
                        list(
                            missing_question_ids
                        )
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Submit survey
        # ----------------------------------------------------

        invitation.status = "SUBMITTED"

        invitation.submitted_at = (
            timezone.now()
        )

        invitation.save(
            update_fields=[
                "status",
                "submitted_at",
            ]
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return Response(
            {
                "success": True,

                "submitted": True,

                "message": (
                    "Survey submitted successfully."
                ),

                "submitted_at": (
                    invitation.submitted_at
                ),
            },
            status=status.HTTP_200_OK,
        )


    
    
