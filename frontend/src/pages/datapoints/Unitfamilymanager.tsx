import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { DataTable } from "@/common/DataTable";
import { DataTableToolbar } from "@/common/DataTableToolbar";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
  Loader2,
  Pencil,
  Trash2,
  ChevronRight,
} from "lucide-react";

import DatapointApi from "@/api/datapoints/DatapointApi";
import { getApiErrorMessage } from "@/services/errors";

import type { UnitFamily } from "@/types/datapoint";

/* ============================================================
   ZOD SCHEMA
============================================================ */

const unitFamilySchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "Code is required."),

  name: z
    .string()
    .trim()
    .min(1, "Name is required."),
});

type UnitFamilyFormValues = z.infer<
  typeof unitFamilySchema
>;

/* ============================================================
   DEFAULT VALUES
============================================================ */

const defaultValues: UnitFamilyFormValues = {
  code: "",
  name: "",
};

/* ============================================================
   COMPONENT
============================================================ */

export default function UnitFamilyManager() {
  const navigate = useNavigate();

  /* ==========================================================
     STATE
  ========================================================== */

  const [families, setFamilies] = useState<UnitFamily[]>([]);

  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);

  const [editingFamily, setEditingFamily] =
    useState<UnitFamily | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] =
    useState<UnitFamily | null>(null);

  const [deleting, setDeleting] = useState(false);

  /* ==========================================================
     FORM
  ========================================================== */

  const form = useForm<UnitFamilyFormValues>({
    resolver: zodResolver(unitFamilySchema),

    defaultValues,

    mode: "onSubmit",
  });

  /* ==========================================================
     LOAD UNIT FAMILIES
  ========================================================== */

  const loadFamilies = async () => {
    try {
      setLoading(true);

      const response =
        await DatapointApi.getUnitFamilies();

      setFamilies(response.data);
    } catch (error) {
      console.error(
        "Failed to load unit families:",
        error
      );

      toast.error(
        "Failed to load unit families. Please try again."
      );

      setFamilies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      try {
        setLoading(true);

        const response =
          await DatapointApi.getUnitFamilies();

        if (!ignore) {
          setFamilies(response.data);
        }
      } catch (error) {
        if (!ignore) {
          console.error(
            "Failed to load unit families:",
            error
          );

          toast.error(
            "Failed to load unit families. Please try again."
          );

          setFamilies([]);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      ignore = true;
    };
  }, []);

  /* ==========================================================
     SEARCH
     ----------------------------------------------------------
     Search by:
       - Code
       - Name
  ========================================================== */

  const filteredFamilies = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (!keyword) {
      return families;
    }

    return families.filter((family) => {
      const matchesCode =
        family.code
          .toLowerCase()
          .includes(keyword);

      const matchesName =
        family.name
          .toLowerCase()
          .includes(keyword);

      return matchesCode || matchesName;
    });
  }, [families, search]);

  /* ==========================================================
     DIALOG HELPERS
  ========================================================== */

  const openCreateDialog = () => {
    setEditingFamily(null);

    form.reset(defaultValues);

    setDialogOpen(true);
  };

  const openEditDialog = (
    family: UnitFamily
  ) => {
    setEditingFamily(family);

    form.reset({
      code: family.code,
      name: family.name,
    });

    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (submitting) {
      return;
    }

    setDialogOpen(false);

    setEditingFamily(null);

    form.reset(defaultValues);
  };

  /* ==========================================================
     SUBMIT
  ========================================================== */

  const onSubmit = async (
    values: UnitFamilyFormValues
  ) => {
    setSubmitting(true);

    try {
      const payload = {
        code: values.code.trim(),
        name: values.name.trim(),
      };

      if (editingFamily) {
        await DatapointApi.updateUnitFamily(
          editingFamily.id,
          payload
        );

        toast.success(
          "Unit family updated successfully."
        );
      } else {
        await DatapointApi.createUnitFamily(
          payload
        );

        toast.success(
          "Unit family created successfully."
        );
      }

      setDialogOpen(false);

      setEditingFamily(null);

      form.reset(defaultValues);

      await loadFamilies();
    } catch (error) {
      console.error(
        "Failed to save unit family:",
        error
      );

      toast.error(
        getApiErrorMessage(
        error,
        "Failed to save unit family. Please check the form and try again."
      ));
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
      await DatapointApi.deleteUnitFamily(
        deleteTarget.id
      );

      toast.success(
        "Unit family deleted successfully."
      );

      setDeleteTarget(null);

      await loadFamilies();
    } catch (error) {
      console.error(
        "Failed to delete unit family:",
        error
      );

      toast.error(
        "Failed to delete unit family. It may still be in use by existing units or datapoints."
      );
    } finally {
      setDeleting(false);
    }
  };

  /* ==========================================================
     TABLE COLUMNS
  ========================================================== */
