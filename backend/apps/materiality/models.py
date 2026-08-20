import uuid

from django.db import models


from apps.companies.models import Company
from django.core.exceptions import ValidationError

class TopicCategory(models.Model):

    CATEGORY_CHOICES = [
        ("E", "Environmental"),
        ("S", "Social"),
        ("G", "Governance"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=1,
        choices=CATEGORY_CHOICES,
    )

    name = models.CharField(
        max_length=100,
    )

    display_order = models.IntegerField(
        default=0,
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        db_table = "topic_category"
        ordering = ["display_order", "name"]

# Topic model 
class MaterialTopic(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    category = models.ForeignKey(
        TopicCategory,
        on_delete=models.CASCADE,
        related_name="topics",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="material_topics",
    )

    code = models.PositiveIntegerField(
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.IntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )



    def save(self, *args, **kwargs):
        if not self.code:
            last_topic = (
                MaterialTopic.objects
                .filter(
                    category=self.category,
                    company=self.company,
                )
                .order_by("-code")
                .first()
            )

            self.code = last_topic.code + 1 if last_topic else 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        db_table = "material_topic"
        ordering = ["display_order", "name"]  


# subtopic model 

class MaterialSubTopic(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    topic = models.ForeignKey(
        MaterialTopic,
        on_delete=models.CASCADE,
        related_name="subtopics",
    )

    code = models.CharField(
        max_length=20,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.IntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            last_subtopic = (
                MaterialSubTopic.objects
                .filter(topic=self.topic)
                .order_by("-id")
                .first()
            )

            if last_subtopic:
                last_number = int(last_subtopic.code.split(".")[-1])
                next_number = last_number + 1
            else:
                next_number = 1

            self.code = f"{self.topic.code}.{next_number}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        db_table = "material_subtopic"
        ordering = ["display_order", "name"]              


# Materiality Assesment models 
# 

from django.conf import settings
from django.db import models

from apps.companies.models import Company
from apps.core.models import BaseModel
from apps.periods.models import ReportingPeriod 

class MaterialityAssessment(BaseModel):

    MODE_CHOICES = [
        ("SINGLE", "Single Materiality"),
        ("DOUBLE", "Double Materiality"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("APPROVED", "Approved"),
        ("SCORED", "Scored"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="materiality_assessments",
    )

    name = models.CharField(max_length=200)

    # Main relationship
    reporting_period = models.ForeignKey(
        ReportingPeriod,
        on_delete=models.PROTECT,
        related_name="materiality_assessments",
    )

    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default="DOUBLE",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    primary_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.50,
    )

    secondary_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.50,
    )

    scale_min = models.IntegerField(default=1)
    scale_max = models.IntegerField(default=5)

    internal_blend_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.50,
    )

    is_locked = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_materiality_assessments",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_materiality_assessments",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "materiality_assessment"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Assessment {self.pk}"

# Another model to store     
class AssessmentTopic(BaseModel):

    assessment = models.ForeignKey(
        MaterialityAssessment,
        on_delete=models.CASCADE,
        related_name="assessment_topics",
    )

    subtopic = models.ForeignKey(
        MaterialSubTopic,
        on_delete=models.CASCADE,
        related_name="assessment_topics",
    )

    is_included = models.BooleanField(
        default=True,
    )

    display_order = models.IntegerField(
        default=0,
    )

    primary_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    secondary_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    classification = models.CharField(
        max_length=50,
        blank=True,
    )

    is_override = models.BooleanField(
        default=False,
    )

    override_reason = models.TextField(
        blank=True,
    )

    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materiality_topic_overrides",
    )

    class Meta:
        db_table = "assessment_topic"
        ordering = ["display_order"]

        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "subtopic"],
                name="unique_assessment_subtopic",
            ),
        ]
    def __str__(self):
        return f"{self.assessment} - {self.subtopic}"
    



### STAKEHOLDER GROUP 
class StakeholderGroup(BaseModel):

    assessment = models.ForeignKey(
        MaterialityAssessment,
        on_delete=models.CASCADE,
        related_name="stakeholder_groups",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    is_internal = models.BooleanField(
        default=False,
    )

    def clean(self):
        """
        Validate the individual stakeholder group's weight.

        This validates:
        - weight cannot be negative
        - weight cannot exceed 100
        """

        if self.weight < 0:
            raise ValidationError({
                "weight": "Weight cannot be negative."
            })

        if self.weight > 100:
            raise ValidationError({
                "weight": "Weight cannot be greater than 100."
            })

    def __str__(self):
        return self.name

    class Meta:
        db_table = "stakeholder_group"
        ordering = ["name"]


# ============================================================
# PHASE 3
# STAKEHOLDER
# ============================================================

class Stakeholder(BaseModel):

    group = models.ForeignKey(
        StakeholderGroup,
        on_delete=models.CASCADE,
        related_name="stakeholders",
    )

    name = models.CharField(
        max_length=255,
    )

    email = models.EmailField()

    organisation = models.CharField(
        max_length=255,
        blank=True,
    )

    designation = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "stakeholder"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["group", "email"],
                name="unique_stakeholder_email_per_group",
            ),
        ]


