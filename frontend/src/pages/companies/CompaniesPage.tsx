import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import api from "../../services/api";

interface Company {
  id: string;
  company_code: string;
  company_name: string;
  gst_number: string | null;
  cin_number: string | null;
  date_of_incorporation: string | null;
  about_company: string | null;
  billing_address: string | null;
  billing_zip_code: string | null;
  billing_country: string | null;
  billing_state: string | null;
  billing_city: string | null;
  contact_person: string;
  email: string;
  mobile_number: string;
  website: string | null;
  listed_company: boolean;
  is_active: boolean;
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

interface CompanyFormState {
  company_code: string;
  company_name: string;
  password: string;
  gst_number: string;
  cin_number: string;
  date_of_incorporation: string;
  about_company: string;
  billing_address: string;
  billing_zip_code: string;
  billing_country: string;
  billing_state: string;
  billing_city: string;
  contact_person: string;
  email: string;
  mobile_number: string;
  website: string;
  listed_company: boolean;
  is_active: boolean;
}

const initialFormState: CompanyFormState = {
  company_code: "",
  company_name: "",
  password: "",
  gst_number: "",
  cin_number: "",
  date_of_incorporation: "",
  about_company: "",
  billing_address: "",
  billing_zip_code: "",
  billing_country: "",
  billing_state: "",
  billing_city: "",
  contact_person: "",
  email: "",
  mobile_number: "",
  website: "",
  listed_company: false,
  is_active: true,
};

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [formData, setFormData] = useState<CompanyFormState>(initialFormState);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const getErrorMessage = (unknownError: unknown, fallback: string) => {
    if (axios.isAxiosError(unknownError)) {
      return (
        unknownError.response?.data?.message ??
        unknownError.response?.data?.detail ??
        unknownError.message ??
        fallback
      );
    }

    return fallback;
  };

  const loadPageData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [companiesResponse, countriesResponse, statesResponse, citiesResponse] =
        await Promise.all([
          api.get<Company[]>("/companies/companies/"),
          api.get<Country[]>("/companies/countries/"),
          api.get<State[]>("/companies/states/"),
          api.get<City[]>("/companies/cities/"),
        ]);

