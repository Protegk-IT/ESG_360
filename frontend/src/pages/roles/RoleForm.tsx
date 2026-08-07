import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Loader2,
  ShieldCheck,
} from "lucide-react";

import { toast } from "sonner";

import api from "@/services/api";

import AppShell from "@/components/layout/AppShell";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import axios from "axios";

/* ==========================================================
    TYPES
========================================================== */

interface Permission {
  id: number;
  name: string;
  code: string;
  description: string;
}

interface MatrixPermission extends Permission {
  module: string;
  action: string;
}

interface RoleFormData {
  role_name: string;
  role_code: string;
  description: string;
  permissions: number[];
}

/* ==========================================================
    COMPONENT
========================================================== */

export default function RoleForm() {
  const navigate = useNavigate();

  const { id } =
    useParams<{ id: string }>();

  const isEdit = Boolean(id);

  /* ==========================================================
      STATE
  ========================================================== */

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [permissions, setPermissions] =
    useState<MatrixPermission[]>([]);

  const [formData, setFormData] =
    useState<RoleFormData>({
      role_name: "",
      role_code: "",
      description: "",
      permissions: [],
    });

  /* ==========================================================
      LOAD DATA
  ========================================================== */
useEffect(() => {
  const fetchData = async () => {
    try {
      setLoading(true);

      const permissionRes = await api.get(
        "/accounts/permissions/"
      );

      const parsedPermissions = permissionRes.data.map(
        (permission: Permission) => {
          const [
            module = "Other",
            action = permission.name,
          ] = permission.code.split(".");

          return {
            ...permission,
            module:
              module.charAt(0).toUpperCase() +
              module.slice(1),
            action:
              action.charAt(0).toUpperCase() +
              action.slice(1),
          };
        }
      );

      setPermissions(parsedPermissions);

      if (isEdit && id) {
        const roleRes = await api.get(
          `/accounts/roles/${id}/`
        );

        setFormData({
          role_name: roleRes.data.role_name ?? "",
          role_code: roleRes.data.role_code ?? "",
          description: roleRes.data.description ?? "",
          permissions: roleRes.data.permissions ?? [],
        });
      }
    } catch (error) {
      console.error(error);
      toast.error("Unable to load role.");
    } finally {
      setLoading(false);
    }
  };

  fetchData();
}, [id, isEdit]);
  /* ==========================================================
      GROUP PERMISSIONS
  ========================================================== */

  const groupedPermissions =
    useMemo(() => {
      const grouped: Record<
        string,
        Record<
          string,
          MatrixPermission
        >
      > = {};

      permissions.forEach(
        (permission) => {
          if (
            !grouped[
              permission.module
            ]
          ) {
            grouped[
              permission.module
            ] = {};
          }

          grouped[
            permission.module
          ][permission.action] =
            permission;
        }
      );

      return grouped;
    }, [permissions]);

  /* ==========================================================
      ACTIONS
  ========================================================== */

  const actions = useMemo(() => {
    return Array.from(
      new Set(
        permissions.map(
          (permission) =>
            permission.action
        )
      )
    );
  }, [permissions]);
    /* ==========================================================
      TOGGLE PERMISSION
  ========================================================== */

  const togglePermission = (
    permissionId: number
  ) => {
    setFormData((prev) => ({
      ...prev,

      permissions:
        prev.permissions.includes(
          permissionId
        )
          ? prev.permissions.filter(
              (id) =>
                id !== permissionId
            )
          : [
              ...prev.permissions,
              permissionId,
            ],
    }));
  };

  /* ==========================================================
      SELECT ALL
  ========================================================== */

  const handleSelectAll = (
    checked: boolean
  ) => {
    setFormData((prev) => ({
      ...prev,

      permissions: checked
        ? permissions.map(
            (permission) =>
              permission.id
          )
        : [],
    }));
  };

  /* ==========================================================
      UPDATE FIELD
  ========================================================== */

  const updateField = <
    K extends keyof RoleFormData
  >(
    field: K,
    value: RoleFormData[K]
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  /* ==========================================================
      VALIDATION
  ========================================================== */

  const validate = () => {
    if (
      !formData.role_name.trim()
    ) {
      toast.error(
        "Role Name is required."
      );

      return false;
    }

    return true;
  };

  /* ==========================================================
      SUBMIT
  ========================================================== */

  const handleSubmit =
    async () => {
      if (!validate()) {
        return;
      }

      try {
        setSaving(true);

        if (isEdit && id) {
          await api.put(
            `/accounts/roles/${id}/`,
            formData
          );

          toast.success(
            "Role updated successfully."
          );
        } else {
          await api.post(
            "/accounts/roles/",
            formData
          );

          toast.success(
            "Role created successfully."
          );
        }

        navigate(
          "/accounts/roles"
        );
      }catch (error) {
  if (axios.isAxiosError(error)) {
    console.log("Status:", error.response?.status);
    console.log("Response:", error.response?.data);
    console.log("Request Data:", formData);
  } else {
    console.error(error);
  }

        toast.error(
          isEdit
            ? "Unable to update role."
            : "Unable to create role."
        );
      } finally {
        setSaving(false);
      }
    };

  /* ==========================================================
      LOADING
  ========================================================== */

  if (loading) {
    return (
      <AppShell
        title={
          isEdit
            ? "Update Role"
            : "Create Role"
        }
        description="Configure role information and assign permissions."
      >
        <Card>

          <CardHeader>

            <Skeleton className="h-8 w-64" />

            <Skeleton className="mt-2 h-4 w-96" />

          </CardHeader>

          <CardContent className="space-y-6 p-8">

            {Array.from({
              length: 8,
            }).map((_, index) => (
              <Skeleton
                key={index}
                className="h-12 rounded-lg"
              />
            ))}

          </CardContent>

        </Card>
      </AppShell>
    );
  }
    /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title={
        isEdit
          ? "Update Role"
          : "Create Role"
      }
      description="Configure role information and assign permissions."
    >
      <div className="space-y-8">

        {/* ======================================================
            ROLE INFORMATION
        ====================================================== */}

        <Card>

          <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">

            <CardTitle className="flex items-center gap-3">

              <div
                className="
                  flex
                  h-11
                  w-11
                  items-center
                  justify-center
                  rounded-xl
                  bg-[#EEF2FF]
                "
              >
                <ShieldCheck
                  className="
                    h-5
                    w-5
                    text-[#4A3FD6]
                  "
                />
              </div>

              <div>

                <h2
                  className="
                    text-lg
                    font-semibold
                    text-[#22243A]
                  "
                >
                  Role Information
                </h2>

                <p
                  className="
                    mt-1
                    text-sm
                    text-[#6B7280]
                  "
                >
                  Enter basic information for this role.
                </p>

              </div>

            </CardTitle>

          </CardHeader>

          <CardContent className="space-y-8 p-8">

            <div className="space-y-2">

                <Label>
                  Role Code
                </Label>

                <Input
                  placeholder="Enter role code"
                  value={formData.role_code}
                  onChange={(e) =>
                    updateField(
                      "role_code",
                      e.target.value
                    )
                  }
                />

              </div>


              <div className="space-y-2">

                <Label>
                  Role Name
                </Label>

                <Input
                  placeholder="Enter role name"
                  value={formData.role_name}
                  onChange={(e) =>
                    updateField(
                      "role_name",
                      e.target.value
                    )
                  }
                />

              </div>

              

          

            <div className="space-y-2">

              <Label>
                Description
              </Label>

              <Textarea
                rows={4}
                placeholder="Enter role description..."
                value={formData.description}
                onChange={(e) =>
                  updateField(
                    "description",
                    e.target.value
                  )
                }
              />

            </div>

          </CardContent>

        </Card>

        {/* ======================================================
            PERMISSION MATRIX
        ====================================================== */}

        <Card>

          <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">

            <div className="flex items-center justify-between">

              <div>

                <CardTitle>
                  Permission Matrix
                </CardTitle>

                <CardDescription>
                  Assign permissions for this role.
                </CardDescription>

              </div>

              <div className="flex items-center gap-3">

                <Checkbox
                  checked={
                    permissions.length > 0 &&
                    formData.permissions.length ===
                      permissions.length
                  }
                  onCheckedChange={(checked) =>
                    handleSelectAll(
                      checked === true
                    )
                  }
                />

                <span
                  className="
                    text-sm
                    font-medium
                    text-[#374151]
                  "
                >
                  Select All
                </span>

              </div>

            </div>

          </CardHeader>

          <CardContent className="p-0">

            <Table>

              <TableHeader className="border-y bg-[#F8F9FC]">

                <TableRow className="hover:bg-transparent">

                  <TableHead
                    className="
                      w-64
                      px-6
                      text-sm
                      font-semibold
                    "
                  >
                    Module
                  </TableHead>

                  {actions.map((action) => (

                    <TableHead
                      key={action}
                      className="
                        text-center
                        text-sm
                        font-semibold
                      "
                    >
                      {action}
                    </TableHead>

                  ))}

                </TableRow>

              </TableHeader>

              <TableBody>

                                {Object.entries(groupedPermissions).map(
                  ([module, modulePermissions]) => (
                    <TableRow
                      key={module}
                      className="
                        border-b
                        transition-colors
                        hover:bg-[#F5F5FB]
                      "
                    >
                      {/* Module */}

                      <TableCell
                        className="
                          px-6
                          py-5
                          font-semibold
                          text-[#22243A]
                        "
                      >
                        {module}
                      </TableCell>

                      {/* Actions */}

                      {actions.map((action) => {
                        const permission =
                          modulePermissions[action];

                        return (
                          <TableCell
                            key={action}
                            className="
                              px-6
                              py-5
                              text-center
                            "
                          >
                            {permission ? (
                              <div className="flex justify-center">

                                <Checkbox
                                  checked={formData.permissions.includes(
                                    permission.id
                                  )}
                                  onCheckedChange={() =>
                                    togglePermission(
                                      permission.id
                                    )
                                  }
                                />

                              </div>
                            ) : (
                              <span className="text-[#CBD5E1]">
                                —
                              </span>
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  )
                )}

              </TableBody>

            </Table>

          </CardContent>

        </Card>

        {/* ======================================================
            ACTIONS
        ====================================================== */}

        <div className="flex justify-end gap-3">

          <Button
            variant="outline"
            onClick={() =>
              navigate("/accounts/roles")
            }
          >
            Cancel
          </Button>

          <Button
            onClick={handleSubmit}
            disabled={saving}
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isEdit
                  ? "Updating..."
                  : "Saving..."}
              </>
            ) : (
              <>
                {isEdit
                  ? "Update Role"
                  : "Create Role"}
              </>
            )}
          </Button>

        </div>

      </div>

    </AppShell>
  );
}