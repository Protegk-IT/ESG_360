import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "@/services/errors";

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

import { Loader2, Pencil, Trash2, ChevronLeft } from "lucide-react";

import DatapointApi from "@/api/datapoints/DatapointApi";
import type { DatapointDetail, DatapointOption } from "@/types/datapoint";

/* ============================================================
   ZOD SCHEMA
============================================================ */

const optionSchema = z.object({
  code: z.string().trim().min(1, "Code is required."),
  label: z.string().trim().min(1, "Label is required."),
  display_order: z
    .number()
    .int("Display order must be a whole number.")
    .min(0, "Display order cannot be negative."),
  is_active: z.boolean(),
});

type OptionFormValues = z.infer<typeof optionSchema>;

const defaultValues: OptionFormValues = {
  code: "",
  label: "",
  display_order: 0,
  is_active: true,
};

/* ============================================================
   COLUMN DEFINITIONS
   ------------------------------------------------------------
   Kept local to this file (mirrors the shape of
   getDatapointColumns in datapoint-columns.tsx) since options
   don't have their own shared columns file yet.
============================================================ */

function getOptionColumns({
  onEdit,
  onDelete,
}: {
  onEdit: (option: DatapointOption) => void;
  onDelete: (option: DatapointOption) => void;
}): ColumnDef<DatapointOption>[] {
  return [
    {
      accessorKey: "display_order",
      header: "Order",
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.display_order}
        </span>
      ),
    },
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.code}</span>
      ),
    },
    {
      accessorKey: "label",
      header: "Label",
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "success" : "secondary"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: () => <div className="flex">Actions</div>,
      cell: ({ row }) => (
        <div className="flex ">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onEdit(row.original)}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(row.original)}
          >
            <Trash2 className="h-4 w-4 text-red-600" />
          </Button>
        </div>
      ),
    },
  ];
}

/* ============================================================
   COMPONENT
   ------------------------------------------------------------
   Route: /datapoints/:id/options
   Only meaningful for datapoints with data_type === "SELECT",
   but the manager doesn't hard-block other types — it just
   reflects whatever the backend allows.
============================================================ */

export default function DatapointOptionsManager() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [datapoint, setDatapoint] = useState<DatapointDetail | null>(null);
  const [options, setOptions] = useState<DatapointOption[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingOption, setEditingOption] = useState<DatapointOption | null>(
    null
  );
  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<DatapointOption | null>(
    null
  );
  const [deleting, setDeleting] = useState(false);

  const form = useForm<OptionFormValues>({
    resolver: zodResolver(optionSchema),
    defaultValues,
    mode: "onSubmit",
  });

  /* ==========================================================
     LOAD
  ========================================================== */

  const loadOptions = async () => {
    if (!id) return;

    try {
      setLoading(true);

      const [datapointResponse, optionsResponse] = await Promise.all([
        DatapointApi.getById(id),
        DatapointApi.getOptions(id),
      ]);

      setDatapoint(datapointResponse.data);
      setOptions(
        [...optionsResponse.data].sort(
          (a, b) => a.display_order - b.display_order
        )
      );
    } catch (error) {
      console.error("Failed to load datapoint options:", error);
      toast.error("Failed to load options. Please try again.");
      setOptions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    // Deferred to a microtask so the loader's first synchronous
    // setState call (setLoading(true)) doesn't execute inside the
    // effect's own synchronous pass — avoids the "setState
    // synchronously within an effect" cascading-render warning.
    queueMicrotask(() => {
      if (!ignore) void loadOptions();
    });

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  /* ==========================================================
     FILTERED OPTIONS (client-side search, matches list pattern)
  ========================================================== */

  const filteredOptions = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (keyword === "") return options;

    return options.filter(
      (option) =>
        option.code.toLowerCase().includes(keyword) ||
        option.label.toLowerCase().includes(keyword)
    );
  }, [options, search]);

  /* ==========================================================
     DIALOG HELPERS
  ========================================================== */

  const openCreateDialog = () => {
    setEditingOption(null);
    form.reset({
      ...defaultValues,
      display_order: options.length,
    });
    setDialogOpen(true);
  };

  const openEditDialog = (option: DatapointOption) => {
    setEditingOption(option);
    form.reset({
      code: option.code,
      label: option.label,
      display_order: option.display_order,
      is_active: option.is_active,
    });
    setDialogOpen(true);
  };

  /* ==========================================================
     SUBMIT (create or update)
  ========================================================== */

  const onSubmit = async (values: OptionFormValues) => {
    if (!id) return;

    setSubmitting(true);

    try {
      const payload = {
        datapoint: id,
        code: values.code.trim(),
        label: values.label.trim(),
        display_order: values.display_order,
        is_active: values.is_active,
      };

      if (editingOption) {
        await DatapointApi.updateOption(editingOption.id, payload);
        toast.success("Option updated successfully.");
      } else {
        await DatapointApi.createOption(payload);
        toast.success("Option created successfully.");
      }

      setDialogOpen(false);
      await loadOptions();
    } catch (error) {
      console.error("Failed to save option:", error);
      toast.error(
        getApiErrorMessage(
          error,
        "Failed to save option. Please check the form and try again."));
    } finally {
      setSubmitting(false);
    }
  };

  /* ==========================================================
     DELETE
  ========================================================== */

  const confirmDelete = async () => {
    if (!deleteTarget) return;

    setDeleting(true);

    try {
      await DatapointApi.deleteOption(deleteTarget.id);
      toast.success("Option deleted.");
      setDeleteTarget(null);
      await loadOptions();
    } catch (error) {
      console.error("Failed to delete option:", error);
      toast.error("Failed to delete option. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
     COLUMNS
  ========================================================== */

  const columns = useMemo(
    () =>
      getOptionColumns({
        onEdit: openEditDialog,
        onDelete: (option) => setDeleteTarget(option),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [options]
  );

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title={datapoint ? `Options — ${datapoint.label}` : "Datapoint Options"}
      description="Manage the selectable values for this SELECT datapoint."
    >
      <div className="mt-6 space-y-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/datapoints/${id}`)}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back to datapoint
        </Button>

        <DataTable
          columns={columns}
          data={filteredOptions}
          loading={loading}
          emptyMessage={
            search
              ? "No options match your search."
              : "No options yet. Add the first one to get started."
          }
          toolbar={
            <DataTableToolbar
              search={search}
              onSearchChange={setSearch}
              addLabel="Add Option"
              onAdd={openCreateDialog}
            />
          }
        />
      </div>

      {/* ==================================================
          CREATE / EDIT DIALOG
      ================================================== */}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingOption ? "Edit Option" : "Add Option"}
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              noValidate
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code</FormLabel>
                    <FormControl>
                      <Input placeholder="grid_connected" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Label</FormLabel>
                    <FormControl>
                      <Input placeholder="Grid Connected" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
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
                control={form.control}
                name="is_active"
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
                    <FormLabel className="font-normal">Active</FormLabel>
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                  disabled={submitting}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editingOption ? "Save Changes" : "Create Option"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ==================================================
          DELETE CONFIRMATION
      ================================================== */}

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete option?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">{deleteTarget?.label}</span> from
              this datapoint&apos;s option list. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmDelete();
              }}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