      setCompanies(companiesResponse.data);
      setCountries(countriesResponse.data);
      setStates(statesResponse.data);
      setCities(citiesResponse.data);
    } catch (unknownError) {
      setError(getErrorMessage(unknownError, "Unable to load company data."));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadPageData();
  }, []);

  const filteredStates = useMemo(
    () => states.filter((state) => state.country === formData.billing_country),
    [states, formData.billing_country],
  );

  const filteredCities = useMemo(
    () => cities.filter((city) => city.state === formData.billing_state),
    [cities, formData.billing_state],
  );

  const countryMap = useMemo(
    () =>
      countries.reduce<Record<string, string>>((accumulator, country) => {
        accumulator[country.id] = country.name;
        return accumulator;
      }, {}),
    [countries],
  );

  const stateMap = useMemo(
    () =>
      states.reduce<Record<string, string>>((accumulator, state) => {
        accumulator[state.id] = state.name;
        return accumulator;
      }, {}),
    [states],
  );

  const cityMap = useMemo(
    () =>
      cities.reduce<Record<string, string>>((accumulator, city) => {
        accumulator[city.id] = city.name;
        return accumulator;
      }, {}),
    [cities],
  );

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const target = event.target as HTMLInputElement;
    const { name, value, type } = target;

    setFormData((currentData) => {
      if (name === "billing_country") {
        return {
          ...currentData,
          billing_country: value,
          billing_state: "",
          billing_city: "",
        };
      }

      if (name === "billing_state") {
        return {
          ...currentData,
          billing_state: value,
          billing_city: "",
        };
      }

      return {
        ...currentData,
        [name]: type === "checkbox" ? target.checked : value,
      };
    });
  };

  const validateForm = () => {
    if (!formData.company_code.trim()) return "Company code is required.";
    if (!formData.company_name.trim()) return "Company name is required.";
    if (!formData.password.trim()) return "Password is required.";
    if (!formData.contact_person.trim()) return "Contact person is required.";
    if (!formData.email.trim()) return "Email is required.";
    if (!formData.mobile_number.trim()) return "Mobile number is required.";
    if (!formData.billing_country) return "Please select a country.";
    if (!formData.billing_state) return "Please select a state.";
    if (!formData.billing_city) return "Please select a city.";
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
      await api.post("/companies/companies/", {
        company_code: formData.company_code,
        company_name: formData.company_name,
        password: formData.password,
        gst_number: formData.gst_number || null,
        cin_number: formData.cin_number || null,
        date_of_incorporation: formData.date_of_incorporation || null,
        about_company: formData.about_company || null,
        billing_address: formData.billing_address || null,
        billing_zip_code: formData.billing_zip_code || null,
        billing_country: formData.billing_country || null,
        billing_state: formData.billing_state || null,
        billing_city: formData.billing_city || null,
        contact_person: formData.contact_person,
        email: formData.email,
        mobile_number: formData.mobile_number,
        website: formData.website || null,
        listed_company: formData.listed_company,
        is_active: formData.is_active,
      });

      setFormData(initialFormState);
      setSuccessMessage("Company created successfully.");
      await loadPageData();
    } catch (unknownError) {
      setError(getErrorMessage(unknownError, "Unable to save the company."));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell
      title="Companies"
      description="Add company details and review all created companies."
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Add Company</h2>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the company details below.
          </p>

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
          {successMessage && <p className="mt-4 text-sm text-green-600">{successMessage}</p>}

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Company Code</label>
              <input
                name="company_code"
                value={formData.company_code}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Company Name</label>
              <input
                name="company_name"
                value={formData.company_name}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
              <input
                name="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Contact Person</label>
              <input
                name="contact_person"
                value={formData.contact_person}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
              <input
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Mobile Number</label>
              <input
                name="mobile_number"
                value={formData.mobile_number}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Website</label>
              <input
                name="website"
                value={formData.website}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">GST Number</label>
              <input
                name="gst_number"
                value={formData.gst_number}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">CIN Number</label>
              <input
                name="cin_number"
                value={formData.cin_number}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Date of Incorporation</label>
              <input
                name="date_of_incorporation"
                type="date"
                value={formData.date_of_incorporation}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Country</label>
              <select
                name="billing_country"
                value={formData.billing_country}
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
                name="billing_state"
                value={formData.billing_state}
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
                name="billing_city"
                value={formData.billing_city}
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

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Billing Zip Code</label>
              <input
                name="billing_zip_code"
                value={formData.billing_zip_code}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <label className="mb-1 block text-sm font-medium text-gray-700">Billing Address</label>
              <textarea
                name="billing_address"
                value={formData.billing_address}
                onChange={handleInputChange}
                rows={3}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <label className="mb-1 block text-sm font-medium text-gray-700">About Company</label>
              <textarea
                name="about_company"
                value={formData.about_company}
                onChange={handleInputChange}
                rows={3}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <input
                id="listed_company"
                name="listed_company"
                type="checkbox"
                checked={formData.listed_company}
                onChange={handleInputChange}
                className="h-4 w-4 rounded border-gray-300"
              />
              <label htmlFor="listed_company" className="text-sm font-medium text-gray-700">
                Listed Company
              </label>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <input
                id="is_active"
                name="is_active"
                type="checkbox"
                checked={formData.is_active}
                onChange={handleInputChange}
                className="h-4 w-4 rounded border-gray-300"
              />
              <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                Active
              </label>
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-md bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                {isSaving ? "Saving..." : "Save Company"}
              </button>
            </div>
          </form>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Company List</h2>
          <p className="mt-1 text-sm text-gray-600">
            Review the companies available in ESG360.
          </p>

          {isLoading ? (
            <p className="mt-4 text-sm text-gray-600">Loading companies...</p>
          ) : companies.length === 0 ? (
            <p className="mt-4 text-sm text-gray-600">No companies available yet.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full border border-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Code</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Name</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Email</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Contact</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Country</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">State</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">City</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company) => (
                    <tr key={company.id} className="hover:bg-gray-50">
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{company.company_code}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{company.company_name}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{company.email}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{company.contact_person}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">
                        {company.billing_country ? countryMap[company.billing_country] ?? "Unknown" : "Not set"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">
                        {company.billing_state ? stateMap[company.billing_state] ?? "Unknown" : "Not set"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">
                        {company.billing_city ? cityMap[company.billing_city] ?? "Unknown" : "Not set"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">
                        {company.is_active ? "Active" : "Inactive"}
                      </td>
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