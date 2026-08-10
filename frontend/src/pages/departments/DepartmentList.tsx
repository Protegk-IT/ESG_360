import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";
import ConfirmDialog from "@/common/ConfirmDialog";

import DepartmentApi from "@/api/departments/DepartmentApi";

import type { Department } from "@/types/department";

import { getDepartmentColumns } from "./DepartmentColumns";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { toast } from "sonner";

export default function DepartmentList() {

  const navigate = useNavigate();

  /* ==========================================================
     STATES
  ========================================================== */

  const [departments, setDepartments] =
    useState<Department[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("All");

  const [selectedDepartment, setSelectedDepartment] =
    useState<Department | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  /* ==========================================================
     LOAD DEPARTMENTS
  ========================================================== */
const loadDepartments = async () => {
  const response = await DepartmentApi.getAll();

  setDepartments(response.data);
};

useEffect(() => {

  let cancelled = false;

  async function fetchDepartments() {

    try {

      if (!cancelled) {
        setLoading(true);
      }

      const response =
        await DepartmentApi.getAll();

      if (cancelled) return;

      setDepartments(
        response.data
      );

    } catch (error) {

      console.error(error);

      if (!cancelled) {
        toast.error(
          "Unable to load departments."
        );
      }

    } finally {

      if (!cancelled) {
        setLoading(false);
      }

    }

  }

  void fetchDepartments();

  return () => {
    cancelled = true;
  };

}, []);



  /* ==========================================================
     FILTER
  ========================================================== */

  const filteredDepartments =
    useMemo(() => {

      return departments.filter(
        (department) => {

          const keyword =
            search.toLowerCase();

          const matchesSearch =

            department.name
              ?.toLowerCase()
              .includes(keyword)

            ||

            department.code
              ?.toLowerCase()
              .includes(keyword)

            ||

            department.company_name
              ?.toLowerCase()
              .includes(keyword);

          const matchesStatus =

            statusFilter ===
              "All"

            ||

            (
              statusFilter ===
                "Active"

              &&

              department.is_active
            )

            ||

            (
              statusFilter ===
                "Inactive"

              &&

              !department.is_active
            );

          return (

            matchesSearch

            &&

            matchesStatus

          );

        }

      );

    }, [

      departments,

      search,

      statusFilter,

    ]);

  /* ==========================================================
     EXPORT CSV
  ========================================================== */

  const exportDepartments =
    () => {

      const csv = [

        [

          "Code",

          "Department",

          "Company",

          "Status",

        ],

        ...filteredDepartments.map(
          (
            department
          ) => [

            department.code,

            department.name,

            department.company_name,

            department.is_active
              ? "Active"
              : "Inactive",

          ]
        ),

      ]
        .map(
          (row) =>
            row.join(",")
        )
        .join("\n");

      const blob =
        new Blob([csv]);

      const url =
        URL.createObjectURL(
          blob
        );

      const a =
        document.createElement(
          "a"
        );

      a.href = url;

      a.download =
        "departments.csv";

      a.click();

      URL.revokeObjectURL(
        url
      );

    };

  /* ==========================================================
     EDIT
  ========================================================== */

  const handleEdit =
    (id: number) => {

      navigate(
        `/company/departments/${id}/edit`
      );

    };

  /* ==========================================================
     DELETE
  ========================================================== */

  const handleDelete =
    (
      department: Department
    ) => {

      setSelectedDepartment(
        department
      );

    };

      /* ==========================================================
     CONFIRM DELETE
  ========================================================== */

  const confirmDelete =
    async () => {

      if (!selectedDepartment)
        return;

      try {

        setDeleting(true);

        await DepartmentApi.delete(
          selectedDepartment.id
        );

        toast.success(
          "Department deleted successfully."
        );

        await loadDepartments();

        setSelectedDepartment(
          null
        );

      } catch (error) {

        console.error(error);

        toast.error(
          "Unable to delete department."
        );

      } finally {

        setDeleting(false);

      }

    };

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */

  const columns =
    getDepartmentColumns({

      onEdit:
        handleEdit,

      onDelete:
        handleDelete,

    });

  /* ==========================================================
     UI
  ========================================================== */

  return (

    <AppShell
      title="Department Management"
      description="Manage company departments."
    >

      <DataTable

        columns={columns}

        data={filteredDepartments}

        loading={loading}

        emptyMessage="No departments found."

        toolbar={

          <DataTableToolbar

            search={search}

            onSearchChange={setSearch}

            addLabel="Add Department"

            onAdd={() =>
              navigate(
                "/company/departments/create"
              )
            }

            onExport={
              exportDepartments
            }

          >

            {/* ======================================
                STATUS FILTER
            ====================================== */}

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

            {/* ==========================================
          DELETE DIALOG
      ========================================== */}

      <ConfirmDialog
        open={
          selectedDepartment !==
          null
        }
        title="Delete Department"
        description={`Are you sure you want to delete "${selectedDepartment?.name}"? This action cannot be undone.`}
        confirmText="Delete Department"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() =>
          setSelectedDepartment(
            null
          )
        }
      />

    </AppShell>

  );

}