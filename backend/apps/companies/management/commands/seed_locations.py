import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.companies.models import Country, State, City


class Command(BaseCommand):
    help = "Seed countries, states and cities from CSV files."

    def handle(self, *args, **kwargs):
        base_path = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "locations_data"
        )

        countries_file = base_path / "countries.csv"
        states_file = base_path / "states.csv"
        cities_file = base_path / "cities.csv"

        with transaction.atomic():
            self.seed_countries(countries_file)
            self.seed_states(states_file)
            self.seed_cities(cities_file)

        self.stdout.write(
            self.style.SUCCESS(
                "Location master data imported successfully."
            )
        )

    def seed_countries(self, file_path):
        self.stdout.write("Importing countries...")

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                Country.objects.update_or_create(
                    iso_code=row["iso_code"].strip().upper(),
                    defaults={
                        "name": row["country_name"].strip(),
                        "is_active": True,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS("Countries imported.")
        )

    def seed_states(self, file_path):
        self.stdout.write("Importing states...")

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                country = Country.objects.get(
                    iso_code=row["country_iso_code"].strip().upper()
                )

                State.objects.update_or_create(
                    country=country,
                    state_code=row["state_code"].strip().upper(),
                    defaults={
                        "name": row["state_name"].strip(),
                        "is_active": True,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS("States imported.")
        )

    def seed_cities(self, file_path):
        self.stdout.write("Importing cities...")

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                state = State.objects.get(
                    country__iso_code = row["country_iso_code"].strip().upper(),
                    state_code=row["state_code"].strip().upper()
                )

                City.objects.update_or_create(
                    country=state.country,
                    state=state,
                    name=row["city_name"].strip(),
                    defaults={
                        "is_active": True,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS("Cities imported.")
        )