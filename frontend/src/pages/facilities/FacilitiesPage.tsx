import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import api from "../../services/api";

interface Organization {
  id: string;
  name: string;
}

interface Department {
  id: string;
  organization: string;
  name: string;
}

interface Country {
  id: string;
  name: string;
}

interface State {
  id: string;
  country: string;
  name: string;
}

interface City {
  id: string;
  state: string;
  name: string;
}

interface Facility {
  id: string;
  organization: string;
  organization_name?: string;
  department: string | null;
  department_name?: string;
  name: string;
  facility_code: string;
  facility_type: string;
  country: string | null;
  state: string | null;
  city: string | null;
  address: string;
  is_active: boolean;
}

interface FacilityFormState {
  organization: string;
  department: string;
  name: string;
  facility_code: string;
  facility_type: string;
  country: string;
  state: string;
  city: string;
  address: string;
}

const initialFormState: FacilityFormState = {
  organization: "",
  department: "",
  name: "",
  facility_code: "",
  facility_type: "",
  country: "",
  state: "",
  city: "",
  address: "",
};

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [formData, setFormData] = useState<FacilityFormState>(initialFormState);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const loadPageData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [
        facilitiesResponse,
        organizationsResponse,
        departmentsResponse,
        countriesResponse,
        statesResponse,
        citiesResponse,
      ] = await Promise.all([
        api.get<Facility[]>("/organizations/facilities/"),
        api.get<Organization[]>("/organizations/organizations/"),
        api.get<Department[]>("/organizations/departments/"),
        api.get<Country[]>("/companies/countries/"),
        api.get<State[]>("/companies/states/"),
        api.get<City[]>("/companies/cities/"),
      ]);

      setFacilities(facilitiesResponse.data);
      setOrganizations(organizationsResponse.data);
      setDepartments(departmentsResponse.data);
      setCountries(countriesResponse.data);
      setStates(statesResponse.data);
      setCities(citiesResponse.data);
    } catch {
      setError("Unable to load facility data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadPageData();
  }, []);

  const filteredDepartments = useMemo(
    () => departments.filter((department) => department.organization === formData.organization),
    [departments, formData.organization],
  );

  const filteredStates = useMemo(
    () => states.filter((state) => state.country === formData.country),
    [states, formData.country],
  );

  const filteredCities = useMemo(
    () => cities.filter((city) => city.state === formData.state),
    [cities, formData.state],
  );

  const countryMap = useMemo(
    () =>
      countries.reduce<Record<string, string>>((accumulator, country) => {
        accumulator[country.id] = country.name;
        return accumulator;
      }, {}),
    [countries],
  );

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    const { name, value } = event.target;

    setFormData((currentData) => {
      if (name === "organization") {
        return {
          ...currentData,
          organization: value,
          department: "",
        };
      }

      if (name === "country") {
        return {
          ...currentData,
          country: value,
          state: "",
          city: "",
        };
      }

      if (name === "state") {
        return {
          ...currentData,
          state: value,
          city: "",
        };
      }

      return {
        ...currentData,
        [name]: value,
      };
    });
  };

  const validateForm = () => {
    if (!formData.organization) return "Please select an organization.";
    if (!formData.name.trim()) return "Facility name is required.";
    if (!formData.facility_code.trim()) return "Facility code is required.";
    if (!formData.country) return "Please select a country.";
    if (!formData.state) return "Please select a state.";
    if (!formData.city) return "Please select a city.";
    if (!formData.address.trim()) return "Address is required.";
    return "";
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSuccessMessage("");

    const validationMessage = validateForm();
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    setIsSaving(true);
    setError("");

    try {
      await api.post("/organizations/facilities/", {
        organization: formData.organization,
        department: formData.department || null,
        name: formData.name,
        facility_code: formData.facility_code,
        facility_type: formData.facility_type,
        country: formData.country,
        state: formData.state,
        city: formData.city,
        address: formData.address,
      });

      setFormData(initialFormState);
      setSuccessMessage("Facility created successfully.");
      await loadPageData();
    } catch {
      setError("Unable to save the facility. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell
      title="Facilities"
      description="Add facility details and review all facilities."
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Add Facility</h2>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the facility details below.
          </p>

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
          {successMessage && <p className="mt-4 text-sm text-green-600">{successMessage}</p>}

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Organization</label>
              <select
                name="organization"
                value={formData.organization}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select organization</option>
                {organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Department</label>
              <select
                name="department"
                value={formData.department}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select department</option>
                {filteredDepartments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Facility Name</label>
              <input
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Facility Code</label>
              <input
                name="facility_code"
                value={formData.facility_code}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Facility Type</label>
              <input
                name="facility_type"
                value={formData.facility_type}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Country</label>
              <select
                name="country"
                value={formData.country}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select country</option>
                {countries.map((country) => (
                  <option key={country.id} value={country.id}>
                    {country.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">State</label>
              <select
                name="state"
                value={formData.state}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select state</option>
                {filteredStates.map((state) => (
                  <option key={state.id} value={state.id}>
                    {state.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">City</label>
              <select
                name="city"
                value={formData.city}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select city</option>
                {filteredCities.map((city) => (
                  <option key={city.id} value={city.id}>
                    {city.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <label className="mb-1 block text-sm font-medium text-gray-700">Address</label>
              <textarea
                name="address"
                value={formData.address}
                onChange={handleInputChange}
                rows={3}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-md bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                {isSaving ? "Saving..." : "Save Facility"}
              </button>
            </div>
          </form>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Facility List</h2>
          <p className="mt-1 text-sm text-gray-600">
            Review the facilities available in ESG360.
          </p>

          {isLoading ? (
            <p className="mt-4 text-sm text-gray-600">Loading facilities...</p>
          ) : facilities.length === 0 ? (
            <p className="mt-4 text-sm text-gray-600">No facilities available yet.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full border border-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Code</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Name</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Organization</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Department</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Country</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {facilities.map((facility) => (
                    <tr key={facility.id} className="hover:bg-gray-50">
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{facility.facility_code}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{facility.name}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{facility.organization_name ?? "Unknown"}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{facility.department_name ?? "None"}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">
                        {facility.country ? countryMap[facility.country] ?? "Unknown" : "Not set"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{facility.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