##### SURVEY MODELS #######

class Survey(BaseModel):
    """
    Stores the survey configuration for a materiality assessment.
    One assessment can have one survey.
    """

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("READY", "Ready"),
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
    ]

    # Survey belongs to exactly one materiality assessment.
    assessment = models.OneToOneField(
        MaterialityAssessment,
        on_delete=models.CASCADE,
        related_name="survey",
    )

    # Content displayed to stakeholders.
    title = models.CharField(
        max_length=255,
    )

    intro_text = models.TextField(
        blank=True,
    )

    closing_text = models.TextField(
        blank=True,
    )

    # Controls when the survey is available.
    opens_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closes_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Controls the survey lifecycle.
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    class Meta:
        db_table = "survey"

    def __str__(self):
        return self.title
    


class ScaleDefinition(BaseModel):
    """
    Defines a scoring scale for a materiality dimension.
    The actual values/options of the scale are stored in ScaleOption.
    """

    DIMENSION_CHOICES = [
        ("IMPACT", "Impact"),
        ("STAKEHOLDER_IMPORTANCE", "Stakeholder Importance"),
        ("FINANCIAL", "Financial"),
    ]

    # Optional assessment-specific scale.
    # NULL represents a reusable/default scale.
    assessment = models.ForeignKey(
        MaterialityAssessment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scale_definitions",
    )

    # Defines what the scale measures.
    dimension = models.CharField(
        max_length=50,
        choices=DIMENSION_CHOICES,
    )

    # Name of the scale.
    name = models.CharField(
        max_length=255,
    )

    class Meta:
        db_table = "scale_definition"

    def __str__(self):
        return self.name



class ScaleOption(BaseModel):
    """
    Stores the individual values/options belonging to a scale.
    Example: 1 = Very Low, 2 = Low, ..., 5 = Very High.
    """

    # Scale to which this option belongs.
    scale = models.ForeignKey(
        ScaleDefinition,
        on_delete=models.CASCADE,
        related_name="options",
    )

    # Actual numeric value used for scoring.
    value = models.IntegerField()

    # Display label for the value.
    label = models.CharField(
        max_length=255,
    )

    # Optional explanation of the option.
    description = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "scale_option"
        ordering = ["value"]

        constraints = [
            models.UniqueConstraint(
                fields=["scale", "value"],
                name="unique_scale_option_value",
            ),
        ]

    def __str__(self):
        return f"{self.scale.name} - {self.value}: {self.label}"


class SurveyQuestion(BaseModel):
    """
    Stores an individual question in a survey.
    Each question is linked to a selected assessment topic
    and the scale used to answer that question.
    """

    DIMENSION_CHOICES = [
        ("IMPACT", "Impact"),
        ("STAKEHOLDER_IMPORTANCE", "Stakeholder Importance"),
        ("FINANCIAL", "Financial"),
    ]

    # Survey containing this question.
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    # Selected topic/subtopic being evaluated.
    assessment_topic = models.ForeignKey(
        AssessmentTopic,
        on_delete=models.CASCADE,
        related_name="survey_questions",
    )

    # Scale used for answering this question.
    scale = models.ForeignKey(
        ScaleDefinition,
        on_delete=models.PROTECT,
        related_name="survey_questions",
    )

    # Dimension being evaluated by this question.
    dimension = models.CharField(
        max_length=50,
        choices=DIMENSION_CHOICES,
    )

    # Actual question shown to the stakeholder.
    question_text = models.TextField()

    # Optional explanation/instructions for the question.
    help_text = models.TextField(
        blank=True,
    )

    # Controls question order in the survey.
    display_order = models.IntegerField(
        default=0,
    )

    # Whether the stakeholder must answer the question.
    is_required = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "survey_question"
        ordering = ["display_order"]

    def __str__(self):
        return self.question_text

# ============================================================
# PHASE 5
# SURVEY INVITATION
# ============================================================

class SurveyInvitation(BaseModel):

    STATUS_CHOICES = [
        ("NOT_SENT", "Not Sent"),
        ("SENT", "Sent"),
        ("OPENED", "Opened"),
        ("SUBMITTED", "Submitted"),
    ]

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    stakeholder = models.ForeignKey(
        Stakeholder,
        on_delete=models.CASCADE,
        related_name="survey_invitations",
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    first_opened_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NOT_SENT",
    )

    class Meta:
        db_table = "survey_invitation"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["survey", "stakeholder"],
                name="unique_survey_stakeholder_invitation",
            ),
        ]

    def __str__(self):
        return f"{self.survey.title} - {self.stakeholder.name}"


