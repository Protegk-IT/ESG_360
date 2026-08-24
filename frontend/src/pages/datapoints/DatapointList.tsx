import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import type {
  Datapoint,
  DatapointCategory,
  DatapointDataType,
  Module,
} from "@/types/datapoint";

import DatapointApi from "@/api/datapoints/DatapointApi";
import { getDatapointColumns } from "./datapoint-columns";
import ModuleApi from "@/api/modules/ModuleApi";
import { useAuth } from "@/context/AuthContext";

/* ==========================================================
   DATAPOINT LIST
========================================================== */

export default function DatapointList() {
  const navigate = useNavigate();
  const { user, permissions } = useAuth();
  const canManage = Boolean(
    user?.is_superuser || permissions.includes("datapoint.manage")
  );

  /* ========================================================
     STATE
  ======================================================== */

  const [datapoints, setDatapoints] = useState<Datapoint[]>(
    []
  );

  const [categories, setCategories] = useState<
  DatapointCategory[]
>([]);

  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] = useState<
    "All" | "Active" | "Inactive"
  >("All");

  const [typeFilter, setTypeFilter] = useState<
    "All" | DatapointDataType
  >("All");

  const [categoryFilter, setCategoryFilter] =
    useState("All");
  
  const [moduleFilter, setModuleFilter] = useState("All");
  const [modules, setModules] = useState<Module[]>([]);


  // Load Modules 

  useEffect(() => {
  let ignore = false;

  const loadModules = async () => {
    try {
      const response = await ModuleApi.getEnabled();

      if (!ignore) {
        setModules(response.data);
      }
    } catch (error) {
      if (!ignore) {
        console.error("Failed to load modules:", error);
        setModules([]);
      }
    }
  };

  void loadModules();

  return () => {
    ignore = true;
  };
}, []);

  
  /* ========================================================
     LOAD DATAPOINTS
  ======================================================== */

useEffect(() => {
  let ignore = false;

  const loadData = async () => {
    try {
      setLoading(true);

      const [
        datapointsResponse,
        categoriesResponse,
      ] = await Promise.all([
        DatapointApi.getAll(),
        DatapointApi.getCategories(),
      ]);

      if (!ignore) {
        setDatapoints(
          datapointsResponse.data
        );

        setCategories(
          categoriesResponse.data
        );
      }
    } catch (error) {
      if (!ignore) {
        console.error(
          "Failed to load datapoint catalog:",
          error
        );

        toast.error(
          "Failed to load datapoints. Please try again."
        );

        setDatapoints([]);
        setCategories([]);
      }
    } finally {
      if (!ignore) {
        setLoading(false);
      }
    }
  };

  void loadData();

  return () => {
    ignore = true;
  };
}, []);
  /* ========================================================
     CATEGORY OPTIONS
     
     These are derived from the API data instead of being
     hard-coded.
  ======================================================== */

const categoryOptions = useMemo(
  () => categories,
  [categories]
);

  /* ========================================================
     FILTER DATAPOINTS
  ======================================================== */

  const filteredDatapoints = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    return datapoints.filter((datapoint) => {
      /* ----------------------------------------------------
         SEARCH
      ---------------------------------------------------- */

      const matchesSearch =
        keyword === "" ||
        datapoint.label
          .toLowerCase()
          .includes(keyword) ||
        datapoint.code
          .toLowerCase()
          .includes(keyword) ||
        datapoint.description
          .toLowerCase()
          .includes(keyword);

      /* ----------------------------------------------------
         STATUS
      ---------------------------------------------------- */

      const matchesStatus =
        statusFilter === "All" ||
        (statusFilter === "Active" &&
          datapoint.is_active) ||
        (statusFilter === "Inactive" &&
          !datapoint.is_active);

      /* ----------------------------------------------------
         DATA TYPE
      ---------------------------------------------------- */

      const matchesType =
        typeFilter === "All" ||
        datapoint.data_type === typeFilter;
      
       
      /* ----------------------------------------------------
         CATEGORY
      ---------------------------------------------------- */

      const matchesCategory =
        categoryFilter === "All" ||
        datapoint.category === categoryFilter;

       /* ----------------------------------------------------
               MODULE
              ---------------------------------------------------- */

      const matchesModule =
      moduleFilter === "All" ||
      datapoint.module === moduleFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesType &&
        matchesCategory &&
        matchesModule
      );
    });
  }, [search, datapoints, statusFilter, typeFilter, categoryFilter, moduleFilter]);



  /* ========================================================
     TABLE COLUMNS
  ======================================================== */
