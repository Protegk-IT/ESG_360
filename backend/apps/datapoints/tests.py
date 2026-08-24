from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.datapoints.models import (
    CollectionFrequency,
    CollectionLevel,
    Datapoint,
    DatapointCategory,
    DatapointDataType,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
    Unit,
    UnitFamily,
)
from apps.modules.models import ESGPillar, Module


class DatapointCatalogTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.energy_module = Module.objects.create(
            code="energy",
            name="Energy",
            esg_pillar=ESGPillar.E,
            display_order=1,
        )
        cls.water_module = Module.objects.create(
            code="water",
            name="Water",
            esg_pillar=ESGPillar.E,
            display_order=2,
        )
        cls.category = DatapointCategory.objects.create(
            code="ENERGY",
            name="Energy",
            module=cls.energy_module,
        )
        cls.energy_family = UnitFamily.objects.create(code="ENERGY", name="Energy")
        cls.mass_family = UnitFamily.objects.create(code="MASS", name="Mass")
        cls.kwh = Unit.objects.create(
            family=cls.energy_family,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )
        cls.mwh = Unit.objects.create(
            family=cls.energy_family,
            code="MWH",
            name="Megawatt-hour",
            factor_to_base=Decimal("1000"),
        )
        cls.kg = Unit.objects.create(
            family=cls.mass_family,
            code="KG",
            name="Kilogram",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

    def make_datapoint(self, code, data_type, **overrides):
        data = {
            "code": code,
            "category": self.category,
            "module": self.energy_module,
            "label": code.replace("_", " ").title(),
            "data_type": data_type,
            "collection_level": CollectionLevel.ORG_NODE,
            "frequency": CollectionFrequency.MONTHLY,
        }
        data.update(overrides)
        return Datapoint.objects.create(**data)

    def test_all_datapoint_types_are_supported(self):
        self.assertEqual(
            {choice.value for choice in DatapointDataType},
            {
                "DECIMAL",
                "INTEGER",
                "TEXT",
                "LONG_TEXT",
                "BOOLEAN",
                "SELECT",
                "DATE",
                "TABLE",
            },
        )

    def test_select_options_only_attach_to_select_datapoints(self):
        select_dp = self.make_datapoint("ENERGY_SOURCE", DatapointDataType.SELECT)
        option = DatapointOption(
            datapoint=select_dp,
            code="GRID",
            label="Grid",
        )
        option.full_clean()

        text_dp = self.make_datapoint("ENERGY_NOTE", DatapointDataType.TEXT)
        invalid = DatapointOption(datapoint=text_dp, code="BAD", label="Bad")
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_fixed_and_dynamic_table_definitions_are_explicit(self):
        fixed = self.make_datapoint("FIXED_TABLE", DatapointDataType.TABLE)
        dynamic = self.make_datapoint(
            "DYNAMIC_TABLE",
            DatapointDataType.TABLE,
            allow_dynamic_rows=True,
            validation_metadata={"min_rows": 1},
        )

        self.assertFalse(fixed.allow_dynamic_rows)
        self.assertTrue(dynamic.allow_dynamic_rows)
        self.assertEqual(dynamic.validation_metadata, {"min_rows": 1})

    def test_table_ordering_and_uniqueness(self):
        table = self.make_datapoint("ORDERED_TABLE", DatapointDataType.TABLE)
        DatapointTableColumn.objects.create(
            datapoint=table,
            code="A",
            label="A",
            data_type=DatapointDataType.TEXT,
            display_order=1,
        )

        duplicate_column = DatapointTableColumn(
            datapoint=table,
            code="B",
            label="B",
            data_type=DatapointDataType.TEXT,
            display_order=1,
        )
        with self.assertRaises(ValidationError):
            duplicate_column.full_clean()

        DatapointTableRow.objects.create(
            datapoint=table,
            code="ROW_A",
            label="Row A",
            display_order=1,
        )
        duplicate_row = DatapointTableRow(
            datapoint=table,
            code="ROW_B",
            label="Row B",
            display_order=1,
        )
        with self.assertRaises(ValidationError):
            duplicate_row.full_clean()

    def test_unit_family_base_unit_invariants(self):
        invalid_base = Unit(
            family=self.energy_family,
            code="BAD_BASE",
            name="Bad Base",
            factor_to_base=Decimal("2"),
            is_base_unit=True,
        )
        with self.assertRaises(ValidationError):
            invalid_base.full_clean()

        invalid_factor = Unit(
            family=self.energy_family,
            code="BAD_FACTOR",
            name="Bad Factor",
            factor_to_base=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            invalid_factor.full_clean()

    def test_unit_conversion_is_deterministic_decimal_math(self):
        self.assertEqual(
            self.mwh.convert_value_to_base(Decimal("2.5")),
            Decimal("2500.0000000000"),
        )

    def test_module_registry_compatibility_and_category_module_consistency(self):
        datapoint = self.make_datapoint("ENERGY_TOTAL", DatapointDataType.DECIMAL)
        datapoint.full_clean()

        invalid = Datapoint(
            code="WATER_TOTAL",
            category=self.category,
            module=self.water_module,
            label="Water Total",
            data_type=DatapointDataType.DECIMAL,
            collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.MONTHLY,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_datapoint_and_table_column_validation_metadata_contract(self):
        dp = Datapoint(
            code="BAD_METADATA",
            category=self.category,
            module=self.energy_module,
            label="Bad Metadata",
            data_type=DatapointDataType.TEXT,
            collection_level=CollectionLevel.ORG_NODE,
            frequency=CollectionFrequency.MONTHLY,
            validation_metadata=["not", "an", "object"],
        )
        with self.assertRaises(ValidationError):
            dp.full_clean()

        table = self.make_datapoint("METADATA_TABLE", DatapointDataType.TABLE)
        column = DatapointTableColumn(
            datapoint=table,
            code="VALUE",
            label="Value",
            data_type=DatapointDataType.DECIMAL,
            validation_metadata={"min": "0"},
        )
        column.full_clean()

    def test_table_column_unit_family_default_unit_compatibility(self):
        table = self.make_datapoint("UNIT_TABLE", DatapointDataType.TABLE)
        column = DatapointTableColumn(
            datapoint=table,
            code="QUANTITY",
            label="Quantity",
            data_type=DatapointDataType.DECIMAL,
            unit_family=self.mass_family,
            default_unit=self.kwh,
        )
        with self.assertRaises(ValidationError):
            column.full_clean()

        invalid_text_column = DatapointTableColumn(
            datapoint=table,
            code="TEXT_WITH_UNIT",
            label="Text With Unit",
            data_type=DatapointDataType.TEXT,
            unit_family=self.energy_family,
        )
        with self.assertRaises(ValidationError):
            invalid_text_column.full_clean()


class DatapointSeedTests(TestCase):
    def test_seed_datapoints_is_idempotent_and_uses_registered_modules(self):
        call_command("seed_modules", verbosity=0)
        call_command("seed_datapoints", verbosity=0)

        counts = {
            "families": UnitFamily.objects.count(),
            "units": Unit.objects.count(),
            "categories": DatapointCategory.objects.count(),
            "datapoints": Datapoint.objects.count(),
            "options": DatapointOption.objects.count(),
            "columns": DatapointTableColumn.objects.count(),
            "rows": DatapointTableRow.objects.count(),
        }

        call_command("seed_datapoints", verbosity=0)

        self.assertEqual(counts["families"], UnitFamily.objects.count())
        self.assertEqual(counts["units"], Unit.objects.count())
        self.assertEqual(counts["categories"], DatapointCategory.objects.count())
        self.assertEqual(counts["datapoints"], Datapoint.objects.count())
        self.assertEqual(counts["options"], DatapointOption.objects.count())
        self.assertEqual(counts["columns"], DatapointTableColumn.objects.count())
        self.assertEqual(counts["rows"], DatapointTableRow.objects.count())

        for datapoint in Datapoint.objects.select_related("category", "module"):
            self.assertEqual(datapoint.module_id, datapoint.category.module_id)

        self.assertEqual(
            set(Datapoint.objects.values_list("data_type", flat=True)),
            {choice.value for choice in DatapointDataType},
        )

        self.assertTrue(
            Datapoint.objects.filter(
                code="WASTE_STREAMS_TABLE",
                data_type=DatapointDataType.TABLE,
                allow_dynamic_rows=True,
            ).exists()
        )

    def test_seed_upgrades_legacy_energy_kwh_base_unit(self):
        """The expanded registry moves ENERGY's canonical base to joules."""
        call_command("seed_modules", verbosity=0)
        energy = UnitFamily.objects.create(code="ENERGY", name="Energy")
        Unit.objects.create(
            family=energy,
            code="KWH",
            name="Kilowatt-hour",
            factor_to_base=Decimal("1"),
            is_base_unit=True,
        )

        call_command("seed_datapoints", verbosity=0)

        energy = UnitFamily.objects.get(code="ENERGY")
        joule = Unit.objects.get(code="J")
        kwh = Unit.objects.get(code="KWH")

        self.assertEqual(joule.family, energy)
        self.assertTrue(joule.is_base_unit)
        self.assertEqual(joule.factor_to_base, Decimal("1"))
        self.assertFalse(kwh.is_base_unit)
        self.assertEqual(kwh.factor_to_base, Decimal("3600000"))
        self.assertEqual(
            Unit.objects.filter(family=energy, is_base_unit=True).count(),
            1,
        )


class DatapointAPITests(TestCase):
    def setUp(self):
        call_command("seed_modules", verbosity=0)
        call_command("seed_datapoints", verbosity=0)
        self.client = APIClient()
        self.user = User.objects.create_user(username="catalog-user", password="pass")
        self.client.force_authenticate(self.user)

    def grant_datapoint_manage(self):
        permission = Permission.objects.create(
            code="datapoint.manage",
            name="Manage datapoint catalog",
            module_code="datapoint",
            action="MANAGE",
        )
        role = Role.objects.create(role_code="catalog_admin", role_name="Catalog Admin")
        role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role)

    def test_api_filtering_and_detail_response_shape(self):
        response = self.client.get("/api/datapoints/?data_type=SELECT")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)
        self.assertTrue(all(item["data_type"] == "SELECT" for item in response.data))

        datapoint = Datapoint.objects.get(code="EMISSIONS_TABLE")
        detail = self.client.get(f"/api/datapoints/{datapoint.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("validation_metadata", detail.data)
        self.assertIn("allow_dynamic_rows", detail.data)
        self.assertIn("table_columns", detail.data)
        self.assertIn("table_rows", detail.data)

        table_definition = self.client.get(
            f"/api/datapoints/{datapoint.id}/table-definition/"
        )
        self.assertEqual(table_definition.status_code, 200)
        self.assertEqual(
            set(table_definition.data.keys()),
            {"datapoint", "columns", "rows"},
        )
        self.assertIn("validation_metadata", table_definition.data["columns"][0])

    def test_datapoint_manage_authorization_for_administrative_writes(self):
        payload = {
            "code": "API_CATEGORY",
            "name": "API Category",
            "module": "energy",
            "description": "",
            "display_order": 99,
            "is_active": True,
        }
        response = self.client.post("/api/datapoints/categories/", payload, format="json")
        self.assertEqual(response.status_code, 403)

        self.grant_datapoint_manage()
        response = self.client.post("/api/datapoints/categories/", payload, format="json")
        self.assertEqual(response.status_code, 201)
