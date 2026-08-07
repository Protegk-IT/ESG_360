import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import OrganizationApi from "@/api/organizations/OrganizationApi";

import type { OrgNode } from "@/types/organization";

import { getOrganizationColumns } from "./OrgColumns";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { toast } from "sonner";

export default function OrganizationList() {
  const navigate = useNavigate();

  /* ==========================================================
      STATES
  ========================================================== */

  const [organizations, setOrganizations] = useState<OrgNode[]>([]);

  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] = useState("All");

  const [typeFilter, setTypeFilter] = useState("All");

  const [selectedNode, setSelectedNode] = useState<OrgNode | null>(null);

  const [deleting, setDeleting] = useState(false);

  /* ==========================================================
      LOAD ORGANIZATIONS
  ========================================================== */
const loadOrganizations = async () => {
  try {
    setLoading(true);

    const response = await OrganizationApi.getAll();

    console.log("API Response:", response.data);

    setOrganizations(response.data);
  } catch (error) {
    console.error(error);
    toast.error("Unable to load organization nodes.");
  } finally {
    setLoading(false);
  }
};

useEffect(() => {
  // eslint-disable-next-line react-hooks/set-state-in-effect
  loadOrganizations();
}, []);
  /* ==========================================================
      FILTER
  ========================================================== */

  const filteredOrganizations = useMemo(() => {
    return organizations.filter((node) => {
      const keyword = search.toLowerCase();

      const matchesSearch =
        node.name.toLowerCase().includes(keyword) ||
        node.code.toLowerCase().includes(keyword) ||
        (node.company_name ?? "").toLowerCase().includes(keyword);

      const matchesStatus =
        statusFilter === "All" ||
        (statusFilter === "Active" && node.is_active) ||
        (statusFilter === "Inactive" && !node.is_active);

      const matchesType = typeFilter === "All" || node.node_type === typeFilter;

      return matchesSearch && matchesStatus && matchesType;
    });
  }, [organizations, search, statusFilter, typeFilter]);

  /* ==========================================================
      EXPORT CSV
  ========================================================== */

  const exportOrganizations = () => {
    const csv = [
      ["Name", "Code", "Type", "Company", "Parent", "Ownership", "Status"],
      ...filteredOrganizations.map((node) => [
        node.name,
        node.code,
        node.node_type,
        node.company_name,
        node.parent_name ?? "-",
        node.ownership_percentage,
        node.is_active ? "Active" : "Inactive",
      ]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csv]);

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");

    a.href = url;

    a.download = "organization.csv";

    a.click();

    URL.revokeObjectURL(url);
  };

  /* ==========================================================
      EDIT
  ========================================================== */

  const handleEdit = (id: string) => {
    navigate(`/org/nodes/${id}/edit`);
  };

  /* ==========================================================
      DELETE
  ========================================================== */

  const handleDelete = (node: OrgNode) => {
    setSelectedNode(node);
  };

  const confirmDelete = async () => {
    if (!selectedNode) return;

    try {
      setDeleting(true);

      await OrganizationApi.delete(selectedNode.id);

      toast.success("Organization deleted successfully.");

      await loadOrganizations();

      setSelectedNode(null);
    } catch (error) {
      console.error(error);

      toast.error("Unable to delete organization.");
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
      TABLE COLUMNS
  ========================================================== */

  const columns = getOrganizationColumns({
    onEdit: handleEdit,
    onDelete: handleDelete,
  });

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title="Organization Management"
      description="Manage organization hierarchy."
    >
  
        <DataTable
          columns={columns}
          data={filteredOrganizations}
          loading={loading}
          emptyMessage="No organization nodes found."
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
              addLabel="Add Organization"
              onAdd={() => navigate("/org/nodes/")}
              onExport={exportOrganizations}
              className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center"
            >
              {/* ======================================
                  NODE TYPE FILTER
              ====================================== */}
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-full sm:w-52">
                  <SelectValue placeholder="Node Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All Types</SelectItem>
                  <SelectItem value="LEGAL_ENTITY">Legal Entity</SelectItem>
                  <SelectItem value="BUSINESS_UNIT">Business Unit</SelectItem>
                  <SelectItem value="DIVISION">Division</SelectItem>
                  <SelectItem value="REGION">Region</SelectItem>
                  <SelectItem value="FACILITY">Facility</SelectItem>
                </SelectContent>
              </Select>

              {/* ======================================
                  STATUS FILTER
              ====================================== */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All Status</SelectItem>
                  <SelectItem value="Active">Active</SelectItem>
                  <SelectItem value="Inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </DataTableToolbar>
          }
        />
      

      {/* ==========================================================
          DELETE DIALOG
      ========================================================== */}
      <ConfirmDialog
        open={selectedNode !== null}
        title="Delete Organization Node"
        description={`Are you sure you want to delete "${selectedNode?.name}"? This action cannot be undone.`}
        confirmText="Delete Organization"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setSelectedNode(null)}
      />
    </AppShell>
  );
}