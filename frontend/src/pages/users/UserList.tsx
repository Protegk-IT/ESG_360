import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import UserApi from "@/api/users/UserApi";

import type { UserData } from "@/types/user";

import { getUserColumns } from "./columns";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function UserList() {
  const navigate = useNavigate();

  /* =====================================================
     STATE
  ===================================================== */

  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(false);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [roleFilter, setRoleFilter] = useState("All");

  const [selectedUser, setSelectedUser] =
    useState<UserData | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  const getRoleLabel = (user: UserData) =>
    user.role_name || (user.is_superuser ? "Platform administrator" : "-");

  /* =====================================================
     LOAD USERS
  ===================================================== */

  const loadUsers = async () => {
    try {
      setLoading(true);

      const response = await UserApi.getAll();


      setUsers(response.data);
    } catch (error) {
      console.error(error);

      toast.error("Unable to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadUsers();
  }, []);

  /* =====================================================
     FILTER USERS
  ===================================================== */

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const keyword = search.toLowerCase();

      const matchesSearch =
        user.full_name
          ?.toLowerCase()
          .includes(keyword) ||
        user.email
          ?.toLowerCase()
          .includes(keyword) ||
        user.employee_code
          ?.toLowerCase()
          .includes(keyword);

      const matchesStatus =
        statusFilter === "All" ||
        (statusFilter === "Active" &&
          user.is_active) ||
        (statusFilter === "Inactive" &&
          !user.is_active);

      const matchesRole =
        roleFilter === "All" ||
        getRoleLabel(user) === roleFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesRole
      );
    });
  }, [
    users,
    search,
    statusFilter,
    roleFilter,
  ]);

  /* =====================================================
     EXPORT CSV
  ===================================================== */

  const exportUsers = () => {
    const csv = [
      [
        "Name",
        "Employee Code",
        "Role",
        "Mobile Number",
        "Email",
        "Status",
      ],

      ...filteredUsers.map((u) => [
        u.full_name,
        u.employee_code,
        getRoleLabel(u),
        u.mobile_number,
        u.email,
        u.is_active
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
    a.download = "users.csv";
    a.click();

    URL.revokeObjectURL(url);
  };

  /* =====================================================
     ACTIONS
  ===================================================== */

  const handleEdit = (id: number) => {
    navigate(
      `/accounts/users/edit/${id}`
    );
  };

  const handleDelete = (
    user: UserData
  ) => {
    setSelectedUser(user);
  };

  const confirmDelete = async () => {
    if (!selectedUser) return;

    try {
      setDeleting(true);

      await UserApi.delete(
        selectedUser.id
      );

      toast.success(
        "User deleted successfully."
      );

      await loadUsers();

      setSelectedUser(null);
    } catch (error) {
      console.error(error);

      toast.error(
        "Unable to delete user."
      );
    } finally {
      setDeleting(false);
    }
  };

  /* =====================================================
     TABLE COLUMNS
  ===================================================== */

  const columns = getUserColumns({
    onEdit: handleEdit,
    onDelete: handleDelete,
  });

  /* =====================================================
     UI
  ===================================================== */

  return (
    <AppShell
      title="User Management"
      description="Manage platform users and role assignments."
    >
      <DataTable
        columns={columns}
        data={filteredUsers}
        loading={loading}
        emptyMessage="No users found."
        toolbar={
          <DataTableToolbar
            search={search}
            onSearchChange={
              setSearch
            }
            addLabel="Add User"
            onAdd={() =>
              navigate(
                "/accounts/users/create"
              )
            }
            onExport={
              exportUsers
            }
          >
            <Select
              value={
                roleFilter
              }
              onValueChange={
                setRoleFilter
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Role" />
              </SelectTrigger>

<SelectContent>
  <SelectItem value="All">
    All Roles
  </SelectItem>

  {[...new Set(
    users
      .map(getRoleLabel)
      .filter(Boolean)
  )]
    .sort()
    .map((role) => (
      <SelectItem
        key={`role-${role}`}
        value={role}
      >
        {role}
      </SelectItem>
    ))}
</SelectContent>
            </Select>

            <Select
              value={
                statusFilter
              }
              onValueChange={
                setStatusFilter
              }
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

      <ConfirmDialog
        open={!!selectedUser}
        title="Delete User"
        description={
          selectedUser
            ? `Are you sure you want to delete "${selectedUser.full_name}"? This action cannot be undone.`
            : ""
        }
        confirmText="Delete"
        cancelText="Cancel"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() =>
          setSelectedUser(null)
        }
      />
    </AppShell>
  );
}
