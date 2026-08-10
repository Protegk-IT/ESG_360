from django.test import TestCase

from apps.companies.models import Company
from .models import OrgNode


class OrgNodePathTests(TestCase):
    def test_renaming_a_parent_code_updates_descendant_paths(self):
        company = Company.objects.create(
            company_name="Acme", company_code="ACME", contact_person="Owner",
            email="owner@example.com", mobile_number="1234567890",
        )
        root = OrgNode.objects.get(company=company, parent__isnull=True)
        child = OrgNode.objects.create(
            company=company, parent=root, node_type="BUSINESS_UNIT",
            code="OPS", name="Operations",
        )
        root.code = "acme-holdings"
        root.save()
        child.refresh_from_db()

        self.assertEqual(child.depth, 1)
        self.assertEqual(child.path, "/acme-holdings/OPS/")
