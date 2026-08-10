from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OrgNode
from apps.companies.models import Company


@receiver(post_save, sender=Company)
def create_root_org_node(sender, instance, created, **kwargs):
    if not created:
        return

    OrgNode.objects.create(
        company=instance,
        parent=None,
        node_type="LEGAL_ENTITY",
        code=instance.company_code.lower(),
        name=instance.company_name,
    )