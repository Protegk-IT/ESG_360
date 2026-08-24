from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
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
        if not Module.objects.exists():
            raise CommandError(
                 "No modules found, Please seed the module command first"
            )


        self.seed_units()
        self.seed_datapoints()

        self.stdout.write(
            self.style.SUCCESS("M4 datapoint catalog seeded successfully.")
        )

    # ---------------------------------------------------------
    # UNIT REGISTRY
    # ---------------------------------------------------------

    def seed_units(self):
        """
        Seed the canonical M4 unit registry.

        factor_to_base means:

            quantity_in_base_unit =
                quantity * factor_to_base

        Example:
            1 KWH = 3,600,000 J
            therefore KWH.factor_to_base = 3600000

        M6 consumes these units directly for deterministic
        factor calculation. No duplicate units should be created
        in M6.
        """

        unit_families = {
            "LENGTH": "Length",
            "MASS": "Mass",
            "VOLUME": "Volume",
            "ENERGY": "Energy",
            "AREA": "Area",
            "SPEED": "Speed",
            "TIME": "Time",
            "COOLING": "Cooling",
        }

        # ---------------------------------------------------------
        # UNIT FAMILIES
        # ---------------------------------------------------------

        families = {}

        for code, name in unit_families.items():
            family, _ = UnitFamily.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                },
            )

            families[code] = family

        # ---------------------------------------------------------
        # UNIT CONVERSION DATA
        # ---------------------------------------------------------
        #
        # factor_to_base converts the unit INTO the family
        # base unit.
        #
        # Example:
        #
        # ENERGY base = J
        #
        # 1 KWH = 3,600,000 J
        # factor_to_base = 3600000
        #
        # 1 MWH = 3,600,000,000 J
        # factor_to_base = 3600000000
        #
        # ---------------------------------------------------------

        units = [
            # =====================================================
            # LENGTH
            # Base: metre
            # =====================================================

            {
                "family": "LENGTH",
                "code": "M",
                "name": "Meter",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "LENGTH",
                "code": "KM",
                "name": "Kilometer",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "CM",
                "name": "Centimeter",
                "factor_to_base": Decimal("0.01"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "MM",
                "name": "Millimeter",
                "factor_to_base": Decimal("0.001"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "MI",
                "name": "Mile",
                "factor_to_base": Decimal("1609.344"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "YD",
                "name": "Yard",
                "factor_to_base": Decimal("0.9144"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "FT",
                "name": "Foot",
                "factor_to_base": Decimal("0.3048"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "IN",
                "name": "Inch",
                "factor_to_base": Decimal("0.0254"),
                "is_base_unit": False,
            },
            {
                "family": "LENGTH",
                "code": "NMI",
                "name": "Nautical Mile",
                "factor_to_base": Decimal("1852"),
                "is_base_unit": False,
            },

            # =====================================================
            # MASS
            # Base: kilogram
            # =====================================================

            {
                "family": "MASS",
                "code": "KG",
                "name": "Kilogram",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "MASS",
                "code": "G",
                "name": "Gram",
                "factor_to_base": Decimal("0.001"),
                "is_base_unit": False,
            },
            {
                "family": "MASS",
                "code": "MG",
                "name": "Milligram",
                "factor_to_base": Decimal("0.000001"),
                "is_base_unit": False,
            },
            {
                "family": "MASS",
                "code": "TONNE",
                "name": "Tonne",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "MASS",
                "code": "LB",
                "name": "Pound",
                "factor_to_base": Decimal("0.45359237"),
                "is_base_unit": False,
            },
            {
                "family": "MASS",
                "code": "OZ",
                "name": "Ounce",
                "factor_to_base": Decimal("0.0283495231"),
                "is_base_unit": False,
            },

            # =====================================================
            # VOLUME
            # Base: litre
            # =====================================================

            {
                "family": "VOLUME",
                "code": "L",
                "name": "Liter",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "VOLUME",
                "code": "ML",
                "name": "Milliliter",
                "factor_to_base": Decimal("0.001"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "M3",
                "name": "Cubic Meter",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "GAL_US",
                "name": "Gallon (US)",
                "factor_to_base": Decimal("3.785411784"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "QT_US",
                "name": "Quart (US)",
                "factor_to_base": Decimal("0.946352946"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "PT_US",
                "name": "Pint (US)",
                "factor_to_base": Decimal("0.473176473"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "CUP_US",
                "name": "Cup (US)",
                "factor_to_base": Decimal("0.2365882365"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "FT3",
                "name": "Cubic Foot",
                "factor_to_base": Decimal("28.316846592"),
                "is_base_unit": False,
            },
            {
                "family": "VOLUME",
                "code": "GAL_UK",
                "name": "Gallon (UK)",
                "factor_to_base": Decimal("4.54609"),
                "is_base_unit": False,
            },

            # =====================================================
            # ENERGY
            # Base: joule
            # =====================================================

            {
                "family": "ENERGY",
                "code": "J",
                "name": "Joule",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "ENERGY",
                "code": "KJ",
                "name": "Kilojoule",
                "factor_to_base": Decimal("1000"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "WH",
                "name": "Watt-hour",
                "factor_to_base": Decimal("3600"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "KWH",
                "name": "Kilowatt-hour",
                "factor_to_base": Decimal("3600000"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "MWH",
                "name": "Megawatt-hour",
                "factor_to_base": Decimal("3600000000"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "GWH",
                "name": "Gigawatt-hour",
                "factor_to_base": Decimal("3600000000000"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "CAL",
                "name": "Calorie",
                "factor_to_base": Decimal("4.184"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "KCAL",
                "name": "Kilocalorie",
                "factor_to_base": Decimal("4184"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "GJ",
                "name": "Gigajoule",
                "factor_to_base": Decimal("1000000000"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "BTU",
                "name": "British Thermal Unit",
                "factor_to_base": Decimal("1055.05585262"),
                "is_base_unit": False,
            },
            {
                "family": "ENERGY",
                "code": "THERM",
                "name": "Therm",
                "factor_to_base": Decimal("105505585.262"),
                "is_base_unit": False,
            },

            # =====================================================
            # AREA
            # Base: square metre
            # =====================================================

            {
                "family": "AREA",
                "code": "M2",
                "name": "Square Meter",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "AREA",
                "code": "KM2",
                "name": "Square Kilometer",
                "factor_to_base": Decimal("1000000"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "MI2",
                "name": "Square Mile",
                "factor_to_base": Decimal("2589988.110336"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "YD2",
                "name": "Square Yard",
                "factor_to_base": Decimal("0.83612736"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "FT2",
                "name": "Square Foot",
                "factor_to_base": Decimal("0.09290304"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "IN2",
                "name": "Square Inch",
                "factor_to_base": Decimal("0.00064516"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "ACRE",
                "name": "Acre",
                "factor_to_base": Decimal("4046.8564224"),
                "is_base_unit": False,
            },
            {
                "family": "AREA",
                "code": "HECTARE",
                "name": "Hectare",
                "factor_to_base": Decimal("10000"),
                "is_base_unit": False,
            },

            # =====================================================
            # SPEED
            # Base: metre/second
            # =====================================================

            {
                "family": "SPEED",
                "code": "MPS",
                "name": "Meter per Second",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "SPEED",
                "code": "KMPH",
                "name": "Kilometer per Hour",
                "factor_to_base": Decimal("0.2777777778"),
                "is_base_unit": False,
            },
            {
                "family": "SPEED",
                "code": "MPH",
                "name": "Mile per Hour",
                "factor_to_base": Decimal("0.44704"),
                "is_base_unit": False,
            },
            {
                "family": "SPEED",
                "code": "KNOT",
                "name": "Knot",
                "factor_to_base": Decimal("0.5144444444"),
                "is_base_unit": False,
            },
            {
                "family": "SPEED",
                "code": "FTPS",
                "name": "Foot per Second",
                "factor_to_base": Decimal("0.3048"),
                "is_base_unit": False,
            },

            # =====================================================
            # TIME
            # Base: second
            # =====================================================

            {
                "family": "TIME",
                "code": "S",
                "name": "Second",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
            {
                "family": "TIME",
                "code": "MIN",
                "name": "Minute",
                "factor_to_base": Decimal("60"),
                "is_base_unit": False,
            },
            {
                "family": "TIME",
                "code": "H",
                "name": "Hour",
                "factor_to_base": Decimal("3600"),
                "is_base_unit": False,
            },
            {
                "family": "TIME",
                "code": "DAY",
                "name": "Day",
                "factor_to_base": Decimal("86400"),
                "is_base_unit": False,
            },
            {
                "family": "TIME",
                "code": "WEEK",
                "name": "Week",
                "factor_to_base": Decimal("604800"),
                "is_base_unit": False,
            },
            {
                "family": "TIME",
                "code": "MS",
                "name": "Millisecond",
                "factor_to_base": Decimal("0.001"),
                "is_base_unit": False,
            },
            {
                "family": "TIME",
                "code": "US",
                "name": "Microsecond",
                "factor_to_base": Decimal("0.000001"),
                "is_base_unit": False,
            },

            # =====================================================
            # COOLING
            #
            # Kept as a separate family because it is a domain
            # quantity and is not linearly interchangeable with
            # energy without additional domain rules.
            # =====================================================

            {
                "family": "COOLING",
                "code": "TRH",
                "name": "Ton of Refrigeration Hour",
                "factor_to_base": Decimal("1"),
                "is_base_unit": True,
            },
        ]

        # ---------------------------------------------------------
        # CREATE / UPDATE UNITS
        # ---------------------------------------------------------

        # A family has a database-enforced single-base-unit invariant.
        # Earlier M4 installations used KWH as the ENERGY base unit;
        # the expanded registry correctly uses J instead.  Demote any
        # previous base before creating/updating the canonical base so an
        # in-place seed upgrade never violates that constraint.
        canonical_base_codes = {
            unit_data["family"]: unit_data["code"]
            for unit_data in units
            if unit_data["is_base_unit"]
        }
        for family_code, base_code in canonical_base_codes.items():
            Unit.objects.filter(
                family=families[family_code],
                is_base_unit=True,
            ).exclude(code=base_code).update(is_base_unit=False)

        for unit_data in units:
            family = families[unit_data["family"]]

            Unit.objects.update_or_create(
                code=unit_data["code"],
                defaults={
                    "family": family,
                    "name": unit_data["name"],
                    "factor_to_base": unit_data["factor_to_base"],
                    "is_base_unit": unit_data["is_base_unit"],
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(families)} unit families "
                f"and {len(units)} units."
            )
        )

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
                "validation_metadata": {"min": "0", "decimal_places": 4},
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
                "validation_metadata": {},
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
                "validation_metadata": {"max_length": 2000},
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
                "validation_metadata": {"min": "0", "decimal_places": 4},
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
                "validation_metadata": {},
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
                "validation_metadata": {"min": "0"},
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
                "validation_metadata": {},
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
                "validation_metadata": {"max_length": 255},
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
                "allow_dynamic_rows": False,
                "validation_metadata": {},
            },
            {
                "code": "WASTE_STREAMS_TABLE",
                "category": "WASTE",
                "module": "waste",
                "label": "Waste streams",
                "data_type": DatapointDataType.TABLE,
                "unit_family": None,
                "default_unit": None,
                "collection_level": CollectionLevel.FACILITY,
                "frequency": CollectionFrequency.MONTHLY,
                "allow_dynamic_rows": True,
                "validation_metadata": {"min_rows": 1},
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
                    "allow_dynamic_rows": data.get("allow_dynamic_rows", False),
                    "validation_metadata": data.get("validation_metadata", {}),
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
                "validation_metadata": {"max_length": 255},
                "display_order": 1,
            },
            {
                "code": "QUANTITY",
                "label": "Emission Quantity",
                "data_type": DatapointDataType.DECIMAL,
                "unit_family": "MASS",
                "default_unit": "KG",
                "is_required": True,
                "validation_metadata": {"min": "0", "decimal_places": 4},
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
                    "validation_metadata": column["validation_metadata"],
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

        dynamic_table = datapoint_objects["WASTE_STREAMS_TABLE"]
        DatapointTableColumn.objects.update_or_create(
            datapoint=dynamic_table,
            code="WASTE_STREAM",
            defaults={
                "label": "Waste Stream",
                "data_type": DatapointDataType.TEXT,
                "unit_family": None,
                "default_unit": None,
                "is_required": True,
                "validation_metadata": {"max_length": 255},
                "display_order": 1,
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
