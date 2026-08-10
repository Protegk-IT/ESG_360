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