const columns = [
  {
    accessorKey: "code",
    header: "Code",

    cell: ({
      row,
    }: {
      row: {
        original: UnitFamily;
      };
    }) => (
      <span className="font-mono text-sm">
        {row.original.code}
      </span>
    ),
  },

  {
    accessorKey: "name",
    header: "Name",

    cell: ({
      row,
    }: {
      row: {
        original: UnitFamily;
      };
    }) => (
      <span className="text-sm">
        {row.original.name}
      </span>
    ),
  },

{
  id: "actions",
  header: "Actions",
  enableSorting: false,

  cell: ({
    row,
  }: {
    row: {
      original: UnitFamily;
    };
  }) => {
    const family = row.original;

    return (
      <div className="flex justify-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">

            {/* Units */}
            <DropdownMenuItem
              onClick={() =>
                navigate(`/units?family=${family.id}`)
              }
            >
              <ChevronRight className="mr-2 h-4 w-4" />
              Units
            </DropdownMenuItem>

            {/* Edit */}
            <DropdownMenuItem
              onClick={() => openEditDialog(family)}
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>

            {/* Delete */}
            <DropdownMenuItem
              variant="destructive"
              onClick={() => setDeleteTarget(family)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>

          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  },

  meta: {
    className: "w-[100px] text-center",
  },
},
];

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title="Unit Families"
      description="Browse and manage the unit families available for datapoints."
    >
      <DataTable
        columns={columns}
        data={filteredFamilies}
        loading={loading}
        emptyMessage={
          search.trim()
            ? "No unit families match your search."
            : "No unit families found."
        }
        toolbar={
          <DataTableToolbar
            search={search}
            onSearchChange={setSearch}
            addLabel="Add Unit Family"
            onAdd={openCreateDialog}
          />
        }
      />

      {/* ======================================================
          CREATE / EDIT DIALOG
      ====================================================== */}

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            closeDialog();
          } else {
            setDialogOpen(true);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingFamily
                ? "Edit Unit Family"
                : "Add Unit Family"}
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(
                onSubmit
              )}
              noValidate
              className="space-y-6"
            >
              {/* ==================================================
                  CODE
              ================================================== */}

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
                        placeholder="mass"
                        {...field}
                      />
                    </FormControl>

                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ==================================================
                  NAME
              ================================================== */}

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
                        placeholder="Mass"
                        {...field}
                      />
                    </FormControl>

                    <FormMessage />
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
                  onClick={closeDialog}
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

                  {editingFamily
                    ? "Save Changes"
                    : "Create Unit Family"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ======================================================
          DELETE CONFIRMATION
      ====================================================== */}

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open && !deleting) {
            setDeleteTarget(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete unit family?
            </AlertDialogTitle>

            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium">
                {deleteTarget?.name}
              </span>
              . Units belonging to this family
              and datapoints referencing them may
              be affected. This action cannot be
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
              className="bg-red-500 hover:bg-red-700"
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