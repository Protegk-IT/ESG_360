import { useEffect, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import api from "../../services/api";

interface Organization {
  id: string;
  name: string;
}

interface Department {
  id: string;
  organization: string;
  organization_name?: string;
  name: string;
  department_code: string;
  parent_department: string | null;
  parent_department_name?: string;
  is_active: boolean;
}

interface DepartmentFormState {
  organization: string;
  name: string;
  department_code: string;
  parent_department: string;
}

const initialFormState: DepartmentFormState = {
  organization: "",
  name: "",
  department_code: "",
  parent_department: "",
};

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [formData, setFormData] = useState<DepartmentFormState>(initialFormState);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const loadPageData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [departmentsResponse, organizationsResponse] = await Promise.all([
        api.get<Department[]>("/organizations/departments/"),
        api.get<Organization[]>("/organizations/organizations/"),
      ]);

      setDepartments(departmentsResponse.data);
      setOrganizations(organizationsResponse.data);
    } catch {
      setError("Unable to load department data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadPageData();
  }, []);

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = event.target;
    setFormData((currentData) => ({ ...currentData, [name]: value }));
  };

  const validateForm = () => {
    if (!formData.organization) return "Please select an organization.";
    if (!formData.name.trim()) return "Department name is required.";
    if (!formData.department_code.trim()) return "Department code is required.";
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
      await api.post("/organizations/departments/", {
        organization: formData.organization,
        name: formData.name,
        department_code: formData.department_code,
        parent_department: formData.parent_department || null,
      });

      setFormData(initialFormState);
      setSuccessMessage("Department created successfully.");
      await loadPageData();
    } catch {
      setError("Unable to save the department. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell
      title="Departments"
      description="Add department details and review all departments."
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Add Department</h2>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the department details below.
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
              <label className="mb-1 block text-sm font-medium text-gray-700">Department Name</label>
              <input
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Department Code</label>
              <input
                name="department_code"
                value={formData.department_code}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Parent Department</label>
              <select
                name="parent_department"
                value={formData.parent_department}
                onChange={handleInputChange}
                className="w-full rounded-md border px-3 py-2"
              >
                <option value="">Select parent department</option>
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <button
                type="submit"
                disabled={isSaving}
                className="rounded-md bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                {isSaving ? "Saving..." : "Save Department"}
              </button>
            </div>
          </form>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Department List</h2>
          <p className="mt-1 text-sm text-gray-600">
            Review the departments available in ESG360.
          </p>

          {isLoading ? (
            <p className="mt-4 text-sm text-gray-600">Loading departments...</p>
          ) : departments.length === 0 ? (
            <p className="mt-4 text-sm text-gray-600">No departments available yet.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full border border-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Code</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Name</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Organization</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Parent</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((department) => (
                    <tr key={department.id} className="hover:bg-gray-50">
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{department.department_code}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{department.name}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{department.organization_name ?? "Unknown"}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{department.parent_department_name ?? "None"}</td>
                      <td className="border-b px-4 py-3 text-sm text-gray-700">{department.is_active ? "Active" : "Inactive"}</td>
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
