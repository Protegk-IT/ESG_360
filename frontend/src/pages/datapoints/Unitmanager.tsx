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

import type { ColumnDef } from "@tanstack/react-table";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

import type {
  Unit,
  UnitFamily,
} from "@/types/datapoint";
import { getApiErrorMessage } from "@/services/errors";

/* ============================================================
   ZOD SCHEMA
============================================================ */

const unitSchema = z.object({
  family: z
    .string()
    .min(1, "Unit family is required."),

  code: z
    .string()
    .trim()
    .min(1, "Code is required."),

  name: z
    .string()
    .trim()
    .min(1, "Name is required."),

  factor_to_base: z
    .string()
    .trim()
    .min(1, "Conversion factor is required.")
    .refine(
      (value) => !Number.isNaN(Number(value)),
      "Conversion factor must be a number.",
    ),

  is_base_unit: z.boolean(),

  is_active: z.boolean(),
});

type UnitFormValues = z.infer<typeof unitSchema>;

/* ============================================================
   DEFAULT VALUES
============================================================ */

const defaultValues: UnitFormValues = {
  family: "",
  code: "",
  name: "",
  factor_to_base: "1",
  is_base_unit: false,
  is_active: true,
};

/* ============================================================
   COMPONENT
============================================================ */

export default function UnitManager() {
  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams();

  const familyParam = searchParams.get("family");

  /* ==========================================================
     STATE
  ========================================================== */

  const [units, setUnits] = useState<Unit[]>([]);

  const [families, setFamilies] =
    useState<UnitFamily[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [search, setSearch] =
    useState("");

  const [familyFilter, setFamilyFilter] =
    useState<string>(
      familyParam ?? "All",
    );

  const [dialogOpen, setDialogOpen] =
    useState(false);

  const [editingUnit, setEditingUnit] =
    useState<Unit | null>(null);

  const [submitting, setSubmitting] =
    useState(false);

  const [deleteTarget, setDeleteTarget] =
    useState<Unit | null>(null);

  const [deleting, setDeleting] =
    useState(false);

  /* ==========================================================
     FORM
  ========================================================== */

  const form = useForm<UnitFormValues>({
    resolver: zodResolver(unitSchema),
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
          unitsResponse,
          familiesResponse,
        ] = await Promise.all([
          DatapointApi.getUnits(),
          DatapointApi.getUnitFamilies(),
        ]);

        setUnits(unitsResponse.data);
        setFamilies(familiesResponse.data);
      } catch (error) {
        console.error(
          "Failed to load units:",
          error,
        );

        toast.error(
          "Failed to load units. Please try again.",
        );

        setUnits([]);
        setFamilies([]);
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
     FAMILY NAME MAP
  ========================================================== */

  const familyNameMap = useMemo(
    () =>
      new Map(
        families.map((family) => [
          family.id,
          family.name,
        ]),
      ),
    [families],
  );

  /* ==========================================================
     FILTER + SEARCH
  ========================================================== */

  const filteredUnits = useMemo(() => {
    const keyword = search
      .trim()
      .toLowerCase();

    return units.filter((unit) => {
      /* ------------------------------------------------------
         SEARCH
      ------------------------------------------------------ */

      const familyName =
        familyNameMap.get(unit.family) ?? "";

      const matchesSearch =
        keyword === "" ||
        unit.code
          .toLowerCase()
          .includes(keyword) ||
        unit.name
          .toLowerCase()
          .includes(keyword) ||
        familyName
          .toLowerCase()
          .includes(keyword);

      /* ------------------------------------------------------
         FAMILY FILTER
      ------------------------------------------------------ */

      const matchesFamily =
        familyFilter === "All" ||
        unit.family === familyFilter;

      return (
        matchesSearch &&
        matchesFamily
      );
    });
  }, [
    units,
    search,
    familyFilter,
    familyNameMap,
  ]);

  /* ==========================================================
     FILTER STATE
  ========================================================== */

  const hasFilters =
    search.trim() !== "" ||
    familyFilter !== "All";

  /* ==========================================================
     CLEAR FILTERS
  ========================================================== */

  const clearFilters = useCallback(() => {
    setSearch("");
    setFamilyFilter("All");

    const params = new URLSearchParams(
      searchParams,
    );

    params.delete("family");

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
     FAMILY FILTER CHANGE
  ========================================================== */

  const handleFamilyChange = useCallback(
    (value: string) => {
      setFamilyFilter(value);

      const params = new URLSearchParams(
        searchParams,
      );

      if (value === "All") {
        params.delete("family");
      } else {
        params.set("family", value);
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
    setEditingUnit(null);

    form.reset({
      ...defaultValues,

      family:
        familyFilter !== "All"
          ? familyFilter
          : "",
    });

    setDialogOpen(true);
  }, [
    form,
    familyFilter,
  ]);

  /* ==========================================================
     EDIT
  ========================================================== */

  const openEditDialog = useCallback(
    (unit: Unit) => {
      setEditingUnit(unit);

      form.reset({
        family: unit.family,

        code: unit.code,

        name: unit.name,

        factor_to_base:
          String(unit.factor_to_base),

        is_base_unit:
          unit.is_base_unit,

        is_active:
          unit.is_active,
      });

      setDialogOpen(true);
    },
    [form],
  );
/* ==========================================================
   SUBMIT
========================================================== */

const onSubmit = async (
  values: UnitFormValues,
) => {
  setSubmitting(true);

  try {
    const payload = {
      family: values.family,

      code: values.code.trim(),

      name: values.name.trim(),

      factor_to_base:
        values.factor_to_base.trim(),

      is_base_unit:
        values.is_base_unit,

      is_active:
        values.is_active,
    };

    if (editingUnit) {
      await DatapointApi.updateUnit(
        editingUnit.id,
        payload,
      );

      toast.success(
        "Unit updated successfully.",
      );
    } else {
      await DatapointApi.createUnit(
        payload,
      );

      toast.success(
        "Unit created successfully.",
      );
    }

    setDialogOpen(false);

    setEditingUnit(null);

    form.reset(defaultValues);

    await loadAll();

  } catch (error) {
    console.error(
      "Failed to save unit:",
      error,
    );

    toast.error(
      getApiErrorMessage(
        error,
        "Failed to save unit. Please try again.",
      ),
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
      await DatapointApi.deleteUnit(
        deleteTarget.id,
      );

      toast.success(
        "Unit deleted successfully.",
      );

      setDeleteTarget(null);

      await loadAll();
    } catch (error) {
      console.error(
        "Failed to delete unit:",
        error,
      );

      toast.error(
        "Failed to delete unit. It may still be in use by existing datapoints.",
      );
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */

  const columns = useMemo<
    ColumnDef<Unit>[]
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
         FAMILY
      ------------------------------------------------------ */

      {
        id: "family",

        header: "Family",

        cell: ({ row }) => (
          <span>
            {familyNameMap.get(
              row.original.family,
            ) ?? "-"}
          </span>
        ),
      },

      /* ------------------------------------------------------
         FACTOR TO BASE
      ------------------------------------------------------ */

      {
        accessorKey: "factor_to_base",

        header: "Factor to Base",

        cell: ({ row }) => {
          const factor = Number(
            row.original.factor_to_base,
          );

          return (
            <span className="tabular-nums">
              {Number.isFinite(factor)
                ? factor.toFixed(2)
                : "-"}
            </span>
          );
        },
      },

      /* ------------------------------------------------------
         BASE
      ------------------------------------------------------ */

      {
        id: "base",

        header: "Base",

        cell: ({ row }) =>
          row.original.is_base_unit ? (
            <Badge variant="outline">
              Base
            </Badge>
          ) : null,
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
      familyNameMap,
      openEditDialog,
    ],
  );

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title="Units"
      description="Browse and manage the units available for datapoints."
    >
      <div className="mt-6">
        <DataTable
          columns={columns}
          data={filteredUnits}
          loading={loading}
          emptyMessage={
            hasFilters
              ? "No units match the selected search or filter."
              : "No units found."
          }
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
              addLabel="Add Unit"
              onAdd={openCreateDialog}
            >
              {/* ==================================================
                  UNIT FAMILY FILTER
              ================================================== */}

              <Select
                value={familyFilter}
                onValueChange={
                  handleFamilyChange
                }
              >
                <SelectTrigger className="w-44">
                  <SelectValue placeholder="Filter by family" />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="All">
                    All Unit Families
                  </SelectItem>

                  {families.map((family) => (
                    <SelectItem
                      key={family.id}
                      value={family.id}
                    >
                      {family.name}
                    </SelectItem>
                  ))}
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
            setEditingUnit(null);
            form.reset(defaultValues);
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingUnit
                ? "Edit Unit"
                : "Add Unit"}
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
                  UNIT FAMILY
              ================================================== */}

              <FormField
                control={form.control}
                name="family"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Unit Family
                    </FormLabel>

                    <Select
                      value={field.value}
                      onValueChange={
                        field.onChange
                      }
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select unit family" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {families.map(
                          (family) => (
                            <SelectItem
                              key={family.id}
                              value={family.id}
                            >
                              {family.name}
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
                          placeholder="kg"
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
                          placeholder="Kilogram"
                          {...field}
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* ==================================================
                  FACTOR
              ================================================== */}

              <FormField
                control={form.control}
                name="factor_to_base"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Factor to Base Unit
                    </FormLabel>

                    <FormControl>
                      <Input
                        placeholder="1"
                        inputMode="decimal"
                        {...field}
                      />
                    </FormControl>

                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ==================================================
                  FLAGS
              ================================================== */}

              <div className="flex items-center gap-6">
                <FormField
                  control={form.control}
                  name="is_base_unit"
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
                        Base unit
                      </FormLabel>
                    </FormItem>
                  )}
                />

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
              </div>

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

                  {editingUnit
                    ? "Save Changes"
                    : "Create Unit"}
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
              Delete unit?
            </AlertDialogTitle>

            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">
                {deleteTarget?.name}
              </span>
              . Datapoints referencing this
              unit as their default may be
              affected. This action cannot be
              undone.
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