import { useEffect, useState } from "react";

import { useNavigate, useParams } from "react-router-dom";

import { Loader2 } from "lucide-react";

import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import DepartmentApi from "@/api/departments/DepartmentApi";
import CompanyApi from "@/api/companies/CompanyApi";

import type { Company } from "@/types/company";

import type { Department, DepartmentFormData } from "@/types/department";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";

import { Checkbox } from "@/components/ui/checkbox";

import { Input } from "@/components/ui/input";

import { Label } from "@/components/ui/label";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Skeleton } from "@/components/ui/skeleton";

import { Textarea } from "@/components/ui/textarea";

export default function DepartmentForm() {
  const navigate = useNavigate();

  const { id } = useParams<{ id: string }>();

  const isEdit = Boolean(id);

  /* ==========================================================
      STATE
  ========================================================== */

  const [loading, setLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [company, setCompany] = useState<Company | null>(null);

  const [parentDepartments, setParentDepartments] = useState<Department[]>([]);

  const [formData, setFormData] = useState<DepartmentFormData>({
    company: "",
    parent_department: null,
    name: "",
    code: "",
    description: "",
    is_active: true,
  });

  /* ==========================================================
      LOAD DATA
      React 19 Safe
  ========================================================== */
useEffect(() => {
  const fetchData = async () => {
    try {
      setLoading(true);

      const companyRes = await CompanyApi.getProfile();
      console.log("Company:", companyRes.data);

      const parentRes = await DepartmentApi.getParentDepartments();
      console.log("Parents:", parentRes.data);

      setCompany(companyRes.data);
      setParentDepartments(parentRes.data);

      setFormData((prev) => ({
        ...prev,
        company: companyRes.data.id,
      }));

      if (isEdit && id) {
        const departmentRes =
          await DepartmentApi.getById(id);

        setFormData({
          company: departmentRes.data.company,
          parent_department: departmentRes.data.parent_department,
          name: departmentRes.data.name,
          code: departmentRes.data.code,
          description: departmentRes.data.description ?? "",
          is_active: departmentRes.data.is_active,
        });
      }

    } catch (error) {
      console.error("Department Form Error:", error);
      toast.error("Unable to load department.");
    } finally {
      setLoading(false);
    }
  };

  void fetchData();
}, [id, isEdit]);

  /* ==========================================================
      UPDATE FIELD
  ========================================================== */

  const updateField = <K extends keyof DepartmentFormData>(
    field: K,
    value: DepartmentFormData[K],
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
    if (!formData.name.trim()) {
      toast.error("Department name is required.");
      return false;
    }

    if (!formData.code.trim()) {
      toast.error("Department code is required.");
      return false;
    }

    return true;
  };

  /* ==========================================================
      SUBMIT
  ========================================================== */

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    try {
      setSaving(true);

      if (isEdit && id) {
        await DepartmentApi.update(id, formData);

        toast.success("Department updated successfully.");
      } else {
        await DepartmentApi.create(formData);

        toast.success("Department created successfully.");
      }

      navigate("/company/departments");
    } catch (error) {
      console.error(error);

      toast.error(
        isEdit
          ? "Unable to update department."
          : "Unable to create department.",
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
        title={isEdit ? "Edit Department" : "Create Department"}
        description="Loading department..."
      >
        <div className="px-4 md:px-6 lg:px-8">
          <Card>
            <CardHeader className="px-6 py-6">
              <Skeleton className="h-6 w-52" />
              <Skeleton className="mt-2 h-4 w-80" />
            </CardHeader>

            <CardContent className="space-y-6 px-6 py-6">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-24 w-full" />
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title={isEdit ? "Edit Department" : "Create Department"}
      description={
        isEdit ? "Update department details." : "Create a new department."
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6 px-4 md:px-6 lg:px-8">
        {/* ==========================================================
            DEPARTMENT INFORMATION
        ========================================================== */}
        <Card>
          <CardHeader className="px-6 py-6">
            <CardTitle>Department Information</CardTitle>
            <CardDescription>
              Basic information about the department.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6 px-6 py-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {/* Company */}
              <div className="space-y-2">
                <Label>Company</Label>
                <Input
                  value={company?.company_name ?? "Loading..."}
                  readOnly
                  className="bg-muted text-foreground disabled:opacity-100"
                />
              </div>

              {/* Parent Department */}
              <div className="space-y-2">
                <Label>Parent Department</Label>
                <Select
                  value={formData.parent_department ?? "none"}
                  onValueChange={(value) =>
                    updateField(
                      "parent_department",
                      value === "none" ? null : value,
                    )
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Parent Department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>

                    {parentDepartments
                      .filter((department) => department.id !== id)
                      .map((department) => (
                        <SelectItem key={department.id} value={department.id}>
                          {department.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Department Name */}
              <div className="space-y-2">
                <Label>Department Name</Label>
                <Input
                  placeholder="Enter department name"
                  value={formData.name}
                  onChange={(e) => updateField("name", e.target.value)}
                />
              </div>

              {/* Department Code */}
              <div className="space-y-2">
                <Label>Department Code</Label>
                <Input
                  placeholder="Enter department code"
                  value={formData.code}
                  onChange={(e) => updateField("code", e.target.value)}
                />
              </div>

              {/* Description */}
              <div className="space-y-2 md:col-span-2 lg:col-span-3">
                <Label>Description</Label>
                <Textarea
                  placeholder="Enter department description"
                  rows={5}
                  value={formData.description}
                  onChange={(e) => updateField("description", e.target.value)}
                />
              </div>

              {/* Status */}
              <div className="flex items-center space-x-3 md:col-span-2 lg:col-span-3">
                <Checkbox
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) =>
                    updateField("is_active", checked === true)
                  }
                />
                <Label htmlFor="is_active" className="cursor-pointer">
                  Active Department
                </Label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ==========================================================
            ACTIONS
        ========================================================== */}
        <Card>
          <CardContent className="flex items-center justify-end gap-3 px-6 py-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/departments")}
            >
              Cancel
            </Button>

            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isEdit ? "Updating..." : "Creating..."}
                </>
              ) : isEdit ? (
                "Update Department"
              ) : (
                "Create Department"
              )}
            </Button>
          </CardContent>
        </Card>
      </form>
    </AppShell>
  );
}