from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import City, Company, Country, Department, State
from .serializers import CompanySerializer, DepartmentSerializer


def make_company(code):
    return Company.objects.create(
        company_name=f"{code} Company",
        company_code=code,
        contact_person="Owner",
        email=f"{code.lower()}@example.com",
        mobile_number="1234567890",
    )


class DepartmentValidationTests(TestCase):
    def test_parent_must_belong_to_same_company(self):
        parent = Department.objects.create(
            company=make_company("ONE"), name="Parent", code="PARENT"
        )

        with self.assertRaises(ValidationError):
            Department.objects.create(
                company=make_company("TWO"),
                parent_department=parent,
                name="Child",
                code="CHILD",
            )

    def test_serializer_reports_cross_company_parent_as_validation_error(self):
        parent = Department.objects.create(
            company=make_company("ONE"), name="Parent", code="PARENT"
        )
        serializer = DepartmentSerializer(data={
            "company": str(make_company("TWO").pk),
            "parent_department": str(parent.pk),
            "name": "Child",
            "code": "CHILD",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("parent_department", serializer.errors)


class CompanySerializerValidationTests(TestCase):
    def setUp(self):
        self.country_one = Country.objects.create(name="India", iso_code="IN")
        self.country_two = Country.objects.create(name="Japan", iso_code="JP")
        self.state_one = State.objects.create(
            country=self.country_one, name="Maharashtra", state_code="MH"
        )
        self.state_two = State.objects.create(
            country=self.country_two, name="Tokyo", state_code="TK"
        )
        self.city_one = City.objects.create(
            country=self.country_one, state=self.state_one, name="Pune"
        )
        self.company = Company.objects.create(
            company_name="One", company_code="ONE", contact_person="Owner",
            email="owner@example.com", mobile_number="1234567890",
            country=self.country_one, state=self.state_one, city=self.city_one,
        )

    def test_partial_update_validates_without_mutating_instance_on_failure(self):
        serializer = CompanySerializer(
            self.company, data={"state": str(self.state_two.pk)}, partial=True
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("city", serializer.errors)
        self.assertEqual(self.company.state_id, self.state_one.id)

    def test_full_and_partial_valid_updates_validate_and_save(self):
        partial = CompanySerializer(
            self.company, data={"company_name": "Renamed"}, partial=True
        )
        self.assertTrue(partial.is_valid(), partial.errors)
        partial.save()
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Renamed")

        data = CompanySerializer(self.company).data
        data.update({"company_name": "Full Update"})
        full = CompanySerializer(self.company, data=data)
        self.assertTrue(full.is_valid(), full.errors)
        full.save()
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Full Update")

    def test_serializer_exposes_location_labels_with_writable_ids(self):
        data = CompanySerializer(self.company).data
        self.assertEqual(str(data["country"]), str(self.country_one.id))
        self.assertEqual(data["country_name"], "India")
        self.assertEqual(data["state_name"], "Maharashtra")
        self.assertEqual(data["city_name"], "Pune")
