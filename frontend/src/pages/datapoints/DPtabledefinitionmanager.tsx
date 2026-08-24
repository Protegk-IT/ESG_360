import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { getApiErrorMessage } from "@/services/errors";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

import { Loader2, Plus, Pencil, Trash2, ChevronLeft } from "lucide-react";

import DatapointApi from "@/api/datapoints/DatapointApi";
import { ValidationMetadataFields } from "@/pages/datapoints/ValidationMetadataFields";
import type {
  DatapointDetail,
  DatapointTableColumn,
  DatapointTableColumnFormData,
  DatapointTableRow,
  DatapointTableRowFormData,
  DatapointDataType,
  ValidationMetadata,
  UnitFamily,
  Unit,
} from "@/types/datapoint";

/* ============================================================
   DATA TYPE OPTIONS
   ------------------------------------------------------------
   Table columns support every scalar data type except TABLE
   itself (a table column can't nest another table).
============================================================ */

const COLUMN_DATA_TYPE_OPTIONS = [
  { value: "DECIMAL", label: "Decimal" },
  { value: "INTEGER", label: "Integer" },
  { value: "TEXT", label: "Text" },
  { value: "LONG_TEXT", label: "Long Text" },
  { value: "BOOLEAN", label: "Boolean" },
  { value: "DATE", label: "Date" },
] as const satisfies readonly { value: string; label: string }[];

const COLUMN_DATA_TYPE_VALUES = COLUMN_DATA_TYPE_OPTIONS.map(
  (o) => o.value
) as [
  (typeof COLUMN_DATA_TYPE_OPTIONS)[number]["value"],
  ...(typeof COLUMN_DATA_TYPE_OPTIONS)[number]["value"][],
];

/* ============================================================
   ZOD SCHEMAS
   ------------------------------------------------------------
   validation_metadata is a structured ValidationMetadata object
   now, built and edited entirely through ValidationMetadataFields
   (a plain-language rule builder) rather than typed as raw JSON.
   There's nothing for zod to check here beyond "it's an object" —
   ValidationMetadataFields only ever writes known, well-typed keys,
   so the per-field constraints (numbers, valid regex, etc.) are
   already enforced at the point of entry.
============================================================ */

const columnSchema = z.object({
  code: z.string().trim().min(1, "Code is required."),
  label: z.string().trim().min(1, "Label is required."),
  data_type: z.enum(COLUMN_DATA_TYPE_VALUES),
  unit_family: z.string().nullable(),
  default_unit: z.string().nullable(),
  is_required: z.boolean(),
  validation_metadata: z.custom<ValidationMetadata>(
    (val) => typeof val === "object" && val !== null
  ),
  display_order: z
    .number()
    .int("Display order must be a whole number.")
    .min(0, "Display order cannot be negative."),
});

type ColumnFormValues = z.infer<typeof columnSchema>;

const columnDefaultValues: ColumnFormValues = {
  code: "",
  label: "",
  data_type: "TEXT",
  unit_family: null,
  default_unit: null,
  is_required: false,
  validation_metadata: {},
  display_order: 0,
};

const rowSchema = z.object({
  code: z.string().trim().min(1, "Code is required."),
  label: z.string().trim().min(1, "Label is required."),
  display_order: z
    .number()
    .int("Display order must be a whole number.")
    .min(0, "Display order cannot be negative."),
});

type RowFormValues = z.infer<typeof rowSchema>;

const rowDefaultValues: RowFormValues = {
  code: "",
  label: "",
  display_order: 0,
};

/* ============================================================
   COMPONENT
   ------------------------------------------------------------
   Route: /datapoints/:id/table-definition
   Only meaningful for datapoints with data_type === "TABLE".
============================================================ */

