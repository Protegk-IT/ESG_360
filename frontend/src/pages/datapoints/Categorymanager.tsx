import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useSearchParams } from "react-router-dom";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { getApiErrorMessage } from "@/services/errors";
import type { ColumnDef } from "@tanstack/react-table";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import {
  MoreHorizontal,
  Pencil,
  Trash2,
  Loader2,
} from "lucide-react";

import DatapointApi from "@/api/datapoints/DatapointApi";
import ModuleApi from "@/api/modules/ModuleApi";

import type {
  DatapointCategory,
  ESGPillar,
  Module,
} from "@/types/datapoint";

/* ============================================================
   ESG PILLAR OPTIONS
   ------------------------------------------------------------
   Backend: esg_pillar = models.CharField(choices=ESGPillar.choices,
   blank=True, null=True) — optional, so the form treats "none"
   as null the same way UnitManager treats an unset unit_family.
============================================================ */

const ESG_PILLAR_OPTIONS: { value: ESGPillar; label: string }[] = [
  { value: "E", label: "Environmental" },
  { value: "S", label: "Social" },
  { value: "G", label: "Governance" },
];

/* ============================================================
   ZOD SCHEMA
============================================================ */

const categorySchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "Code is required."),

  name: z
    .string()
    .trim()
    .min(1, "Name is required."),

  description: z
    .string()
    .trim(),

  module: z
    .string()
    .min(1, "Module is required."),

  esg_pillar: z
    .enum(["E", "S", "G"])
    .nullable(),

  display_order: z
    .number()
    .int("Display order must be a whole number.")
    .min(0, "Display order cannot be negative."),

  is_active: z.boolean(),
});

type CategoryFormValues = z.infer<typeof categorySchema>;

/* ============================================================
   DEFAULT VALUES
============================================================ */

const defaultValues: CategoryFormValues = {
  code: "",
  name: "",
  description: "",
  module: "",
  esg_pillar: null,
  display_order: 0,
  is_active: true,
};

/* ============================================================
   COMPONENT
============================================================ */