const categoryNameMap = useMemo(() => {
  return new Map(
    categories.map((category) => [
      category.id,
      category.name,
    ])
  );
}, [categories]);

const columns = useMemo(
  () =>
    getDatapointColumns({
      onView: (id) => {
        navigate(`/datapoints/${id}`);
      },

      onEdit: (id) => {
        navigate(`/datapoints/${id}/edit`);
      },

      getCategoryName: (categoryId) =>
        categoryNameMap.get(categoryId) ?? "-",

      canManage,
    }),
  [navigate, categoryNameMap, canManage]
);
  /* ========================================================
     RENDER
  ======================================================== */

  return (
    <AppShell
      title="Datapoint Catalog"
      description="Browse and manage ESG datapoint definitions."
    >
      <DataTable
        columns={columns}
        data={filteredDatapoints}
        loading={loading}
        emptyMessage={
          search ||
          statusFilter !== "All" ||
          typeFilter !== "All" ||
          categoryFilter !== "All"
            ? "No datapoints match the selected filters."
            : "No datapoints found."
        }
        toolbar={
                    <DataTableToolbar
            search={search}
            onSearchChange={setSearch}
            addLabel={canManage ? "Add Datapoint" : undefined}
            onAdd={
              canManage
                ? () => {
                    navigate("/datapoints/create");
                  }
                : undefined
            }
          >
          {/* ==================================================
    CATEGORY FILTER
================================================== */}

<Select value={categoryFilter} onValueChange={setCategoryFilter}>
  <SelectTrigger className="h-9 w-34 shrink-0">
    <SelectValue placeholder="Category" />
  </SelectTrigger>

  <SelectContent>
    <SelectItem value="All">Categories</SelectItem>

    {categoryOptions.map((category) => (
      <SelectItem key={category.id} value={category.id}>
        {category.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>

{/* ==================================================
    DATA TYPE FILTER
================================================== */}

<Select
  value={typeFilter}
  onValueChange={(value) => {
    setTypeFilter(value as "All" | DatapointDataType);
  }}
>
  <SelectTrigger className="h-9 w-28 shrink-0">
    <SelectValue placeholder="Data Type" />
  </SelectTrigger>

  <SelectContent>
    <SelectItem value="All">Types</SelectItem>
    <SelectItem value="DECIMAL">Decimal</SelectItem>
    <SelectItem value="INTEGER">Integer</SelectItem>
    <SelectItem value="TEXT">Text</SelectItem>
    <SelectItem value="LONG_TEXT">Long Text</SelectItem>
    <SelectItem value="BOOLEAN">Boolean</SelectItem>
    <SelectItem value="SELECT">Select</SelectItem>
    <SelectItem value="DATE">Date</SelectItem>
    <SelectItem value="TABLE">Table</SelectItem>
  </SelectContent>
</Select>

{/* ==================================================
    MODULE FILTER
================================================== */}

<Select value={moduleFilter} onValueChange={setModuleFilter}>
  <SelectTrigger className="h-9 w-32 shrink-0">
    <SelectValue placeholder="Module" />
  </SelectTrigger>

  <SelectContent>
    <SelectItem value="All"> Modules</SelectItem>

    {modules.map((module) => (
      <SelectItem key={module.code} value={module.code}>
        {module.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>

{/* ==================================================
    STATUS FILTER
================================================== */}

<Select
  value={statusFilter}
  onValueChange={(value) => {
    setStatusFilter(value as "All" | "Active" | "Inactive");
  }}
>
  <SelectTrigger className="h-9 w-26 shrink-0">
    <SelectValue placeholder="Status" />
  </SelectTrigger>

  <SelectContent>
    <SelectItem value="All">Status</SelectItem>
    <SelectItem value="Active">Active</SelectItem>
    <SelectItem value="Inactive">Inactive</SelectItem>
  </SelectContent>
</Select>
          </DataTableToolbar>
        }
      />
    </AppShell>
  );
}
