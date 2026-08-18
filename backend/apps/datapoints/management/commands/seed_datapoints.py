from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.modules.models import Module
from apps.datapoints.models import (
    UnitFamily,
    Unit,
    DatapointCategory,
    Datapoint,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
    DatapointDataType,
    CollectionLevel,
    CollectionFrequency,
)


class Command(BaseCommand):
    help = "Seed M4 datapoint catalog and unit registry."

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write("Seeding M4 datapoint catalog...")

        self.seed_units()
        self.seed_datapoints()

        self.stdout.write(
            self.style.SUCCESS("M4 datapoint catalog seeded successfully.")
        )

    # ---------------------------------------------------------
    # UNIT REGISTRY
    # ---------------------------------------------------------

    def seed_units(self):

        unit_families = {
            "ENERGY": "Energy",
            "VOLUME": "Volume",
            "MASS": "Mass",
        }

        families = {}

        for code, name in unit_families.items():
            family, _ = UnitFamily.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                },
            )
            families[code] = family

        units = [
            {
                "family": "ENERGY",
                "code": "KWH",
                "name": "Kilowatt-hour",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "ENERGY",
                "code": "MWH",
                "name": "Megawatt-hour",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "L",
                "name": "Litre",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "VOLUME",
                "code": "M3",
                "name": "Cubic metre",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "MASS",
                "code": "KG",
                "name": "Kilogram",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "MASS",
                "code": "TONNE",
                "name": "Tonne",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
        ]

        for data in units:
            family = families[data.pop("family")]

            Unit.objects.update_or_create(
                code=data["code"],
                defaults={
                    "family": family,
                    **data,
                },
            )

        self.stdout.write("  Units seeded.")

    # ---------------------------------------------------------
    # DATAPOINT CATALOG
    # ---------------------------------------------------------

    def seed_datapoints(self):

        categories = {}

        category_data = [
            {
                "code": "ENERGY_CONSUMPTION",
                "name": "Energy Consumption",
                "module": "energy",
            },
            {
                "code": "EMISSIONS",
                "name": "Emissions",
                "module": "emissions",
            },
            {
                "code": "WATER_CONSUMPTION",
                "name": "Water Consumption",
                "module": "water",
            },
            {
                "code": "WASTE",
                "name": "Waste",
                "module": "waste",
            },
        ]

        for data in category_data:
            module = Module.objects.get(code=data["module"])

            category, _ = DatapointCategory.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "module": module,
                    "description": "",
                    "display_order": 0,
                    "is_active": True,
                },
            )

            categories[data["code"]] = category

        # -----------------------------------------------------
        # NORMAL DATAPOINTS
        # -----------------------------------------------------

        datapoints = [
            {
                "code": "ENERGY_TOTAL_CONSUMPTION",
                "category": "ENERGY_CONSUMPTION",
                "module": "energy",
                "label": "Total energy consumption",
                "data_type": DatapointDataType.DECIMAL,
                "unit_family": "ENERGY",
                "default_unit": "KWH",
                "collection_level": CollectionLevel.ORG_NODE,
                "frequency": CollectionFrequency.MONTHLY,
            },
            {
                "code": "ENERGY_SOURCE_TYPE",
                "category": "ENERGY_CONSUMPTION",
                "module": "energy",
                "label": "Primary energy source",
                "data_type": DatapointDataType.SELECT,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.ORG_NODE,
                "frequency": CollectionFrequency.ANNUAL,
            },
            {
                "code": "ENERGY_DESCRIPTION",
                "category": "ENERGY_CONSUMPTION",
                "module": "energy",
                "label": "Energy consumption description",
                "data_type": DatapointDataType.LONG_TEXT,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.ORG_NODE,
                "frequency": CollectionFrequency.ANNUAL,
            },
            {
                "code": "WATER_TOTAL_CONSUMPTION",
                "category": "WATER_CONSUMPTION",
                "module": "water",
                "label": "Total water consumption",
                "data_type": DatapointDataType.DECIMAL,
                "unit_family": "VOLUME",
                "default_unit": "M3",
                "collection_level": CollectionLevel.FACILITY,
                "frequency": CollectionFrequency.MONTHLY,
            },
            {
                "code": "WATER_REUSED",
                "category": "WATER_CONSUMPTION",
                "module": "water",
                "label": "Water reused",
                "data_type": DatapointDataType.BOOLEAN,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.FACILITY,
                "frequency": CollectionFrequency.ANNUAL,
            },
            {
                "code": "WASTE_GENERATED",
                "category": "WASTE",
                "module": "waste",
                "label": "Total waste generated",
                "data_type": DatapointDataType.INTEGER,
                "unit_family": "MASS",
                "default_unit": "KG",
                "collection_level": CollectionLevel.FACILITY,
                "frequency": CollectionFrequency.MONTHLY,
            },
            {
                "code": "EMISSIONS_REPORTING_DATE",
                "category": "EMISSIONS",
                "module": "emissions",
                "label": "Emissions reporting date",
                "data_type": DatapointDataType.DATE,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.COMPANY,
                "frequency": CollectionFrequency.ANNUAL,
            },
            {
                "code": "EMISSIONS_REFERENCE",
                "category": "EMISSIONS",
                "module": "emissions",
                "label": "Emissions reference",
                "data_type": DatapointDataType.TEXT,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.COMPANY,
                "frequency": CollectionFrequency.ANNUAL,
            },
            {
                "code": "EMISSIONS_TABLE",
                "category": "EMISSIONS",
                "module": "emissions",
                "label": "Emissions by source",
                "data_type": DatapointDataType.TABLE,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.ORG_NODE,
                "frequency": CollectionFrequency.ANNUAL,
            },
        ]

        datapoint_objects = {}

        for index, data in enumerate(datapoints):

            category = categories[data["category"]]
            module = Module.objects.get(code=data["module"])

            unit_family = None
            default_unit = None

            if data["unit_family"]:
                unit_family = UnitFamily.objects.get(
                    code=data["unit_family"]
                )

            if data["default_unit"]:
                default_unit = Unit.objects.get(
                    code=data["default_unit"]
                )

            datapoint, _ = Datapoint.objects.update_or_create(
                code=data["code"],
                defaults={
                    "category": category,
                    "module": module,
                    "label": data["label"],
                    "description": "",
                    "data_type": data["data_type"],
                    "unit_family": unit_family,
                    "default_unit": default_unit,
                    "collection_level": data["collection_level"],
                    "frequency": data["frequency"],
                    "is_required": False,
                    "display_order": index,
                    "is_active": True,
                },
            )

            datapoint_objects[data["code"]] = datapoint

        # -----------------------------------------------------
        # SELECT OPTIONS
        # -----------------------------------------------------

        self.seed_options(
            datapoint_objects["ENERGY_SOURCE_TYPE"],
            [
                ("ELECTRICITY", "Electricity"),
                ("NATURAL_GAS", "Natural Gas"),
                ("DIESEL", "Diesel"),
                ("RENEWABLE", "Renewable Energy"),
            ],
        )

        # -----------------------------------------------------
        # TABLE DEFINITION
        # -----------------------------------------------------

        table = datapoint_objects["EMISSIONS_TABLE"]

        columns = [
            {
                "code": "SOURCE",
                "label": "Emission Source",
                "data_type": DatapointDataType.TEXT,
                "unit_family": None,
                "default_unit": None,
                "is_required": True,
                "display_order": 1,
            },
            {
                "code": "QUANTITY",
                "label": "Emission Quantity",
                "data_type": DatapointDataType.DECIMAL,
                "unit_family": "MASS",
                "default_unit": "KG",
                "is_required": True,
                "display_order": 2,
            },
        ]

        for column in columns:

            unit_family = None
            default_unit = None

            if column["unit_family"]:
                unit_family = UnitFamily.objects.get(
                    code=column["unit_family"]
                )

            if column["default_unit"]:
                default_unit = Unit.objects.get(
                    code=column["default_unit"]
                )

            DatapointTableColumn.objects.update_or_create(
                datapoint=table,
                code=column["code"],
                defaults={
                    "label": column["label"],
                    "data_type": column["data_type"],
                    "unit_family": unit_family,
                    "default_unit": default_unit,
                    "is_required": column["is_required"],
                    "display_order": column["display_order"],
                },
            )

        # Fixed-row example
        DatapointTableRow.objects.update_or_create(
            datapoint=table,
            code="SCOPE_1",
            defaults={
                "label": "Scope 1",
                "display_order": 1,
                
            },
        )

        DatapointTableRow.objects.update_or_create(
            datapoint=table,
            code="SCOPE_2",
            defaults={
                "label": "Scope 2",
                "display_order": 2,
                
            },
        )

        self.stdout.write("  Datapoints seeded.")

    # ---------------------------------------------------------
    # OPTIONS
    # ---------------------------------------------------------

    def seed_options(self, datapoint, options):

        for index, (code, label) in enumerate(options):

            DatapointOption.objects.update_or_create(
                datapoint=datapoint,
                code=code,
                defaults={
                    "label": label,
                    "display_order": index,
                    "is_active": True,
                },
            )