import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import RoleApi from "@/api/roles/RoleApi";

import type { Role } from "@/types/role";

import { getRoleColumns } from "./role-columns";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function RoleList() {
  const navigate = useNavigate();

  /* ==========================================================
     STATES
  ========================================================== */

  const [roles, setRoles] = useState<Role[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("All");

  const [typeFilter, setTypeFilter] =
    useState("All");

  const [selectedRole, setSelectedRole] =
    useState<Role | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  /* ==========================================================
     LOAD ROLES
  ========================================================== */

  const loadRoles = async () => {
    try {
      setLoading(true);

      const response =
        await RoleApi.getAll();

      setRoles(response.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  /* ==========================================================
     FILTER ROLES
  ========================================================== */

  const filteredRoles = useMemo(() => {
    return roles.filter((role) => {
      const keyword =
        search.toLowerCase();

      const matchesSearch =
        role.role_name
          ?.toLowerCase()
          .includes(keyword) ||
        role.role_code
          ?.toLowerCase()
          .includes(keyword) ||
        role.description
          ?.toLowerCase()
          .includes(keyword);

      const matchesStatus =
        statusFilter === "All" ||
        (statusFilter === "Active" &&
          role.is_active) ||
        (statusFilter === "Inactive" &&
          !role.is_active);

      const matchesType =
        typeFilter === "All" ||
        (typeFilter === "System" &&
          role.is_system_role) ||
        (typeFilter === "Custom" &&
          !role.is_system_role);

      return (
        matchesSearch &&
        matchesStatus &&
        matchesType
      );
    });
  }, [
    roles,
    search,
    statusFilter,
    typeFilter,
  ]);

  /* ==========================================================
     EXPORT CSV
  ========================================================== */

  const exportRoles = () => {
    const csv = [
      [
        "Role",
        "Code",
        "Description",
        "Type",
        "Status",
      ],

      ...filteredRoles.map((role) => [
        role.role_name,
        role.role_code,
        role.description,
        role.is_system_role
          ? "System"
          : "Custom",
        role.is_active
          ? "Active"
          : "Inactive",
      ]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csv]);

    const url =
      URL.createObjectURL(blob);

    const a =
      document.createElement("a");

    a.href = url;
    a.download = "roles.csv";
    a.click();

    URL.revokeObjectURL(url);
  };

  /* ==========================================================
     EDIT ROLE
  ========================================================== */

  const handleEdit = (
    id: number
  ) => {
    navigate(
      `/accounts/roles/${id}/edit`
    );
  };

  /* ==========================================================
     DELETE ROLE
  ========================================================== */

  const handleDelete = (
    role: Role
  ) => {
    setSelectedRole(role);
  };

    const confirmDelete = async () => {
    if (!selectedRole) return;

    try {
      setDeleting(true);

      await RoleApi.delete(selectedRole.id);

      await loadRoles();

      setSelectedRole(null);
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */

  const columns = getRoleColumns({
    onEdit: handleEdit,
    onDelete: handleDelete,
  });

  /* ==========================================================
     UI
  ========================================================== */

  return (
    <AppShell
      title="Role Management"
      description="Manage company roles and permissions."
    >
      <DataTable
        columns={columns}
        data={filteredRoles}
        loading={loading}
        emptyMessage="No roles found."
        toolbar={
          <DataTableToolbar
            search={search}
            onSearchChange={setSearch}
            addLabel="Add Role"
            onAdd={() =>
              navigate("/accounts/roles/create")
            }
            onExport={exportRoles}
          >
            {/* ======================================
                TYPE FILTER
            ====================================== */}

            <Select
              value={typeFilter}
              onValueChange={setTypeFilter}
            >
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Role Type" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="All">
                  All Types
                </SelectItem>

                <SelectItem value="System">
                  System
                </SelectItem>

                <SelectItem value="Custom">
                  Custom
                </SelectItem>
              </SelectContent>
            </Select>

            {/* ======================================
                STATUS FILTER
            ====================================== */}

            <Select
              value={statusFilter}
              onValueChange={setStatusFilter}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="All">
                  All Status
                </SelectItem>

                <SelectItem value="Active">
                  Active
                </SelectItem>

                <SelectItem value="Inactive">
                  Inactive
                </SelectItem>
              </SelectContent>
            </Select>
          </DataTableToolbar>
        }
      />

      {/* ==========================================
          DELETE DIALOG
      ========================================== */}

      <ConfirmDialog
        open={selectedRole !== null}
        title="Delete Role"
        description={`Are you sure you want to delete "${selectedRole?.role_name}"? This action cannot be undone.`}
        confirmText="Delete Role"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setSelectedRole(null)}
      />
    </AppShell>
  );
}