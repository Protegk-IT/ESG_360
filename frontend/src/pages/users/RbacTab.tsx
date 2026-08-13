import { useEffect, useState } from "react";

import { ShieldPlus, ShieldCheck } from "lucide-react";

import UserApi from "@/api/users/UserApi";

import type { UserFormData } from "@/types/user";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/* ==========================================================
    TYPES
========================================================== */

interface Role {
  id: string;
  role_name: string;
  role_code: string;
  description: string;
  is_active: boolean;
}

interface OrganizationUnit {
  id: string;
  name: string;
}

interface Props {
  formData: UserFormData;

  updateField: <K extends keyof UserFormData>(
    field: K,
    value: UserFormData[K]
  ) => void;

  errors: Record<string, string[]>;
}

/* ==========================================================
    COMPONENT
========================================================== */

export default function RoleAccessTab({
  formData,
  updateField,
  errors,
}: Props) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [organizationUnits, setOrganizationUnits] = useState<OrganizationUnit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchReferenceData() {
      try {
        const [rolesRes, orgUnitsRes] = await Promise.all([
          UserApi.getRoles(),
          UserApi.getOrganizationUnits(),
        ]);

        if (cancelled) return;

        setRoles(rolesRes.data);
        setOrganizationUnits(orgUnitsRes.data);
      } catch (error) {
        console.error(error);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchReferenceData();

    return () => {
      cancelled = true;
    };
  }, []);

  const hasRole = formData.role !== "";

  function selectRole(role: Role) {
    // Preserve the hydrated scope when an editor clicks the role already
    // selected. Resetting it in that case turns an otherwise no-op edit into
    // an unscoped assignment when the user saves the form.
    if (formData.role === role.id) return;

    updateField("role", role.id);
    // Reset org node whenever the role changes
    updateField("org_node", "");
  }

  return (
    <div className="space-y-8">
      {/* ======================================================
          ROLE SELECTION
      ====================================================== */}
      <Card>
        <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">
          <CardTitle className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#EEF2FF]">
              <ShieldPlus className="h-5 w-5 text-[#4A3FD6]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#22243A]">
                Role Assignment
              </h2>
              <CardDescription>Select a role for this user.</CardDescription>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-6 p-8">
          {errors.role && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
              {errors.role[0]}
            </div>
          )}

          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-32 rounded-xl" />
              ))}
            </div>
          ) : roles.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center">
                <p className="text-sm text-muted-foreground">
                  No roles available.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {roles.map((role) => {
                const selected = formData.role === role.id;

                return (
                  <Card
                    key={role.id}
                    role="button"
                    onClick={() => selectRole(role)}
                    className={`cursor-pointer transition-all duration-200 ${
                      selected
                        ? "border-[#4A3FD6] bg-[#EEF2FF]"
                        : "hover:border-[#4A3FD6]/40"
                    }`}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4">
                          <div
                            className={`flex h-11 w-11 items-center justify-center rounded-xl ${
                              selected
                                ? "bg-[#4A3FD6] text-white"
                                : "bg-[#EEF2FF] text-[#4A3FD6]"
                            }`}
                          >
                            <ShieldPlus className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="font-semibold text-[#22243A]">
                              {role.role_name}
                            </h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {role.description || "No description"}
                            </p>
                            <Badge
                              variant={role.is_active ? "success" : "secondary"}
                              className="mt-3"
                            >
                              {role.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ======================================================
          ACCESS SCOPE — single org node
      ====================================================== */}
      <Card>
        <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">
          <CardTitle className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#EEF2FF]">
              <ShieldCheck className="h-5 w-5 text-[#4A3FD6]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#22243A]">
                Access Scope
              </h2>
              <CardDescription>
                Assign this role to a single organization unit.
              </CardDescription>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 p-8">
          {!hasRole ? (
            <div className="rounded-xl border border-dashed p-6 text-center">
              <p className="text-muted-foreground">
                Select a role before configuring access scope.
              </p>
            </div>
          ) : (
            <div className="max-w-md space-y-2">
              <Select
                value={formData.org_node}
                onValueChange={(value) => updateField("org_node", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Organization Unit" />
                </SelectTrigger>
                <SelectContent>
                  {organizationUnits.map((unit) => (
                    <SelectItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {errors.org_node && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
              {errors.org_node[0]}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