export default function CategoryManager() {
  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams();

  const moduleParam = searchParams.get("module");

  /* ==========================================================
     STATE
  ========================================================== */

  const [categories, setCategories] =
    useState<DatapointCategory[]>([]);

  const [modules, setModules] =
    useState<Module[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [search, setSearch] =
    useState("");

  const [moduleFilter, setModuleFilter] =
    useState<string>(
      moduleParam ?? "All",
    );

  const [statusFilter, setStatusFilter] =
    useState<"All" | "Active" | "Inactive">(
      "All",
    );

  const [dialogOpen, setDialogOpen] =
    useState(false);

  const [editingCategory, setEditingCategory] =
    useState<DatapointCategory | null>(null);

  const [submitting, setSubmitting] =
    useState(false);

  const [deleteTarget, setDeleteTarget] =
    useState<DatapointCategory | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  /* ==========================================================
     FORM
  ========================================================== */

  const form = useForm<CategoryFormValues>({
    resolver: zodResolver(categorySchema),
    defaultValues,
    mode: "onSubmit",
  });

  /* ==========================================================
     LOAD DATA
  ========================================================== */

  const loadAll = useCallback(
    async () => {
      try {
        setLoading(true);

        const [
          categoriesResponse,
          modulesResponse,
        ] = await Promise.all([
          DatapointApi.getCategories(),
          ModuleApi.getEnabled(),
        ]);

        setCategories(categoriesResponse.data);
        setModules(modulesResponse.data);
      } catch (error) {
        getApiErrorMessage(
          error,
          "Failed to load categories. Please try again.",
        );

        setCategories([]);
        setModules([]);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      if (ignore) return;

      await loadAll();
    };

    void load();

    return () => {
      ignore = true;
    };
  }, [loadAll]);

  /* ==========================================================
     MODULE NAME MAP
     ----------------------------------------------------------
     DatapointCategory.module is a Module *code* (the FK uses
     to_field="code"), so lookups key off code, not id.
  ========================================================== */

  const moduleNameMap = useMemo(
    () =>
      new Map(
        modules.map((module) => [
          module.code,
          module.name,
        ]),
      ),
    [modules],
  );

  /* ==========================================================
     FILTER + SEARCH
  ========================================================== */

  const filteredCategories = useMemo(() => {
    const keyword = search
      .trim()
      .toLowerCase();

    return categories.filter((category) => {
      /* ------------------------------------------------------
         SEARCH
      ------------------------------------------------------ */

      const moduleName =
        moduleNameMap.get(category.module) ?? "";

      const matchesSearch =
        keyword === "" ||
        category.code
          .toLowerCase()
          .includes(keyword) ||
        category.name
          .toLowerCase()
          .includes(keyword) ||
        category.description
          .toLowerCase()
          .includes(keyword) ||
        moduleName
          .toLowerCase()
          .includes(keyword);

      /* ------------------------------------------------------
         MODULE FILTER
      ------------------------------------------------------ */

      const matchesModule =
        moduleFilter === "All" ||
        category.module === moduleFilter;

      /* ------------------------------------------------------
         STATUS FILTER
      ------------------------------------------------------ */

      const matchesStatus =
        statusFilter === "All" ||
        (statusFilter === "Active" &&
          category.is_active) ||
        (statusFilter === "Inactive" &&
          !category.is_active);

      return (
        matchesSearch &&
        matchesModule &&
        matchesStatus
      );
    });
  }, [
    categories,
    search,
    moduleFilter,
    statusFilter,
    moduleNameMap,
  ]);

  /* ==========================================================
     FILTER STATE
  ========================================================== */

  const hasFilters =
    search.trim() !== "" ||
    moduleFilter !== "All" ||
    statusFilter !== "All";

  /* ==========================================================
     CLEAR FILTERS
  ========================================================== */

  const clearFilters = useCallback(() => {
    setSearch("");
    setModuleFilter("All");
    setStatusFilter("All");

    const params = new URLSearchParams(
      searchParams,
    );

    params.delete("module");

    setSearchParams(
      params,
      {
        replace: true,
      },
    );
  }, [
    searchParams,
    setSearchParams,
  ]);

  /* ==========================================================
     MODULE FILTER CHANGE
  ========================================================== */

  const handleModuleChange = useCallback(
    (value: string) => {
      setModuleFilter(value);

      const params = new URLSearchParams(
        searchParams,
      );

      if (value === "All") {
        params.delete("module");
      } else {
        params.set("module", value);
      }

      setSearchParams(
        params,
        {
          replace: true,
        },
      );
    },
    [
      searchParams,
      setSearchParams,
    ],
  );

  /* ==========================================================
     CREATE
  ========================================================== */

  const openCreateDialog = useCallback(() => {
    setEditingCategory(null);

    form.reset({
      ...defaultValues,

      module:
        moduleFilter !== "All"
          ? moduleFilter
          : "",
    });

    setDialogOpen(true);
  }, [
    form,
    moduleFilter,
  ]);

  /* ==========================================================
     EDIT
  ========================================================== */

  const openEditDialog = useCallback(
    (category: DatapointCategory) => {
      setEditingCategory(category);

      form.reset({
        code: category.code,

        name: category.name,

        description: category.description,

        module: category.module,

        esg_pillar:
          category.esg_pillar ?? null,

        display_order:
          category.display_order,

        is_active:
          category.is_active,
      });

      setDialogOpen(true);
    },
    [form],
  );

  /* ==========================================================
     SUBMIT
  ========================================================== */

  const onSubmit = async (
    values: CategoryFormValues,
  ) => {
    setSubmitting(true);

    try {
      const payload = {
        code: values.code.trim(),

        name: values.name.trim(),

        description: values.description.trim(),

        module: values.module,

        esg_pillar: values.esg_pillar,

        display_order: values.display_order,

        is_active: values.is_active,
      };

      if (editingCategory) {
        await DatapointApi.updateCategory(
          editingCategory.id,
          payload,
        );

        toast.success(
          "Category updated successfully.",
        );
      } else {
        await DatapointApi.createCategory(
          payload,
        );

        toast.success(
          "Category created successfully.",
        );
      }

      setDialogOpen(false);

      setEditingCategory(null);

      form.reset(defaultValues);

      await loadAll();
    } catch (error) {
      getApiErrorMessage(
        error,
        "Failed to save category. Please check the form and try again.",
       
      );
    } finally {
      setSubmitting(false);
    }
  };

  /* ==========================================================
     DELETE
  ========================================================== */

  const confirmDelete = async () => {
    if (!deleteTarget) {
      return;
    }

    setDeleting(true);

    try {
      await DatapointApi.deleteCategory(
        deleteTarget.id,
      );

      toast.success(
        "Category deleted successfully.",
      );

      setDeleteTarget(null);

      await loadAll();
    } catch (error) {
      getApiErrorMessage(
        error,
        "Failed to delete category. It may still be in use by existing datapoints.",
      );
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */

  const columns = useMemo<
    ColumnDef<DatapointCategory>[]
  >(
    () => [
      /* ------------------------------------------------------
         CODE
      ------------------------------------------------------ */

      {
        accessorKey: "code",

        header: "Code",

        cell: ({ row }) => (
          <span className="font-mono text-sm">
            {row.original.code}
          </span>
        ),
      },

      /* ------------------------------------------------------
         NAME
      ------------------------------------------------------ */

      {
        accessorKey: "name",

        header: "Name",

        cell: ({ row }) => (
          <span className="font-medium">
            {row.original.name}
          </span>
        ),
      },

      /* ------------------------------------------------------
         MODULE
      ------------------------------------------------------ */

      {
        id: "module",

        header: "Module",

        cell: ({ row }) => (
          <span>
            {moduleNameMap.get(
              row.original.module,
            ) ?? "-"}
          </span>
        ),
      },

      /* ------------------------------------------------------
         ESG PILLAR
      ------------------------------------------------------ */

      {
        id: "esg_pillar",

        header: "ESG Pillar",

        cell: ({ row }) =>
          row.original.esg_pillar ? (
            <Badge variant="outline">
              {row.original.esg_pillar}
            </Badge>
          ) : (
            <span className="text-muted-foreground">-</span>
          ),
      },

      /* ------------------------------------------------------
         DISPLAY ORDER
      ------------------------------------------------------ */

      {
        accessorKey: "display_order",

        header: "Order",

        cell: ({ row }) => (
          <span className="tabular-nums">
            {row.original.display_order}
          </span>
        ),
      },

      /* ------------------------------------------------------
         STATUS
      ------------------------------------------------------ */

      {
        id: "status",

        header: "Status",

        cell: ({ row }) => (
          <Badge
            variant={
              row.original.is_active
                ? "success"
                : "secondary"
            }
          >
            {row.original.is_active
              ? "Active"
              : "Inactive"}
          </Badge>
        ),
      },

      /* ------------------------------------------------------
         ACTIONS
      ------------------------------------------------------ */

      {
        id: "actions",

        header: () => (
          <div className="text-center">
            Actions
          </div>
        ),

        enableSorting: false,
        enableHiding: false,

        cell: ({ row }) => (
          <div className="flex justify-center">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Actions for ${row.original.name}`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>

              <DropdownMenuContent align="end">
                {/* Edit */}
                <DropdownMenuItem
                  onClick={() =>
                    openEditDialog(row.original)
                  }
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>

                {/* Delete */}
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() =>
                    setDeleteTarget(row.original)
                  }
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [
      moduleNameMap,
      openEditDialog,
    ],
  );

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title="Datapoint Categories"
      description="Browse and manage the categories datapoints are grouped under."
    >
      <div className="mt-6">
        <DataTable
          columns={columns}
          data={filteredCategories}
          loading={loading}
          emptyMessage={
            hasFilters
              ? "No categories match the selected search or filter."
              : "No categories found."
          }
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
              addLabel="Add Category"
              onAdd={openCreateDialog}
            >
              {/* ==================================================
                  MODULE FILTER
              ================================================== */}

              <Select
                value={moduleFilter}
                onValueChange={
                  handleModuleChange
                }
              >
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="Filter by module" />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="All">
                    All Modules
                  </SelectItem>

                  {modules.map((module) => (
                    <SelectItem
                      key={module.code}
                      value={module.code}
                    >
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
                onValueChange={(value) =>
                  setStatusFilter(
                    value as
                      | "All"
                      | "Active"
                      | "Inactive",
                  )
                }
              >
                <SelectTrigger className="w-36">
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

              {/* ==================================================
                  CLEAR FILTERS
              ================================================== */}

              {hasFilters && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={clearFilters}
                >
                  Clear
                </Button>
              )}
            </DataTableToolbar>
          }
        />
      </div>

      {/* ==========================================================
          CREATE / EDIT DIALOG
      ========================================================== */}

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);

          if (!open) {
            setEditingCategory(null);
            form.reset(defaultValues);
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingCategory
                ? "Edit Category"
                : "Add Category"}
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(
                onSubmit,
              )}
              noValidate
              className="space-y-5"
            >
              {/* ==================================================
                  MODULE
              ================================================== */}

              <FormField
                control={form.control}
                name="module"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Module
                    </FormLabel>

                    <Select
                      value={field.value}
                      onValueChange={
                        field.onChange
                      }
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select module" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {modules.map(
                          (module) => (
                            <SelectItem
                              key={module.code}
                              value={module.code}
                            >
                              {module.name}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>

                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ==================================================
                  CODE + NAME
              ================================================== */}

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Code
                      </FormLabel>

                      <FormControl>
                        <Input
                          placeholder="emissions"
                          {...field}
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Name
                      </FormLabel>

                      <FormControl>
                        <Input
                          placeholder="Emissions"
                          {...field}
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* ==================================================
                  DESCRIPTION
              ================================================== */}

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Description
                    </FormLabel>

                    <FormControl>
                      <Textarea
                        rows={3}
                        placeholder="What this category covers."
                        {...field}
                      />
                    </FormControl>

                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ==================================================
                  ESG PILLAR + DISPLAY ORDER
              ================================================== */}

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="esg_pillar"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        ESG Pillar
                      </FormLabel>

                      <Select
                        value={field.value ?? "none"}
                        onValueChange={(value) =>
                          field.onChange(
                            value === "none"
                              ? null
                              : (value as ESGPillar),
                          )
                        }
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select pillar" />
                          </SelectTrigger>
                        </FormControl>

                        <SelectContent>
                          <SelectItem value="none">
                            None
                          </SelectItem>

                          {ESG_PILLAR_OPTIONS.map(
                            (option) => (
                              <SelectItem
                                key={option.value}
                                value={option.value}
                              >
                                {option.label}
                              </SelectItem>
                            ),
                          )}
                        </SelectContent>
                      </Select>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="display_order"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Display Order
                      </FormLabel>

                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          {...field}
                          onChange={(event) =>
                            field.onChange(
                              event.target
                                .value === ""
                                ? 0
                                : Number(
                                    event.target
                                      .value,
                                  ),
                            )
                          }
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* ==================================================
                  STATUS
              ================================================== */}

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={
                          field.value
                        }
                        onCheckedChange={(
                          checked,
                        ) =>
                          field.onChange(
                            checked === true,
                          )
                        }
                      />
                    </FormControl>

                    <FormLabel className="font-normal">
                      Active
                    </FormLabel>
                  </FormItem>
                )}
              />

              {/* ==================================================
                  ACTIONS
              ================================================== */}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    setDialogOpen(false)
                  }
                  disabled={submitting}
                >
                  Cancel
                </Button>

                <Button
                  type="submit"
                  disabled={submitting}
                >
                  {submitting && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}

                  {editingCategory
                    ? "Save Changes"
                    : "Create Category"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ==========================================================
          DELETE CONFIRMATION
      ========================================================== */}

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete category?
            </AlertDialogTitle>

            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">
                {deleteTarget?.name}
              </span>
              . Datapoints referencing this
              category may be affected. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogFooter>
            <AlertDialogCancel
              disabled={deleting}
            >
              Cancel
            </AlertDialogCancel>

            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmDelete();
              }}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}

              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}