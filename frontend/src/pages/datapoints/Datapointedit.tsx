import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Loader2, ListChecks, Table2 } from "lucide-react";

import DatapointApi from "@/api/datapoints/DatapointApi";
import ModuleApi from "@/api/modules/ModuleApi";

import type {
  DatapointFormData,
  DatapointCategory,
  UnitFamily,
  Unit,
  Module,
} from "@/types/datapoint";

/* ============================================================
   ENUM OPTIONS — SINGLE SOURCE OF TRUTH
   ------------------------------------------------------------
   Mirrors DatapointCreate.tsx. See the note there: data_type /
   collection_level / frequency are Django `choices=` enums,
   not DB-backed rows, so there's nothing to fetch them from
   yet. Keep these two files' option lists in sync until the
   backend exposes a shared /choices/ endpoint.
============================================================ */

const DATA_TYPE_OPTIONS = [
  { value: "DECIMAL", label: "Decimal" },
  { value: "INTEGER", label: "Integer" },
  { value: "TEXT", label: "Text" },
  { value: "LONG_TEXT", label: "Long Text" },
  { value: "BOOLEAN", label: "Boolean" },
  { value: "SELECT", label: "Select" },
  { value: "DATE", label: "Date" },
  { value: "TABLE", label: "Table" },
] as const satisfies readonly { value: string; label: string }[];

const DATA_TYPE_VALUES = DATA_TYPE_OPTIONS.map((o) => o.value) as [
  (typeof DATA_TYPE_OPTIONS)[number]["value"],
  ...(typeof DATA_TYPE_OPTIONS)[number]["value"][],
];

const COLLECTION_LEVEL_OPTIONS = [
  { value: "COMPANY", label: "Company" },
  { value: "FACILITY", label: "Facility" },
  { value: "ORG_NODE", label: "Org_node" },
] as const satisfies readonly { value: string; label: string }[];

const COLLECTION_LEVEL_VALUES = COLLECTION_LEVEL_OPTIONS.map((o) => o.value) as [
  (typeof COLLECTION_LEVEL_OPTIONS)[number]["value"],
  ...(typeof COLLECTION_LEVEL_OPTIONS)[number]["value"][],
];

