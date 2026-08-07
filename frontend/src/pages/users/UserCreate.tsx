import { useEffect, useState } from "react";
import { AxiosError } from "axios";
import { toast } from "sonner";
import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  Lock,
  ShieldPlus,
  User,
} from "lucide-react";

import type {
  UserFormData,
} from "@/types/user";

import UserApi from "@/api/users/UserApi";

import { AppSidebar } from "@/components/layout/AppSidebar";

import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

import ProfileTab from "./ProfileTab";
import RbacTab from "./RbacTab";
import PasswordTab from "./PasswordTab";

type ValidationErrors =
  Record<string, string[]>;

type TabType =
  | "profile"
  | "location"
  | "password";

export default function UserCreate() {

  const navigate =
    useNavigate();

  const { id } =
    useParams();

  const [
    activeTab,
    setActiveTab,
  ] =
    useState<TabType>(
      "profile"
    );

  const [
    loading,
    setLoading,
  ] =
    useState(false);

  const [
    errors,
    setErrors,
  ] =
    useState<ValidationErrors>(
      {}
    );

  const [
    formData,
    setFormData,
  ] =
    useState<UserFormData>({
      profile_image: null,

      full_name: "",

      role_name: "",

      email: "",

      username: "",

      mobile_number: "",

      company: "",

      role: "",

      org_node: "",

      designation: "",

      department: "",

      employee_code: "",

      assigned_plants: [],

      is_active: true,

      password: "",

      confirm_password: "",
    });

  /* ===========================================
      LOAD USER
  =========================================== */

 useEffect(() => {
  if (!id) return;

  const userId = id; // userId is now a string

  let cancelled = false;

  async function loadUser() {
    try {
      if (!cancelled) {
        setLoading(true);
      }

      const response =
        await UserApi.getById(userId);

      if (cancelled) return;

      const user = response.data;

      setFormData({
        profile_image: null,

        full_name: user.full_name ?? "",
        role_name: user.role_name ?? "",
        email: user.email ?? "",
        username: user.username ?? "",
        mobile_number: user.mobile_number ?? "",

        company: user.company ?? "",
        role: user.role ?? "",
        org_node: user.org_node ?? "",
        designation: user.designation ?? "",
        department: user.department ?? "",
        employee_code: user.employee_code ?? "",

        assigned_plants: user.assigned_plants ?? [],

        is_active: user.is_active,

        password: "",
        confirm_password: "",
      });
    } catch (error) {
      console.error(error);
    } finally {
      if (!cancelled) {
        setLoading(false);
      }
    }
  }

  void loadUser();

  return () => {
    cancelled = true;
  };
}, [id]);
    /* ==========================================================
      UPDATE FIELD
  ========================================================== */

  const updateField = <
    K extends keyof UserFormData
  >(
    field: K,
    value: UserFormData[K]
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  /* ==========================================================
      SUBMIT
  ========================================================== */

  const handleSubmit = async (
  e: React.FormEvent<HTMLFormElement>
) => {
  e.preventDefault();

  setLoading(true);
  setErrors({});

  try {
    const body = new FormData();

    Object.entries(formData).forEach(
      ([key, value]) => {

        if (key === "profile_image") {

          if (value instanceof File) {
            body.append(key, value);
          }

          return;
        }

        if (key === "assigned_plants") {

          (value as number[]).forEach(
            (plantId) => {
              body.append(
                "assigned_plants",
                String(plantId)
              );
            }
          );

          return;
        }

        body.append(
          key,
          String(value ?? "")
        );
      }
    );

    if (id) {

      await UserApi.update(id, body);

      toast.success(
        "User updated successfully."
      );

    } else {

      await UserApi.create(body);

      toast.success(
        "User created successfully."
      );

    }

    navigate("/accounts/users");

  }  catch (error) {

    const axiosError =
      error as AxiosError<Record<string, unknown>>;

    const data = axiosError.response?.data;

    if (data && typeof data === "object" && !Array.isArray(data)) {

      if (typeof data.detail === "string") {

        // Non-field error: auth/permission/404/etc.
        toast.error(data.detail);

      } else {

        // Field-level validation errors: { field: string[] }
        const validationErrors = data as ValidationErrors;

        setErrors(validationErrors);

        Object.values(validationErrors)
          .flat()
          .forEach((message) => {
            if (typeof message === "string") {
              toast.error(message);
            }
          });

      }

    } else {

      console.error(error);

      toast.error(
        "Something went wrong. Please try again."
      );

    }

  } finally {

    setLoading(false);

  }
};
  {/* ==========================================================
    HEADER
========================================================== */}

return (
  <SidebarProvider>

    <AppSidebar />

    <SidebarInset>

      {/* ==========================================================
          HEADER
      ========================================================== */}

      <header className="border-b bg-white">

        <div className="flex h-16 items-center justify-between px-6">

          <div className="flex items-center gap-4">

            <SidebarTrigger />

            <div>

              <h1 className="text-2xl font-bold">
                {id ? "Edit User" : "Create User"}
              </h1>

              <p className="text-sm text-muted-foreground">
                {id
                  ? "Update user details and permissions."
                  : "Create a new platform user."}
              </p>

            </div>

          </div>

          <button
            type="submit"
            form="user-form"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? "Saving..."
              : id
              ? "Update User"
              : "Create User"}
          </button>

        </div>

      </header>

      <main className="min-h-[calc(100vh-64px)] bg-muted/30 p-6">

        <form
          id="user-form"
          onSubmit={handleSubmit}
        >

          <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">

            {/* ==========================================================
                TABS
            ========================================================== */}

            <div className="border-b border-gray-100 bg-white">

              <div className="flex">

                <button
                  type="button"
                  onClick={() =>
                    setActiveTab("profile")
                  }
                  className={`flex flex-1 items-center justify-center gap-2 border-b-2 px-6 py-4 text-sm font-medium transition-colors ${
                    activeTab === "profile"
                      ? "border-blue-500 bg-blue-50 text-blue-600"
                      : "border-transparent bg-white text-gray-500 hover:bg-blue-50 hover:text-blue-600"
                  }`}
                >
                  <User className="h-4 w-4" />
                  Profile
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setActiveTab("location")
                  }
                  className={`flex flex-1 items-center justify-center gap-2 border-b-2 px-6 py-4 text-sm font-medium transition-colors ${
                    activeTab === "location"
                      ? "border-blue-500 bg-blue-50 text-blue-600"
                      : "border-transparent bg-white text-gray-500 hover:bg-blue-50 hover:text-blue-600"
                  }`}
                >
                  <ShieldPlus className="h-4 w-4" />
                  Roles & Scopes
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setActiveTab("password")
                  }
                  className={`flex flex-1 items-center justify-center gap-2 border-b-2 px-6 py-4 text-sm font-medium transition-colors ${
                    activeTab === "password"
                      ? "border-blue-500 bg-blue-50 text-blue-600"
                      : "border-transparent bg-white text-gray-500 hover:bg-blue-50 hover:text-blue-600"
                  }`}
                >
                  <Lock className="h-4 w-4" />
                  Password
                </button>

              </div>

            </div>

            {/* ==========================================================
                FORM CONTENT
            ========================================================== */}

            <div className="bg-white p-8">

              {loading && (

                <div className="mb-6 text-sm text-muted-foreground">
                  Loading user...
                </div>

              )}

             

              {activeTab === "profile" && (
                <ProfileTab
                  formData={formData}
                  updateField={updateField}
                  errors={errors}
                />
              )}

             {activeTab === "location" && (
  <RbacTab
    formData={formData}
    updateField={updateField}
    errors={errors}
  />
)}

              {activeTab === "password" && (
                <PasswordTab
                  formData={formData}
                  updateField={updateField}
                  errors={errors}
                />
              )}

            </div>

          </div>

        </form>

      </main>

    </SidebarInset>

  </SidebarProvider>
);
}