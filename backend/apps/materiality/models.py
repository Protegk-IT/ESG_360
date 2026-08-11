import uuid

from django.db import models


from apps.companies.models import Company


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


class MaterialityAssessment(BaseModel):

    MODE_CHOICES = [
        ("IMPACT", "Impact Materiality"),
        ("FINANCIAL", "Financial Materiality"),
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

    name = models.CharField(
        max_length=200,
    )

    financial_year = models.CharField(
        max_length=20,
    )

    period_start = models.DateField()

    period_end = models.DateField()

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

    scale_min = models.IntegerField(
        default=1,
    )

    scale_max = models.IntegerField(
        default=5,
    )

    internal_blend_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.50,
    )

    is_locked = models.BooleanField(
        default=False,
    )

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

    def __str__(self):
        return f"{self.assessment} - {self.subtopic}"