const FREQUENCY_OPTIONS = [
  { value: "MONTHLY", label: "Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "ANNUAL", label: "Annual" },
] as const satisfies readonly { value: string; label: string }[];

const FREQUENCY_VALUES = FREQUENCY_OPTIONS.map((o) => o.value) as [
  (typeof FREQUENCY_OPTIONS)[number]["value"],
  ...(typeof FREQUENCY_OPTIONS)[number]["value"][],
];

/* ============================================================
   ZOD SCHEMA
   ------------------------------------------------------------
   Same shape as create. `code` stays editable — if your
   backend treats code as immutable after creation, disable
   the field in the form below rather than dropping it from
   the schema, so the payload shape stays consistent.
============================================================ */

const datapointSchema = z.object({
  code: z.string().trim().min(1, "Code is required."),
  category: z.string().min(1, "Category is required."),
  module: z.string().min(1, "Module is required."),
  label: z.string().trim().min(1, "Label is required."),
  description: z.string().trim().min(1, "Description is required."),

  data_type: z.enum(DATA_TYPE_VALUES),

  unit_family: z.string().nullable(),
  default_unit: z.string().nullable(),

  collection_level: z.enum(COLLECTION_LEVEL_VALUES),
  frequency: z.enum(FREQUENCY_VALUES),

  is_required: z.boolean(),

  display_order: z
    .number()
    .int("Display order must be a whole number.")
    .min(0, "Display order cannot be negative."),

  is_active: z.boolean(),
});

type DatapointFormValues = z.infer<typeof datapointSchema>;

/* ============================================================
   REQUIRED MARK
============================================================ */

function RequiredMark() {
  return (
    <span className="ml-0.5 text-red-600" aria-hidden="true">
      *
    </span>
  );
}

/* ============================================================
   COMPONENT
   ------------------------------------------------------------
   Route: /datapoints/:id/edit
============================================================ */

export default function DatapointEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  /* ==========================================================
     STATE
  ========================================================== */

  const [categories, setCategories] = useState<DatapointCategory[]>([]);
  const [unitFamilies, setUnitFamilies] = useState<UnitFamily[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [unitsFamilyId, setUnitsFamilyId] = useState<string | null>(null);
  const [modules, setModules] = useState<Module[]>([]);

  const [loadingOptions, setLoadingOptions] = useState(true);
  const [modulesLoading, setModulesLoading] = useState(true);
  const [loadingUnits, setLoadingUnits] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // True until the datapoint itself has been fetched and the
  // form has been populated via reset(). Kept separate from
  // loadingOptions/modulesLoading so the page doesn't render
  // the form with stale defaultValues while the real record
  // is still in flight.
  const [loadingDatapoint, setLoadingDatapoint] = useState(true);
  const [notFound, setNotFound] = useState(false);

  /* ==========================================================
     FORM
  ========================================================== */

  const form = useForm<DatapointFormValues>({
    resolver: zodResolver(datapointSchema),
    defaultValues: {
      code: "",
      category: "",
      module: "",
      label: "",
      description: "",
      data_type: "TEXT",
      unit_family: null,
      default_unit: null,
      collection_level: "COMPANY",
      frequency: "ANNUAL",
      is_required: false,
      display_order: 0,
      is_active: true,
    },
    mode: "onSubmit",
  });

  const { control, handleSubmit, setValue, reset } = form;

  const dataType = useWatch({ control, name: "data_type" });
  const selectedUnitFamily = useWatch({ control, name: "unit_family" });

  /* ==========================================================
     LOAD FORM OPTIONS (categories + unit families)
  ========================================================== */

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      try {
        setLoadingOptions(true);

        const [categoryResponse, unitFamilyResponse] = await Promise.all([
          DatapointApi.getCategories(),
          DatapointApi.getUnitFamilies(),
        ]);

        if (ignore) return;

        setCategories(categoryResponse.data);
        setUnitFamilies(unitFamilyResponse.data);
      } catch (error) {
        if (ignore) return;

        console.error("Failed to load datapoint form options:", error);
        setCategories([]);
        setUnitFamilies([]);
        toast.error("Failed to load datapoint form options.");
      } finally {
        if (!ignore) setLoadingOptions(false);
      }
    };

    queueMicrotask(() => {
      if (!ignore) void load();
    });

    return () => {
      ignore = true;
    };
  }, []);

  /* ==========================================================
     LOAD MODULES
  ========================================================== */

  useEffect(() => {
    let ignore = false;

    const loadModules = async () => {
      try {
        setModulesLoading(true);

        const response = await ModuleApi.getEnabled();

        if (!ignore) {
          setModules(response.data);
        }
      } catch (error) {
        if (!ignore) {
          console.error("Failed to load modules:", error);
          toast.error("Failed to load modules. Please try again.");
          setModules([]);
        }
      } finally {
        if (!ignore) setModulesLoading(false);
      }
    };

    queueMicrotask(() => {
      if (!ignore) void loadModules();
    });

    return () => {
      ignore = true;
    };
  }, []);

  function getRelationId(
  value:
    | string
    | { id: string }
    | null
    | undefined
): string | null {
  if (!value) {
    return null;
  }

  if (typeof value === "string") {
    return value;
  }

  return value.id;
}

  /* ==========================================================
     LOAD THE DATAPOINT ITSELF AND POPULATE THE FORM
  ========================================================== */

  useEffect(() => {
    if (!id) return;

    let ignore = false;

    const loadDatapoint = async () => {
      try {
        setLoadingDatapoint(true);
        setNotFound(false);

        const response = await DatapointApi.getById(id);

        if (ignore) return;

      const datapoint = response.data;

reset({
  code: datapoint.code,

  category:
    datapoint.category &&
    typeof datapoint.category === "object"
      ? String((datapoint.category as { id: string | number }).id)
      : datapoint.category != null
        ? String(datapoint.category)
        : "",

   module: datapoint.module,
  label: datapoint.label,
  description: datapoint.description,
  data_type: datapoint.data_type,

  unit_family: getRelationId(datapoint.unit_family),

  default_unit: getRelationId(datapoint.default_unit),

  collection_level:
    datapoint.collection_level === "COMPANY" ||
    datapoint.collection_level === "FACILITY" ||
    datapoint.collection_level === "ORG_NODE"
      ? datapoint.collection_level
      : "COMPANY",

  frequency: datapoint.frequency,
  is_required: datapoint.is_required,
  display_order: datapoint.display_order,
  is_active: datapoint.is_active,
});
      } catch (error) {
        if (ignore) return;

        console.error("Failed to load datapoint:", error);
        toast.error("Failed to load this datapoint.");
        setNotFound(true);
      } finally {
        if (!ignore) setLoadingDatapoint(false);
      }
    };

    queueMicrotask(() => {
      if (!ignore) void loadDatapoint();
    });

    return () => {
      ignore = true;
    };
  }, [id, reset]);

  /* ==========================================================
     LOAD UNITS FOR THE SELECTED UNIT FAMILY
     ----------------------------------------------------------
     Same cascade as DatapointCreate — fires whenever
     unit_family changes, including the first time it's set
     by reset() once the datapoint loads.
  ========================================================== */

  useEffect(() => {
    if (!selectedUnitFamily) {
      return;
    }

    let cancelled = false;

    const loadUnits = async () => {
      try {
        setLoadingUnits(true);

        const response = await DatapointApi.getUnitsByFamily(selectedUnitFamily);

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
     SUBMIT
  ========================================================== */

  const onSubmit = async (values: DatapointFormValues) => {
    if (!id) return;

    setSubmitting(true);

    try {
      const payload: DatapointFormData = {
        code: values.code.trim(),
        category: values.category,
        module: values.module,
        label: values.label.trim(),
        description: values.description.trim(),
        data_type: values.data_type,
        unit_family: values.unit_family || null,
        default_unit: values.default_unit || null,
        collection_level: values.collection_level,
        frequency: values.frequency,
        is_required: values.is_required,
        display_order: values.display_order,
        is_active: values.is_active,
      };

      await DatapointApi.update(id, payload);

      toast.success("Datapoint updated successfully.");
      navigate("/datapoints");
    } catch (error) {
      console.error("Failed to update datapoint:", error);
      toast.error("Failed to update datapoint. Please check the form and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  /* ==========================================================
     LOADING / NOT FOUND
  ========================================================== */

  if (loadingOptions || loadingDatapoint) {
    return (
      <AppShell
        title="Edit Datapoint"
        description="Update this ESG datapoint definition."
      >
        <div className="mt-6">
          <Card>
            <CardContent className="flex min-h-40 items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  if (notFound) {
    return (
      <AppShell
        title="Edit Datapoint"
        description="Update this ESG datapoint definition."
      >
        <div className="mt-6">
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-4 p-8">
              <p className="text-sm text-muted-foreground">
                This datapoint could not be found.
              </p>
              <Button variant="outline" onClick={() => navigate("/datapoints")}>
                Back to catalog
              </Button>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      title="Edit Datapoint"
      description="Update this ESG datapoint definition."
    >
      <div className="mt-6">
        <Card className="overflow-hidden">
          <CardHeader className="px-6 py-6">
            <CardTitle>Datapoint Details</CardTitle>
          </CardHeader>

          <Separator />

          <CardContent className="px-6 py-6">
            <Form {...form}>
              <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-8">

                {/* ==================================================
                    BASIC INFORMATION
                ================================================== */}

                <div className="grid gap-6 md:grid-cols-2">
                  <FormField
                    control={control}
                    name="code"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Code
                          <RequiredMark />
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="energy.electricity.quantity" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={control}
                    name="label"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Label
                          <RequiredMark />
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="Electricity Consumption" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={control}
                    name="category"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Category
                          <RequiredMark />
                        </FormLabel>
                        <Select
                          value={field.value || undefined}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select category" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {categories.map((category) => (
                              <SelectItem key={category.id} value={String(category.id)}>
                                {category.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={control}
                    name="module"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Module
                          <RequiredMark />
                        </FormLabel>

                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                          disabled={modulesLoading}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue
                                placeholder={
                                  modulesLoading ? "Loading modules..." : "Select module"
                                }
                              />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {modules.map((module) => (
                              <SelectItem key={module.code} value={module.code}>
                                {module.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* ==================================================
                    DESCRIPTION
                ================================================== */}

                <FormField
                  control={control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Description
                        <RequiredMark />
                      </FormLabel>
                      <FormControl>
                        <Textarea
                          rows={4}
                          placeholder="Describe what this datapoint measures."
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* ==================================================
                    DATA CONFIGURATION
                ================================================== */}

                <div className="grid gap-6 md:grid-cols-2">
                  <FormField
                    control={control}
                    name="data_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Data Type
                          <RequiredMark />
                        </FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {DATA_TYPE_OPTIONS.map((option) => (
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
                    control={control}
                    name="collection_level"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Collection Level
                          <RequiredMark />
                        </FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {COLLECTION_LEVEL_OPTIONS.map((option) => (
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
                    control={control}
                    name="frequency"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Frequency
                          <RequiredMark />
                        </FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {FREQUENCY_OPTIONS.map((option) => (
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
                    control={control}
                    name="unit_family"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Unit Family</FormLabel>
                        <Select
                          value={field.value ?? "none"}
                          onValueChange={(value) => {
                            field.onChange(value === "none" ? null : value);
                            // Changing the family invalidates whatever
                            // default unit was previously selected.
                            setValue("default_unit", null, {
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
                    control={control}
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

                  <FormField
                    control={control}
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
                                event.target.value === "" ? 0 : Number(event.target.value)
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
                    FLAGS
                ================================================== */}

                <div className="space-y-4">
                  <FormField
                    control={control}
                    name="is_required"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => field.onChange(checked === true)}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">Required datapoint</FormLabel>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={control}
                    name="is_active"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => field.onChange(checked === true)}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">Active</FormLabel>
                      </FormItem>
                    )}
                  />
                </div>

                {/* ==================================================
                    RELATED CONFIGURATION
                    ------------------------------------------------
                    Only relevant once the record exists (it does,
                    here — this is the edit page) and only for the
                    data types that have something to configure.
                ================================================== */}

                {(dataType === "SELECT" || dataType === "TABLE") && id && (
                  <>
                    <Separator />

                    <div>
                      <h3 className="mb-1 text-sm font-medium">Related Configuration</h3>
                      <p className="mb-4 text-sm text-muted-foreground">
                        {dataType === "SELECT"
                          ? "Manage the selectable values for this datapoint."
                          : "Manage the columns and rows collected for this datapoint."}
                      </p>

                      <Button
                        type="button"
                        variant="outline"
                        onClick={() =>
                          navigate(
                            dataType === "SELECT"
                              ? `/datapoints/${id}/options`
                              : `/datapoints/${id}/table-definition`
                          )
                        }
                      >
                        {dataType === "SELECT" ? (
                          <>
                            <ListChecks className="mr-2 h-4 w-4" />
                            Manage Options
                          </>
                        ) : (
                          <>
                            <Table2 className="mr-2 h-4 w-4" />
                            Manage Table Definition
                          </>
                        )}
                      </Button>
                    </div>
                  </>
                )}

                {/* ==================================================
                    ACTIONS
                ================================================== */}

                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => navigate("/datapoints")}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>

                  <Button type="submit" disabled={submitting}>
                    {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Save Changes
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}