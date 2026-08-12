from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User

from .models import ESGPillar, Module


class ModuleModelTests(TestCase):
    def test_module_code_is_unique(self):
        Module.objects.create(
            code="company",
            name="Company",
            esg_pillar=ESGPillar.PLATFORM,
        )

        with self.assertRaises(Exception):
            Module.objects.create(
                code="company",
                name="Another Company",
                esg_pillar=ESGPillar.PLATFORM,
            )

    def test_core_module_cannot_be_disabled(self):
        module = Module(
            code="company",
            name="Company",
            esg_pillar=ESGPillar.PLATFORM,
            is_core=True,
            is_enabled=False,
        )

        with self.assertRaises(ValidationError):
            module.full_clean()

    def test_non_core_module_can_be_disabled(self):
        module = Module(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
            is_core=False,
            is_enabled=False,
        )

        module.full_clean()

        self.assertFalse(module.is_enabled)

    def test_materiality_module_exists_without_dependency(self):
        module = Module.objects.create(
            code="materiality",
            name="Materiality",
            esg_pillar=ESGPillar.PLATFORM,
            is_core=False,
            is_enabled=False,
            display_order=50,
        )

        self.assertEqual(module.code, "materiality")
        self.assertFalse(module.is_enabled)


class ModuleAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.company = Module.objects.create(
            code="company",
            name="Company",
            esg_pillar=ESGPillar.PLATFORM,
            is_core=True,
            is_enabled=True,
            display_order=1,
        )

        self.energy = Module.objects.create(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
            is_core=False,
            is_enabled=True,
            display_order=10,
        )

        self.emissions = Module.objects.create(
            code="emissions",
            name="Emissions",
            esg_pillar=ESGPillar.E,
            is_core=False,
            is_enabled=False,
            display_order=11,
        )

    def test_module_api_requires_authentication(self):
        response = self.client.get("/api/modules/")

        self.assertEqual(response.status_code, 403)

    def test_module_api_returns_modules_in_display_order(self):
        user = User.objects.create_user(
            username="module_test_user",
            password="testpassword123",
        )

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/")

        self.assertEqual(response.status_code, 200)

        data = response.data

        # Handle both paginated and non-paginated DRF responses.
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        self.assertEqual(
            [module["code"] for module in data],
            ["company", "energy", "emissions"],
        )

    def test_module_api_enabled_filter(self):
        user = User.objects.create_user(
            username="module_filter_user",
            password="testpassword123",
        )

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/?enabled=true")

        self.assertEqual(response.status_code, 200)

        data = response.data

        # Handle both paginated and non-paginated DRF responses.
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        self.assertEqual(
            [module["code"] for module in data],
            ["company", "energy"],
        )