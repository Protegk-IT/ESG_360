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
        default=0,
    )

    secondary_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
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
        return f"{self.name} - {self.financial_year}"

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
# ============================================================
# PHASE 5
# SURVEY RESPONSE
# ============================================================

class SurveyResponse(BaseModel):

    invitation = models.ForeignKey(
        SurveyInvitation,
        on_delete=models.CASCADE,
        related_name="responses",
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
        ]

    def __str__(self):
        return f"{self.invitation} - {self.question}"           