export default function DatapointTableDefinitionManager() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [datapoint, setDatapoint] = useState<DatapointDetail | null>(null);
  const [columns, setColumns] = useState<DatapointTableColumn[]>([]);
  const [rows, setRows] = useState<DatapointTableRow[]>([]);
  const [unitFamilies, setUnitFamilies] = useState<UnitFamily[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [unitsFamilyId, setUnitsFamilyId] = useState<string | null>(null);
  const [loadingUnits, setLoadingUnits] = useState(false);
  const [loading, setLoading] = useState(true);

  /* ---- column dialog state ---- */
  const [columnDialogOpen, setColumnDialogOpen] = useState(false);
  const [editingColumn, setEditingColumn] =
    useState<DatapointTableColumn | null>(null);
  const [submittingColumn, setSubmittingColumn] = useState(false);
  const [deleteColumnTarget, setDeleteColumnTarget] =
    useState<DatapointTableColumn | null>(null);
  const [deletingColumn, setDeletingColumn] = useState(false);

  /* ---- row dialog state ---- */
  const [rowDialogOpen, setRowDialogOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<DatapointTableRow | null>(
    null
  );
  const [submittingRow, setSubmittingRow] = useState(false);
  const [deleteRowTarget, setDeleteRowTarget] =
    useState<DatapointTableRow | null>(null);
  const [deletingRow, setDeletingRow] = useState(false);

  const columnForm = useForm<ColumnFormValues>({
    resolver: zodResolver(columnSchema),
    defaultValues: columnDefaultValues,
    mode: "onSubmit",
  });

  const rowForm = useForm<RowFormValues>({
    resolver: zodResolver(rowSchema),
    defaultValues: rowDefaultValues,
    mode: "onSubmit",
  });

  const selectedUnitFamily = useWatch({
    control: columnForm.control,
    name: "unit_family",
  });

  // Drives which set of rule fields ValidationMetadataFields renders —
  // changing data_type mid-edit should change the rule builder in place.
  const selectedDataType = useWatch({
    control: columnForm.control,
    name: "data_type",
  });

  /* ==========================================================
     LOAD
  ========================================================== */

  const loadAll = async () => {
    if (!id) return;

    try {
      setLoading(true);

      const [datapointRes, columnsRes, rowsRes, unitFamiliesRes] =
        await Promise.all([
          DatapointApi.getById(id),
          DatapointApi.getTableColumns(id),
          DatapointApi.getTableRows(id),
          DatapointApi.getUnitFamilies(),
        ]);

      setDatapoint(datapointRes.data);
      setColumns(
        [...columnsRes.data].sort((a, b) => a.display_order - b.display_order)
      );
      setRows(
        [...rowsRes.data].sort((a, b) => a.display_order - b.display_order)
      );
      setUnitFamilies(unitFamiliesRes.data);
    } catch (error) {
      console.error("Failed to load table definition:", error);
      toast.error("Failed to load table definition. Please try again.");
      setColumns([]);
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    queueMicrotask(() => {
      if (!ignore) void loadAll();
    });

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!selectedUnitFamily) return;

    let cancelled = false;

    const loadUnits = async () => {
      try {
        setLoadingUnits(true);
        const response = await DatapointApi.getUnitsByFamily(
          selectedUnitFamily
        );
        if (!cancelled) {
          setUnits(response.data);
          setUnitsFamilyId(selectedUnitFamily);
        }
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load units:", error);
        setUnits([]);
        setUnitsFamilyId(selectedUnitFamily);
        toast.error("Failed to load units for the selected unit family.");
      } finally {
        if (!cancelled) setLoadingUnits(false);
      }
    };

    queueMicrotask(() => {
      if (!cancelled) void loadUnits();
    });

    return () => {
      cancelled = true;
    };
  }, [selectedUnitFamily]);

  const displayedUnits =
    selectedUnitFamily && unitsFamilyId === selectedUnitFamily ? units : [];

  /* ==========================================================
     COLUMN DIALOG HELPERS
  ========================================================== */

  const openCreateColumn = () => {
    setEditingColumn(null);
    columnForm.reset({
      ...columnDefaultValues,
      display_order: columns.length,
    });
    setColumnDialogOpen(true);
  };

  const openEditColumn = (column: DatapointTableColumn) => {
    setEditingColumn(column);
    columnForm.reset({
      code: column.code,
      label: column.label,
      data_type: column.data_type as (typeof COLUMN_DATA_TYPE_VALUES)[number],
      unit_family: column.unit_family,
      default_unit: column.default_unit,
      is_required: column.is_required,
      validation_metadata: column.validation_metadata ?? {},
      display_order: column.display_order,
    });
    setColumnDialogOpen(true);
  };

  const onSubmitColumn = async (values: ColumnFormValues) => {
    if (!id) return;

    setSubmittingColumn(true);

    try {
      const payload: DatapointTableColumnFormData = {
        datapoint: id,
        code: values.code.trim(),
        label: values.label.trim(),
        data_type: values.data_type as DatapointDataType,
        unit_family: values.unit_family || null,
        default_unit: values.default_unit || null,
        is_required: values.is_required,
        validation_metadata: values.validation_metadata ?? {},
        display_order: values.display_order,
      };

      if (editingColumn) {
        await DatapointApi.updateTableColumn(editingColumn.id, payload);
        toast.success("Column updated successfully.");
      } else {
        await DatapointApi.createTableColumn(payload);
        toast.success("Column created successfully.");
      }

      setColumnDialogOpen(false);
      await loadAll();
    } catch (error) {
      console.error("Failed to save column:", error);
      toast.error(
        getApiErrorMessage(
          error,
          "Failed to save column. Please check the form and try again."
        )
      );
    } finally {
      setSubmittingColumn(false);
    }
  };

  const confirmDeleteColumn = async () => {
    if (!deleteColumnTarget) return;

    setDeletingColumn(true);

    try {
      await DatapointApi.deleteTableColumn(deleteColumnTarget.id);
      toast.success("Column deleted.");
      setDeleteColumnTarget(null);
      await loadAll();
    } catch (error) {
      console.error("Failed to delete column:", error);
      toast.error("Failed to delete column. Please try again.");
    } finally {
      setDeletingColumn(false);
    }
  };

  /* ==========================================================
     ROW DIALOG HELPERS
  ========================================================== */

  const openCreateRow = () => {
    setEditingRow(null);
    rowForm.reset({ ...rowDefaultValues, display_order: rows.length });
    setRowDialogOpen(true);
  };

  const openEditRow = (row: DatapointTableRow) => {
    setEditingRow(row);
    rowForm.reset({
      code: row.code,
      label: row.label,
      display_order: row.display_order,
    });
    setRowDialogOpen(true);
  };

  const onSubmitRow = async (values: RowFormValues) => {
    if (!id) return;

    setSubmittingRow(true);

    try {
      const payload: DatapointTableRowFormData = {
        datapoint: id,
        code: values.code.trim(),
        label: values.label.trim(),
        display_order: values.display_order,
      };

      if (editingRow) {
        await DatapointApi.updateTableRow(editingRow.id, payload);
        toast.success("Row updated successfully.");
      } else {
        await DatapointApi.createTableRow(payload);
        toast.success("Row created successfully.");
      }

      setRowDialogOpen(false);
      await loadAll();
    } catch (error) {
      console.error("Failed to save row:", error);
      toast.error(
        getApiErrorMessage(
          error,
          "Failed to save row. Please check the form and try again."
        )
      );
    } finally {
      setSubmittingRow(false);
    }
  };

  const confirmDeleteRow = async () => {
    if (!deleteRowTarget) return;

    setDeletingRow(true);

    try {
      await DatapointApi.deleteTableRow(deleteRowTarget.id);
      toast.success("Row deleted.");
      setDeleteRowTarget(null);
      await loadAll();
    } catch (error) {
      console.error("Failed to delete row:", error);
      toast.error("Failed to delete row. Please try again.");
    } finally {
      setDeletingRow(false);
    }
  };

  /* ==========================================================
     RENDER
  ========================================================== */

  const dataTypeLabel = (value: string) =>
    COLUMN_DATA_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;

  return (
    <AppShell
      title={
        datapoint ? `Table Definition — ${datapoint.label}` : "Table Definition"
      }
      description="Manage the columns and rows collected for this TABLE datapoint."
    >
      <div className="mt-6 space-y-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/datapoints/${id}`)}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back to datapoint
        </Button>

        {/* ==================================================
            COLUMNS
        ================================================== */}

        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between px-6 py-5">
            <CardTitle>Columns</CardTitle>
            <Button onClick={openCreateColumn} disabled={!id || loading} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Column
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex min-h-32 items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : columns.length === 0 ? (
              <div className="flex min-h-32 items-center justify-center p-8 text-sm text-muted-foreground">
                No columns defined yet.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Order</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead>Data Type</TableHead>
                    <TableHead className="w-24">Required</TableHead>
                    <TableHead className="w-28 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {columns.map((column) => (
                    <TableRow key={column.id}>
                      <TableCell className="text-muted-foreground">
                        {column.display_order}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {column.code}
                      </TableCell>
                      <TableCell>{column.label}</TableCell>
                      <TableCell>{dataTypeLabel(column.data_type)}</TableCell>
                      <TableCell>{column.is_required ? "Yes" : "No"}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditColumn(column)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteColumnTarget(column)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* ==================================================
            ROWS
        ================================================== */}

        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between px-6 py-5">
            <CardTitle>Rows</CardTitle>
            <Button onClick={openCreateRow} disabled={!id || loading} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Row
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex min-h-32 items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : rows.length === 0 ? (
              <div className="flex min-h-32 items-center justify-center p-8 text-sm text-muted-foreground">
                No rows defined yet.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Order</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead className="w-28 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="text-muted-foreground">
                        {row.display_order}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {row.code}
                      </TableCell>
                      <TableCell>{row.label}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditRow(row)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteRowTarget(row)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ==================================================
          COLUMN CREATE / EDIT DIALOG
      ================================================== */}

      <Dialog open={columnDialogOpen} onOpenChange={setColumnDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingColumn ? "Edit Column" : "Add Column"}
            </DialogTitle>
          </DialogHeader>

          <Form {...columnForm}>
            <form
              onSubmit={columnForm.handleSubmit(onSubmitColumn)}
              noValidate
              className="space-y-4"
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={columnForm.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Code</FormLabel>
                      <FormControl>
                        <Input placeholder="fuel_quantity" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={columnForm.control}
                  name="label"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Label</FormLabel>
                      <FormControl>
                        <Input placeholder="Fuel Quantity" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={columnForm.control}
                  name="data_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Data Type</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={(value) => {
                          field.onChange(value);
                          // Rule shapes differ per data type (e.g. min/max vs
                          // min_length/max_length) — stale rules from the
                          // previous type would silently persist otherwise.
                          columnForm.setValue("validation_metadata", {}, {
                            shouldDirty: true,
                          });
                        }}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {COLUMN_DATA_TYPE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={columnForm.control}
                  name="display_order"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Display Order</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          {...field}
                          onChange={(event) =>
                            field.onChange(
                              event.target.value === ""
                                ? 0
                                : Number(event.target.value)
                            )
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={columnForm.control}
                  name="unit_family"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Unit Family</FormLabel>
                      <Select
                        value={field.value ?? "none"}
                        onValueChange={(value) => {
                          field.onChange(value === "none" ? null : value);
                          columnForm.setValue("default_unit", null, {
                            shouldDirty: true,
                          });
                        }}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select unit family" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {unitFamilies.map((family) => (
                            <SelectItem key={family.id} value={String(family.id)}>
                              {family.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={columnForm.control}
                  name="default_unit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Default Unit</FormLabel>
                      <Select
                        value={field.value ?? "none"}
                        onValueChange={(value) =>
                          field.onChange(value === "none" ? null : value)
                        }
                        disabled={!selectedUnitFamily || loadingUnits}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue
                              placeholder={
                                !selectedUnitFamily
                                  ? "Select a unit family first"
                                  : loadingUnits
                                    ? "Loading units..."
                                    : "Select default unit"
                              }
                            />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {displayedUnits.map((unit) => (
                            <SelectItem key={unit.id} value={String(unit.id)}>
                              {unit.name} ({unit.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Structured rule builder — replaces the old raw-JSON
                  textarea. Shape shown depends on the selected data_type
                  (see ValidationMetadataFields for per-type field sets). */}
              <FormField
                control={columnForm.control}
                name="validation_metadata"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <ValidationMetadataFields
                        dataType={selectedDataType}
                        value={field.value}
                        onChange={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={columnForm.control}
                name="is_required"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={(checked) =>
                          field.onChange(checked === true)
                        }
                      />
                    </FormControl>
                    <FormLabel className="font-normal">
                      Required column
                    </FormLabel>
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setColumnDialogOpen(false)}
                  disabled={submittingColumn}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={submittingColumn}>
                  {submittingColumn && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingColumn ? "Save Changes" : "Create Column"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ==================================================
          ROW CREATE / EDIT DIALOG
      ================================================== */}

      <Dialog open={rowDialogOpen} onOpenChange={setRowDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingRow ? "Edit Row" : "Add Row"}</DialogTitle>
          </DialogHeader>

          <Form {...rowForm}>
            <form
              onSubmit={rowForm.handleSubmit(onSubmitRow)}
              noValidate
              className="space-y-4"
            >
              <FormField
                control={rowForm.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code</FormLabel>
                    <FormControl>
                      <Input placeholder="diesel_generator" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={rowForm.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Label</FormLabel>
                    <FormControl>
                      <Input placeholder="Diesel Generator" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={rowForm.control}
                name="display_order"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display Order</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        {...field}
                        onChange={(event) =>
                          field.onChange(
                            event.target.value === ""
                              ? 0
                              : Number(event.target.value)
                          )
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setRowDialogOpen(false)}
                  disabled={submittingRow}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={submittingRow}>
                  {submittingRow && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingRow ? "Save Changes" : "Create Row"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ==================================================
          DELETE CONFIRMATIONS
      ================================================== */}

      <AlertDialog
        open={!!deleteColumnTarget}
        onOpenChange={(open) => !open && setDeleteColumnTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete column?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">{deleteColumnTarget?.label}</span>{" "}
              and any data collected under it. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletingColumn}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmDeleteColumn();
              }}
              disabled={deletingColumn}
              className="bg-red-600 hover:bg-red-700"
            >
              {deletingColumn && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={!!deleteRowTarget}
        onOpenChange={(open) => !open && setDeleteRowTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete row?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">{deleteRowTarget?.label}</span>{" "}
              and any data collected under it. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletingRow}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmDeleteRow();
              }}
              disabled={deletingRow}
              className="bg-red-600 hover:bg-red-700"
            >
              {deletingRow && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
