import { useEffect, useRef, useState } from "react";

import {
  Building2,
  Camera,
  Mail,
  Phone,
  User,
} from "lucide-react";


import type { UserFormData } from "@/types/user";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";


import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import UserApi from "@/api/users/UserApi";
import type { Company } from "@/types/company";
import CompanyApi from "@/api/companies/CompanyApi";

/* ==========================================================
    TYPES
========================================================== */

interface Option {
  id: number;
  name: string;
}


interface ProfileTabProps {
  formData: UserFormData;

  updateField: <
    K extends keyof UserFormData
  >(
    field: K,
    value: UserFormData[K]
  ) => void;

  errors: Record<string, string[]>;
}

/* ==========================================================
    COMPONENT
========================================================== */

export default function ProfileTab({
  formData,
  updateField,
  errors,
}: ProfileTabProps) {

  /* ==========================================================
      STATE
  ========================================================== */

  const [preview, setPreview] =
    useState("");

 const [company, setCompany] =
  useState<Company | null>(null);
  
  const [departments, setDepartments] =
    useState<Option[]>([]);


/* ==========================================================
    LOAD MASTER DATA
    React 19 Safe
========================================================== */

const updateFieldRef = useRef(updateField);

useEffect(() => {
  updateFieldRef.current = updateField;
});

useEffect(() => {
  let cancelled = false;

  async function fetchMasterData() {
    try {
      const [companyRes, departmentRes] = await Promise.all([
        CompanyApi.getProfile(),
        UserApi.getDepartments(),
      ]);

      if (cancelled) return;

      setCompany(companyRes.data);
      setDepartments(departmentRes.data);

      updateFieldRef.current("company", companyRes.data.id);
    } catch (error) {
      console.error(error);
    }
  }

  void fetchMasterData();

  return () => {
    cancelled = true;
  };
}, []);
  /* ==========================================================
      PROFILE IMAGE
  ========================================================== */

  const handleImageChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file =
      event.target.files?.[0];

    if (!file) return;

    updateField(
      "profile_image",
      file
    );

    setPreview(
      URL.createObjectURL(file)
    );
  };

  /* ==========================================================
      VALIDATION ERROR
  ========================================================== */

  const renderError = (
    field: string
  ) =>
    errors[field] ? (
      <p className="mt-1 text-sm text-red-500">
        {errors[field][0]}
      </p>
    ) : null;

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <div className="space-y-8">
            {/* ======================================================
          PROFILE INFORMATION
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
              <User
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
                User Profile
              </h2>

              <CardDescription>
                Personal information and account profile.
              </CardDescription>

            </div>

          </CardTitle>

        </CardHeader>

        <CardContent className="space-y-8 p-8">

          {/* ======================================
              PROFILE IMAGE
          ====================================== */}

          <div className="flex items-center gap-6">

            <div
              className="
                flex
                h-24
                w-24
                items-center
                justify-center
                overflow-hidden
                rounded-full
                border
                bg-[#F8F9FC]
              "
            >

              {preview ? (

                <img
                  src={preview}
                  alt="Profile"
                  className="h-full w-full object-cover"
                />

              ) : (

                <User
                  className="
                    h-10
                    w-10
                    text-gray-400
                  "
                />

              )}

            </div>

            <div className="space-y-2">

              <Button
                variant="outline"
                asChild
              >

                <label className="cursor-pointer">

                  <Camera className="mr-2 h-4 w-4" />

                  Upload Photo

                  <input
                    hidden
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                  />

                </label>

              </Button>

              <p className="text-xs text-muted-foreground">
                JPG, PNG up to 2 MB.
              </p>

            </div>

          </div>

          {/* ======================================
              BASIC INFORMATION
          ====================================== */}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

            <div className="space-y-2">

              <Label>
                Full Name
              </Label>

              <Input
                value={formData.full_name}
                onChange={(e) =>
                  updateField(
                    "full_name",
                    e.target.value
                  )
                }
              />

              {renderError("full_name")}

            </div>

            <div className="space-y-2">

              <Label>
                Username
              </Label>

              <Input
                value={formData.username}
                onChange={(e) =>
                  updateField(
                    "username",
                    e.target.value
                  )
                }
              />

              {renderError("username")}

            </div>

            <div className="space-y-2">

              <Label>
                Email Address
              </Label>

              <div className="relative">

                <Mail
                  className="
                    absolute
                    left-3
                    top-1/2
                    h-4
                    w-4
                    -translate-y-1/2
                    text-muted-foreground
                  "
                />

                <Input
                  type="email"
                  className="pl-10"
                  value={formData.email}
                  onChange={(e) =>
                    updateField(
                      "email",
                      e.target.value
                    )
                  }
                />

              </div>

              {renderError("email")}

            </div>

            <div className="space-y-2">

              <Label>
                Mobile Number
              </Label>

              <div className="relative">

                <Phone
                  className="
                    absolute
                    left-3
                    top-1/2
                    h-4
                    w-4
                    -translate-y-1/2
                    text-muted-foreground
                  "
                />

                <Input
                  className="pl-10"
                  value={formData.mobile_number}
                  onChange={(e) =>
                    updateField(
                      "mobile_number",
                      e.target.value
                    )
                  }
                />

              </div>

              {renderError("mobile_number")}

            </div>

            <div className="space-y-2">

              <Label>
                Employee Code
              </Label>

              <Input
                value={formData.employee_code}
                onChange={(e) =>
                  updateField(
                    "employee_code",
                    e.target.value
                  )
                }
              />

              {renderError("employee_code")}

            </div>

          </div>

        </CardContent>

      </Card>

            {/* ======================================================
          ORGANIZATION INFORMATION
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
              <Building2
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
                Organization Information
              </h2>

              <CardDescription>
                Assign the user to an organization and department.
              </CardDescription>

            </div>

          </CardTitle>

        </CardHeader>

        <CardContent className="space-y-8 p-8">

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

            {/* ======================================
                COMPANY
            ====================================== */}

            <div className="space-y-2">

              <Label>
                Company
              </Label>

               <p className="font-medium">
               {company?.company_name}
              </p>

            </div>

            {/* ======================================
                DEPARTMENT
            ====================================== */}

            <div className="space-y-2">

              <Label>
                Department
              </Label>

              <Select
                value={String(formData.department ?? "")}
                onValueChange={(value) =>
                  updateField(
                    "department",
                    value
                  )
                }
              >

                <SelectTrigger>

                  <SelectValue placeholder="Select Department" />

                </SelectTrigger>

                <SelectContent>

                  {departments.map((department) => (

                    <SelectItem
                      key={department.id}
                      value={String(department.id)}
                    >
                      {department.name}
                    </SelectItem>

                  ))}

                </SelectContent>

              </Select>

              {renderError("department")}

            </div>

            {/* ======================================
                DESIGNATION
            ====================================== */}

           <div className="space-y-2">

  <Label>
    Designation
  </Label>

  <Input
    placeholder="Enter designation"
    value={formData.designation}
    onChange={(e) =>
      updateField(
        "designation",
        e.target.value
      )
    }
  />

  {errors.designation && (
    <p className="text-sm text-red-500">
      {errors.designation[0]}
    </p>
  )}

</div>
</div>

            {/* ======================================
                ACTIVE STATUS
            ====================================== */}

            <div className="flex items-center rounded-xl border p-4">

              <Checkbox
                checked={formData.is_active}
                onCheckedChange={(checked) =>
                  updateField(
                    "is_active",
                    checked === true
                  )
                }
              />

              <div className="ml-3">

                <Label>
                  Active User
                </Label>

                <p className="text-sm text-muted-foreground">
                  Allow this user to access the system.
                </p>

              </div>

            </div>

          

          
        </CardContent>

      </Card>
            {/* ======================================================
          ACTIONS
      ====================================================== */}

      <div className="flex items-center justify-end gap-3">

        <Button
          type="button"
          variant="outline"
          onClick={() =>
            window.history.back()
          }
        >
          Cancel
        </Button>

        <Button
          type="submit"
        >
          Save User
        </Button>

      </div>

    </div>
  );
}