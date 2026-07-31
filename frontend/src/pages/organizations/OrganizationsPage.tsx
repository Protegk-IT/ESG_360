import axios from "axios";
import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import AppShell from "../../components/layout/AppShell";
import api from "../../services/api";
import type { OrgNode } from "../../types/organization";

interface Company {
  id: string;
  company_name: string;
}

interface OrgNodeFormState {
  company: string;
  parent: string;
  node_type: string;
  name: string;
  node_code: string;
  description: string;
  ownership_percentage: string;
  operational_control: boolean;
  financial_control: boolean;
  is_active: boolean;
}

type ApiValidationError = Record<string, string[] | string>;

const nodeTypes = [
  { value: "LEGAL_ENTITY", label: "Legal Entity" },
  { value: "BUSINESS_UNIT", label: "Business Unit" },
  { value: "DIVISION", label: "Division" },
  { value: "REGION", label: "Region" },
  { value: "FACILITY", label: "Facility" },
];

const initialFormState: OrgNodeFormState = {
  company: "",
  parent: "",
  node_type: "LEGAL_ENTITY",
  name: "",
  node_code: "",
  description: "",
  ownership_percentage: "",
  operational_control: true,
  financial_control: true,
  is_active: true,
};

export default function OrganizationsPage() {
  const [orgNodes, setOrgNodes] = useState<OrgNode[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [formData, setFormData] = useState<OrgNodeFormState>(initialFormState);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const loadPageData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [nodesResponse, companiesResponse] = await Promise.all([
        api.get<OrgNode[]>("/organizations/org-nodes/"),
        api.get<Company[]>("/companies/companies/"),
      ]);

      setOrgNodes(nodesResponse.data);
      setCompanies(companiesResponse.data);
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Unable to load OrgNode data. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadPageData();
  }, []);

  const companyNodes = useMemo(
    () => orgNodes.filter((node) => node.company === formData.company && node.id !== editingId),
    [editingId, formData.company, orgNodes],
  );

  const treeNodes = useMemo(() => buildOrgNodeTree(orgNodes), [orgNodes]);

  const handleInputChange = (
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = event.target;

    setFormData((currentData) => {
      if (event.target instanceof HTMLInputElement && event.target.type === "checkbox") {
        return {
          ...currentData,
          [name]: event.target.checked,
        };
      }

      if (name === "company") {
        return {
          ...currentData,
          company: value,
          parent: "",
        };
      }

      return {
        ...currentData,
        [name]: value,
      };
    });
  };

  const validateForm = () => {
    if (!formData.company) return "Please select a company.";
    if (!formData.node_type) return "Please select a node type.";
    if (!formData.name.trim()) return "Name is required.";
    if (formData.ownership_percentage) {
      const ownership = Number(formData.ownership_percentage);
      if (Number.isNaN(ownership) || ownership < 0 || ownership > 100) {
        return "Ownership percentage must be between 0 and 100.";
      }
    }
    return "";
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
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
      const payload = buildPayload(formData);

      if (editingId) {
        await api.put(`/organizations/org-nodes/${editingId}/`, payload);
        setSuccessMessage("OrgNode updated successfully.");
      } else {
        await api.post("/organizations/org-nodes/", payload);
        setSuccessMessage("OrgNode created successfully.");
      }

      setFormData(initialFormState);
      setEditingId(null);
      await loadPageData();
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Unable to save OrgNode. Please try again."));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = (node: OrgNode) => {
    setEditingId(node.id);
    setSuccessMessage("");
    setError("");
    setFormData({
      company: node.company,
      parent: node.parent ?? "",
      node_type: node.node_type,
      name: node.name,
      node_code: node.node_code ?? "",
      description: node.description ?? "",
      ownership_percentage: node.ownership_percentage ?? "",
      operational_control: node.operational_control,
      financial_control: node.financial_control,
      is_active: node.is_active,
    });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setFormData(initialFormState);
    setError("");
    setSuccessMessage("");
  };

  const handleDelete = async (node: OrgNode) => {
    const hasChildren = orgNodes.some((childNode) => childNode.parent === node.id);
    if (hasChildren) {
      setError("Delete child nodes before deleting this OrgNode.");
      return;
    }

    setIsSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      await api.delete(`/organizations/org-nodes/${node.id}/`);
      setSuccessMessage("OrgNode deleted successfully.");
      if (editingId === node.id) {
        handleCancelEdit();
      }
      await loadPageData();
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Unable to delete OrgNode. Please try again."));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell
      title="OrgNodes"
      description="Manage the company hierarchy with unlimited nesting."
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            {editingId ? "Edit OrgNode" : "Add OrgNode"}
          </h2>

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
          {successMessage && <p className="mt-4 text-sm text-green-600">{successMessage}</p>}

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="Company">
              <select name="company" value={formData.company} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2">
                <option value="">Select company</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.company_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Parent Node">
              <select name="parent" value={formData.parent} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2">
                <option value="">Root node</option>
                {companyNodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Node Type">
              <select name="node_type" value={formData.node_type} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2">
                {nodeTypes.map((nodeType) => (
                  <option key={nodeType.value} value={nodeType.value}>
                    {nodeType.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Name">
              <input name="name" value={formData.name} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2" />
            </Field>

            <Field label="Node Code">
              <input name="node_code" value={formData.node_code} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2" />
            </Field>

            <Field label="Ownership Percentage">
              <input name="ownership_percentage" type="number" min="0" max="100" step="0.01" value={formData.ownership_percentage} onChange={handleInputChange} className="w-full rounded-md border px-3 py-2" />
            </Field>

            <div className="flex items-center gap-6 md:col-span-2 xl:col-span-3">
              <Checkbox name="operational_control" label="Operational Control" checked={formData.operational_control} onChange={handleInputChange} />
              <Checkbox name="financial_control" label="Financial Control" checked={formData.financial_control} onChange={handleInputChange} />
              <Checkbox name="is_active" label="Active Status" checked={formData.is_active} onChange={handleInputChange} />
            </div>

            <div className="md:col-span-2 xl:col-span-3">
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <textarea name="description" value={formData.description} onChange={handleInputChange} className="min-h-24 w-full rounded-md border px-3 py-2" />
            </div>

            <div className="flex gap-3 md:col-span-2 xl:col-span-3">
              <button type="submit" disabled={isSaving} className="rounded-md bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300">
                {isSaving ? "Saving..." : editingId ? "Update OrgNode" : "Save OrgNode"}
              </button>
              {editingId && (
                <button type="button" onClick={handleCancelEdit} className="rounded-md border px-4 py-2 text-gray-700 transition hover:bg-gray-50">
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>

        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">OrgNode Tree</h2>

          {isLoading ? (
            <p className="mt-4 text-sm text-gray-600">Loading OrgNodes...</p>
          ) : orgNodes.length === 0 ? (
            <p className="mt-4 text-sm text-gray-600">No OrgNodes available yet.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="min-w-full border border-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Name</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Node Type</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Company</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Parent</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                    <th className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {treeNodes.map((treeNode) => (
                    <OrgNodeRow
                      key={treeNode.id}
                      node={treeNode}
                      depth={0}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
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

function OrgNodeRow({
  node,
  depth,
  onEdit,
  onDelete,
}: {
  node: OrgNodeTreeNode;
  depth: number;
  onEdit: (node: OrgNode) => void;
  onDelete: (node: OrgNode) => void;
}) {
  return (
    <>
      <tr className="hover:bg-gray-50">
        <td className="border-b px-4 py-3 text-sm text-gray-700">
          <span style={{ paddingLeft: `${depth * 24}px` }}>{node.name}</span>
        </td>
        <td className="border-b px-4 py-3 text-sm text-gray-700">{formatNodeType(node.node_type)}</td>
        <td className="border-b px-4 py-3 text-sm text-gray-700">{node.company_name ?? "Unknown"}</td>
        <td className="border-b px-4 py-3 text-sm text-gray-700">{node.parent_name ?? "Root"}</td>
        <td className="border-b px-4 py-3 text-sm text-gray-700">{node.is_active ? "Active" : "Inactive"}</td>
        <td className="border-b px-4 py-3 text-sm text-gray-700">
          <div className="flex gap-2">
            <button type="button" onClick={() => onEdit(node)} className="rounded-md border px-3 py-1 text-sm text-gray-700 hover:bg-gray-50">
              Edit
            </button>
            <button type="button" onClick={() => onDelete(node)} className="rounded-md border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50">
              Delete
            </button>
          </div>
        </td>
      </tr>
      {node.children.map((childNode) => (
        <OrgNodeRow
          key={childNode.id}
          node={childNode}
          depth={depth + 1}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      {children}
    </div>
  );
}

function Checkbox({
  name,
  label,
  checked,
  onChange,
}: {
  name: string;
  label: string;
  checked: boolean;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
      <input name={name} type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 rounded border-gray-300" />
      {label}
    </label>
  );
}

interface OrgNodeTreeNode extends OrgNode {
  children: OrgNodeTreeNode[];
}

function buildOrgNodeTree(nodes: OrgNode[]) {
  const nodesById = new Map<string, OrgNodeTreeNode>();
  const roots: OrgNodeTreeNode[] = [];

  nodes.forEach((node) => {
    nodesById.set(node.id, { ...node, children: [] });
  });

  nodesById.forEach((node) => {
    if (node.parent && nodesById.has(node.parent)) {
      nodesById.get(node.parent)?.children.push(node);
      return;
    }

    roots.push(node);
  });

  return roots;
}

function buildPayload(formData: OrgNodeFormState) {
  return {
    company: formData.company,
    parent: formData.parent || null,
    node_type: formData.node_type,
    name: formData.name.trim(),
    node_code: emptyToNull(formData.node_code),
    description: formData.description.trim(),
    ownership_percentage: emptyToNull(formData.ownership_percentage),
    operational_control: formData.operational_control,
    financial_control: formData.financial_control,
    is_active: formData.is_active,
  };
}

function emptyToNull(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue ? trimmedValue : null;
}

function formatNodeType(nodeType: string) {
  const matchedNodeType = nodeTypes.find((item) => item.value === nodeType);
  return matchedNodeType?.label ?? nodeType;
}

function getApiErrorMessage(caughtError: unknown, fallbackMessage: string) {
  if (!axios.isAxiosError<ApiValidationError | string>(caughtError)) {
    return fallbackMessage;
  }

  const responseData = caughtError.response?.data;
  if (typeof responseData === "string") {
    return responseData;
  }

  const firstError = responseData ? Object.entries(responseData)[0] : undefined;
  if (!firstError) {
    return fallbackMessage;
  }

  const [fieldName, fieldErrors] = firstError;
  const message = Array.isArray(fieldErrors) ? fieldErrors[0] : fieldErrors;

  return message ? `${formatFieldName(fieldName)}: ${message}` : fallbackMessage;
}

function formatFieldName(fieldName: string) {
  return fieldName
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