class SurveyGroupLink(BaseModel):
    """A reusable public link for anonymous respondents in one stakeholder group."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="group_links")
    stakeholder_group = models.ForeignKey(
        StakeholderGroup, on_delete=models.CASCADE, related_name="survey_links"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "survey_group_link"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "stakeholder_group"],
                name="unique_survey_stakeholder_group_link",
            ),
        ]


class SurveySubmission(BaseModel):
    """One respondent's in-progress or submitted answer set.

    Invitations produce identified submissions; group links produce anonymous
    submissions.  The opaque response token prevents one anonymous browser
    from overwriting another respondent's answers.
    """

    SOURCE_CHOICES = [("IDENTIFIED", "Identified invitation"), ("ANONYMOUS", "Anonymous group link")]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="submissions")
    stakeholder_group = models.ForeignKey(
        StakeholderGroup, on_delete=models.PROTECT, related_name="survey_submissions"
    )
    invitation = models.OneToOneField(
        SurveyInvitation,
        on_delete=models.CASCADE,
        related_name="submission",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    response_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "survey_submission"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(source="IDENTIFIED", invitation__isnull=False)
                    | models.Q(source="ANONYMOUS", invitation__isnull=True)
                ),
                name="survey_submission_source_matches_invitation",
            ),
        ]

    def clean(self):
        if self.invitation_id:
            if self.invitation.survey_id != self.survey_id:
                raise ValidationError("Invitation must belong to this survey.")
            if self.invitation.stakeholder.group_id != self.stakeholder_group_id:
                raise ValidationError("Invitation must belong to this stakeholder group.")
# ============================================================
# PHASE 5
# SURVEY RESPONSE
# ============================================================

class SurveyResponse(BaseModel):

    invitation = models.ForeignKey(
        SurveyInvitation,
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
    )

    submission = models.ForeignKey(
        SurveySubmission,
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
    )

    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name="responses",
    )

    value = models.IntegerField()

    comment = models.TextField(
        blank=True,
    )

    answered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "survey_response"
        ordering = ["created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["invitation", "question"],
                name="unique_invitation_question_response",
            ),
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="unique_submission_question_response",
            ),
        ]

    def __str__(self):
        return f"{self.invitation} - {self.question}"           
    

##### SCORING MODELS #######
#     
from django.core.validators import MaxValueValidator, MinValueValidator

# assuming BaseModel already exists in your project

class InternalScore(BaseModel):
    IMPACT_TYPE_CHOICES = [
        ("ACTUAL", "Actual"),
        ("POTENTIAL", "Potential"),
    ]

    assessment_topic = models.OneToOneField(
        "AssessmentTopic",
        on_delete=models.CASCADE,
        related_name="internal_score",
    )

    impact_type = models.CharField(
        max_length=20,
        choices=IMPACT_TYPE_CHOICES,
    )

    scale = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    scope = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    irremediability = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    likelihood = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    financial_magnitude = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    financial_likelihood = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    rationale = models.TextField(
        blank=True,
    )

    scored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="internal_materiality_scores",
    )

    scored_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "internal_score"

    def __str__(self):
        return (
            f"Internal score - "
            f"{self.assessment_topic}"
        )
    


class ScoreRun(BaseModel):
    assessment = models.ForeignKey(
        "MaterialityAssessment",
        on_delete=models.CASCADE,
        related_name="score_runs",
    )

    mode = models.CharField(
        max_length=20,
    )

    thresholds_snapshot = models.JSONField()

    group_weights_snapshot = models.JSONField()

    response_count = models.PositiveIntegerField(
        default=0,
    )

    invited_count = models.PositiveIntegerField(
        default=0,
    )

    method_version = models.CharField(
        max_length=50,
    )

    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="materiality_score_runs",
    )

    run_at = models.DateTimeField(
        auto_now_add=True,
    )

    # NEW — per-group survey breakdown snapshot, keyed by dimension
    

    class Meta:
        db_table = "score_run"
        ordering = ["-run_at"]

    def __str__(self):
        return (
            f"Score Run - "
            f"{self.assessment} - "
            f"{self.run_at}"
        )
    

class ScoreRunTopic(BaseModel):
    score_run = models.ForeignKey(
        ScoreRun,
        on_delete=models.CASCADE,
        related_name="topic_results",
    )

    assessment_topic = models.ForeignKey(
        "AssessmentTopic",
        on_delete=models.CASCADE,
        related_name="score_run_results",
    )

    primary_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    secondary_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    classification = models.CharField(
        max_length=30,
    )

    is_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)

    group_breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "score_run_topic"
        ordering = ["created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "score_run",
                    "assessment_topic",
                ],
                name="unique_score_run_assessment_topic",
            ),
        ]

    def __str__(self):
        return (
            f"{self.score_run} - "
            f"{self.assessment_topic}"
        )
