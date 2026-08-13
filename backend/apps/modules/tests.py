from django.core.exceptions import ValidationError
from django.core.management import call_command
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

        with self.assertRaises(ValidationError):
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

    def test_core_module_can_be_enabled(self):
        module = Module(
            code="company",
            name="Company",
            esg_pillar=ESGPillar.PLATFORM,
            is_core=True,
            is_enabled=True,
        )

        module.full_clean()

        self.assertTrue(module.is_core)
        self.assertTrue(module.is_enabled)

    def test_non_core_module_can_be_disabled(self):
        module = Module(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
            is_core=False,
            is_enabled=False,
        )

        module.full_clean()

        self.assertFalse(module.is_core)
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
        self.assertEqual(module.name, "Materiality")
        self.assertFalse(module.is_enabled)

    def test_valid_esg_pillars(self):
        pillars = [
            ESGPillar.E,
            ESGPillar.S,
            ESGPillar.G,
            ESGPillar.PLATFORM,
        ]

        for index, pillar in enumerate(pillars):
            module = Module(
                code=f"test-module-{index}",
                name=f"Test Module {index}",
                esg_pillar=pillar,
            )

            module.full_clean()

            self.assertEqual(module.esg_pillar, pillar)


class ModuleSeedCommandTests(TestCase):
    def test_seed_modules_creates_canonical_modules(self):
        call_command("seed_modules")

        expected_codes = {
            "company",
            "org",
            "user",
            "period",
            "energy",
            "emissions",
            "water",
            "waste",
            "social",
            "governance",
            "supplier",
            "materiality",
            "report",
        }

        actual_codes = set(
            Module.objects.values_list("code", flat=True)
        )

        self.assertEqual(actual_codes, expected_codes)

    def test_seed_modules_is_idempotent(self):
        call_command("seed_modules")

        first_count = Module.objects.count()

        call_command("seed_modules")

        second_count = Module.objects.count()

        self.assertEqual(first_count, second_count)

    def test_seed_modules_updates_existing_module(self):
        Module.objects.create(
            code="company",
            name="Old Company Name",
            description="Old description",
            esg_pillar=ESGPillar.PLATFORM,
            is_core=True,
            is_enabled=True,
            display_order=999,
        )

        call_command("seed_modules")

        module = Module.objects.get(code="company")

        self.assertEqual(module.name, "Company")
        self.assertTrue(module.is_core)
        self.assertTrue(module.is_enabled)
        self.assertEqual(module.display_order, 1)


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

    def create_user(self, username="module_test_user"):
        return User.objects.create_user(
            username=username,
            password="testpassword123",
        )

    def get_response_data(self, response):
        data = response.data

        # Handle both paginated and non-paginated DRF responses.
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        return data

    def test_module_api_requires_authentication(self):
        response = self.client.get("/api/modules/")

        self.assertEqual(response.status_code, 403)

    def test_module_api_returns_modules_in_display_order(self):
        user = self.create_user()

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/")

        self.assertEqual(response.status_code, 200)

        data = self.get_response_data(response)

        self.assertEqual(
            [module["code"] for module in data],
            ["company", "energy", "emissions"],
        )

    def test_module_api_enabled_filter(self):
        user = self.create_user("module_filter_user")

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/?enabled=true")

        self.assertEqual(response.status_code, 200)

        data = self.get_response_data(response)

        self.assertEqual(
            [module["code"] for module in data],
            ["company", "energy"],
        )

    def test_module_api_returns_disabled_modules_when_enabled_false(self):
        user = self.create_user("module_disabled_filter_user")

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/?enabled=false")

        self.assertEqual(response.status_code, 200)

        data = self.get_response_data(response)

        self.assertEqual(
            [module["code"] for module in data],
            ["emissions"],
        )

    def test_module_api_returns_module_fields(self):
        user = self.create_user("module_fields_user")

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/modules/")

        self.assertEqual(response.status_code, 200)

        data = self.get_response_data(response)

        company = next(
            module for module in data if module["code"] == "company"
        )

        self.assertEqual(company["code"], "company")
        self.assertEqual(company["name"], "Company")
        self.assertEqual(company["esg_pillar"], ESGPillar.PLATFORM)
        self.assertTrue(company["is_core"])
        self.assertTrue(company["is_enabled"])
        self.assertEqual(company["display_order"], 1)