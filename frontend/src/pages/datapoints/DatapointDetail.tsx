import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  ArrowLeft,
  Database,
  Pencil,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

import type {
  DatapointDetail,
  DatapointTableColumn,
  DatapointTableRow,
  Unit,
} from "@/types/datapoint";

import DatapointApi from "@/api/datapoints/DatapointApi";

import { DynamicFieldRenderer } from "./DynamicFieldRenderer";
import type { FieldValue } from "./fields";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

/* ==========================================================
   RELATION VALUE HELPER
   ----------------------------------------------------------
   Some endpoints return related fields (category, module,
   unit_family, default_unit) as a plain string/code, others
   return the full nested object. This normalizes either shape
   into a safe, renderable string so we never pass a raw
   object into JSX.
========================================================== */

type RelationLike = {
  name?: string;
  label?: string;
  code?: string;
  id?: string | number;
};

function relationLabel(
  value: string | RelationLike | null | undefined
) {
  if (!value) {
    return "—";
  }

  if (typeof value === "string") {
    return value;
  }

  return (
    value.name ??
    value.label ??
    value.code ??
    String(value.id ?? "—")
  );
}
/* ==========================================================
   TABLE DEFINITION RESPONSE
========================================================== */

interface DatapointTableDefinitionResponse {
  datapoint: DatapointDetail;
  columns: DatapointTableColumn[];
  rows: DatapointTableRow[];
}

/* ==========================================================
   DETAIL PAGE
========================================================== */

export default function DatapointDetailPage() {
  const navigate = useNavigate();
  const { user, permissions } = useAuth();
  const canManage = Boolean(
    user?.is_superuser || permissions.includes("datapoint.manage")
  );

  const { id } = useParams<{ id: string }>();

  const [datapoint, setDatapoint] = useState<DatapointDetail | null>(null);
  const [value, setValue] = useState<FieldValue>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableLoading, setTableLoading] = useState(false);
  const [unitsById, setUnitsById] = useState<Record<string, Unit>>({});

  /* ========================================================
     LOAD DATAPOINT
  ======================================================== */

  useEffect(() => {
    let cancelled = false;

    const loadDatapoint = async () => {
      if (!id) {
        if (!cancelled) {
          setError("Invalid datapoint ID.");
          setLoading(false);
        }
        return;
      }

      try {
        if (!cancelled) {
          setLoading(true);
          setError(null);
        }

        const response = await DatapointApi.getById(id);

        if (!cancelled) {
          setDatapoint(response.data);
        }
      } catch (err) {
        console.error("Failed to load datapoint:", err);
        toast.error("Failed to load datapoint. Please try again.");

        if (!cancelled) {
          setDatapoint(null);
          setError("Failed to load the datapoint.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadDatapoint();

    return () => {
      cancelled = true;
    };
  }, [id]);

  /* ========================================================
     LOAD SELECT OPTIONS / TABLE DEFINITION

     Backend provides these through dedicated endpoints.
  ======================================================== */

  useEffect(() => {
    if (!datapoint) {
      return;
    }

    // Already loaded for this datapoint — don't refetch.
    if (datapoint.data_type === "SELECT" && datapoint.options !== undefined) {
      return;
    }

    if (
      datapoint.data_type === "TABLE" &&
      datapoint.table_columns !== undefined
    ) {
      return;
    }

    let cancelled = false;

    const loadDefinition = async () => {
      /* ------------------------------------------------------
         SELECT OPTIONS
      ------------------------------------------------------ */

      if (datapoint.data_type === "SELECT") {
        try {
          const response = await DatapointApi.getOptions(datapoint.id);

          if (!cancelled) {
            setDatapoint((current) => {
              if (!current) return current;
              return { ...current, options: response.data };
            });
          }
        } catch (err) {
          console.error("Failed to load datapoint options:", err);
        }

        return;
      }

      /* ------------------------------------------------------
         TABLE DEFINITION
      ------------------------------------------------------ */

      if (datapoint.data_type === "TABLE") {
        try {
          if (!cancelled) setTableLoading(true);

          const response = await DatapointApi.getTableDefinition(datapoint.id);
          const data = response.data as DatapointTableDefinitionResponse;

          if (!cancelled) {
            setDatapoint((current) => {
              if (!current) return current;
              return {
                ...current,
                table_columns: data.columns,
                table_rows: data.rows,
              };
            });
          }
        } catch (err) {
          console.error("Failed to load table definition:", err);
        } finally {
          if (!cancelled) setTableLoading(false);
        }
      }
    };

        void loadDefinition();

    return () => {
      cancelled = true;
    };
    // Only re-run when the datapoint identity or type actually changes,
    // not on every setDatapoint() call inside this same effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datapoint?.id, datapoint?.data_type]);

  /* ========================================================
     LOAD UNITS FOR DISPLAY

     Resolves default_unit IDs (on the datapoint itself, and on
     any TABLE column) into real Unit objects so DynamicFieldRenderer
     can show a unit code next to numeric fields/cells. Uses the
     same DatapointApi.getUnitsByFamily already used elsewhere
     (e.g. DPtabledefinitionmanager) — no new endpoint.
  ======================================================== */

  useEffect(() => {
    if (!datapoint) {
      return;
    }

    const familyIds = new Set<string>();

    const topLevelFamily =
      typeof datapoint.unit_family === "string"
        ? datapoint.unit_family
        : datapoint.unit_family?.id;
    if (topLevelFamily) familyIds.add(topLevelFamily);

    for (const column of datapoint.table_columns ?? []) {
      if (column.unit_family) familyIds.add(column.unit_family);
    }

    if (familyIds.size === 0) {
      return;
    }

    let cancelled = false;

    const loadUnits = async () => {
      try {
        const responses = await Promise.all(
          Array.from(familyIds).map((familyId) =>
            DatapointApi.getUnitsByFamily(familyId)
          )
        );

        if (cancelled) return;

        const nextUnitsById: Record<string, Unit> = {};
        for (const response of responses) {
          for (const unit of response.data) {
            nextUnitsById[unit.id] = unit;
          }
        }

        setUnitsById(nextUnitsById);
      } catch (err) {
        console.error("Failed to load units for display:", err);
      }
    };

    void loadUnits();

    return () => {
      cancelled = true;
    };
  }, [datapoint,datapoint?.id, datapoint?.unit_family, datapoint?.table_columns]);

  /* ========================================================
     LOADING
  ======================================================== */

  if (loading) {
    return (
      <AppShell title="Datapoint" description="Loading datapoint definition.">
        <div className="flex min-h-[300px] items-center justify-center">
          <Card className="w-full max-w-lg">
            <CardContent className="p-8 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Database className="h-6 w-6 text-primary" />
              </div>

              <h2 className="text-xl font-semibold text-foreground">
                Loading Datapoint
              </h2>

              <p className="mt-2 text-sm text-muted-foreground">
                Please wait while the datapoint definition is loaded.
              </p>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  /* ========================================================
     NOT FOUND / ERROR
  ======================================================== */

  if (!datapoint || error) {
    return (
      <AppShell
        title="Datapoint Not Found"
        description="The requested datapoint could not be found."
      >
        <div className="flex min-h-[300px] items-center justify-center">
          <Card className="w-full max-w-lg">
            <CardContent className="p-8 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Database className="h-6 w-6 text-primary" />
              </div>

              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Datapoint Not Found
              </h2>

              <p className="mb-6 text-sm text-muted-foreground">
                {error ??
                  "The datapoint you are looking for does not exist in the current catalog."}
              </p>

              <Button type="button" onClick={() => navigate("/datapoints")}>
                Back to Catalog
              </Button>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  /* ========================================================
     UI
  ======================================================== */

  return (
    <AppShell
      title={datapoint.label}
      description="Inspect the datapoint definition."
    >
      <div className="space-y-5">

        {/* ==================================================
            PAGE ACTIONS
        ================================================== */}

        <div className="flex items-center justify-between gap-4">
          <Button
            type="button"
            variant="ghost"
            className="gap-2 px-2"
            onClick={() => navigate("/datapoints")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Catalog
          </Button>

                    {canManage && (
            <Button
              type="button"
              className="gap-2"
              onClick={() => navigate(`/datapoints/${datapoint.id}/edit`)}
            >
              <Pencil className="h-4 w-4" />
              Edit Datapoint
            </Button>
          )}
        </div>

        {/* ==================================================
            SINGLE CARD — EVERYTHING LIVES HERE
        ================================================== */}

        <Card className="overflow-hidden">

          {/* HEADER */}

          <CardHeader className="flex-row items-start justify-between gap-6 space-y-0 px-6 py-6">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                <Database className="h-7 w-7 text-primary" />
              </div>

              <div className="min-w-0">
                <CardTitle className="truncate text-xl">
                  {datapoint.label}
                </CardTitle>

                <p className="mt-1 text-sm text-muted-foreground">
                  {datapoint.code}
                </p>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <Badge variant="secondary">{datapoint.data_type}</Badge>

              <Badge variant={datapoint.is_active ? "success" : "destructive"}>
                {datapoint.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
          </CardHeader>

          <Separator />

          <CardContent className="p-0">

            {/* ==============================================
                FIELD PREVIEW
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-4 text-lg font-semibold text-foreground">
                Field Preview
              </h3>

                            {tableLoading ? (
                <p className="text-sm text-muted-foreground">
                  Loading table definition...
                </p>
              ) : (
                <DynamicFieldRenderer
                  datapoint={datapoint}
                  value={value}
                  onChange={setValue}
                  unitsById={unitsById}
                />
              )}
            </section>

            <Separator />

            {/* ==============================================
                BASIC INFORMATION
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-5 text-lg font-semibold text-foreground">
                Basic Information
              </h3>

              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <InfoItem label="Code" value={datapoint.code} />
                <InfoItem
                  label="Category"
                  value={relationLabel(datapoint.category)}
                />
                <InfoItem
                  label="Module"
                  value={relationLabel(datapoint.module)}
                />
                <InfoItem
                  label="Display Order"
                  value={String(datapoint.display_order)}
                />
              </div>
            </section>

            <Separator />

            {/* ==============================================
                COLLECTION CONFIGURATION
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-5 text-lg font-semibold text-foreground">
                Collection Configuration
              </h3>

              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <InfoItem label="Data Type" value={datapoint.data_type} />
                <InfoItem
                  label="Collection Level"
                  value={datapoint.collection_level}
                />
                <InfoItem label="Frequency" value={datapoint.frequency} />

                <div>
                  <p className="mb-1 text-sm text-muted-foreground">Required</p>
                  <Badge variant={datapoint.is_required ? "success" : "secondary"}>
                    {datapoint.is_required ? "Yes" : "No"}
                  </Badge>
                </div>
              </div>
            </section>

            <Separator />

            {/* ==============================================
                DESCRIPTION
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-5 text-lg font-semibold text-foreground">
                Description
              </h3>

              <div className="rounded-lg border border-border bg-muted p-4">
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                  {datapoint.description || "No description provided."}
                </p>
              </div>
            </section>

            <Separator />

            {/* ==============================================
                UNIT CONFIGURATION
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-5 text-lg font-semibold text-foreground">
                Unit Configuration
              </h3>

              <div className="grid gap-6 sm:grid-cols-2">
                <InfoItem
                  label="Unit Family"
                  value={
                    datapoint.unit_family
                      ? relationLabel(datapoint.unit_family)
                      : "Not specified"
                  }
                />
                <InfoItem
                  label="Default Unit"
                  value={
                    datapoint.default_unit
                      ? relationLabel(datapoint.default_unit)
                      : "Not specified"
                  }
                />
              </div>
            </section>

            {/* ==============================================
                SELECT OPTIONS
            ============================================== */}

            {datapoint.data_type === "SELECT" && (
              <>
                <Separator />

                <section className="px-6 py-6">
                  <h3 className="mb-5 text-lg font-semibold text-foreground">
                    Select Options
                  </h3>

                  {datapoint.options && datapoint.options.length > 0 ? (
                    <div className="overflow-hidden rounded-lg border border-border">
                      <div className="grid grid-cols-[80px_1fr_1fr_100px] border-b bg-muted px-4 py-3 text-sm font-semibold text-foreground">
                        <span>Order</span>
                        <span>Code</span>
                        <span>Label</span>
                        <span>Status</span>
                      </div>

                      {datapoint.options
                        .slice()
                        .sort((a, b) => a.display_order - b.display_order)
                        .map((option) => (
                          <div
                            key={option.id}
                            className="grid grid-cols-[80px_1fr_1fr_100px] items-center border-b px-4 py-3 last:border-b-0"
                          >
                            <span className="text-sm text-muted-foreground">
                              {option.display_order}
                            </span>

                            <span className="text-sm font-medium text-foreground">
                              {option.code}
                            </span>

                            <span className="text-sm text-muted-foreground">
                              {option.label}
                            </span>

                            <Badge
                              variant={option.is_active ? "success" : "destructive"}
                            >
                              {option.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No options are configured.
                    </p>
                  )}
                </section>
              </>
            )}

            {/* ==============================================
                TABLE DEFINITION
            ============================================== */}

            {datapoint.data_type === "TABLE" && (
              <>
                <Separator />

                <section className="px-6 py-6">
                  <h3 className="mb-5 text-lg font-semibold text-foreground">
                    Table Definition
                  </h3>

                  <div className="space-y-6">

                    {/* TABLE COLUMNS */}

                    <div>
                      <h4 className="mb-3 text-sm font-semibold text-foreground">
                        Columns
                      </h4>

                      {datapoint.table_columns && datapoint.table_columns.length > 0 ? (
                        <div className="overflow-hidden rounded-lg border border-border">
                          <div className="grid grid-cols-[80px_1fr_1fr_140px_100px] border-b bg-muted px-4 py-3 text-sm font-semibold text-foreground">
                            <span>Order</span>
                            <span>Code</span>
                            <span>Label</span>
                            <span>Data Type</span>
                            <span>Required</span>
                          </div>

                          {datapoint.table_columns
                            .slice()
                            .sort((a, b) => a.display_order - b.display_order)
                            .map((column) => (
                              <div
                                key={column.id}
                                className="grid grid-cols-[80px_1fr_1fr_140px_100px] items-center border-b px-4 py-3 last:border-b-0"
                              >
                                <span className="text-sm text-muted-foreground">
                                  {column.display_order}
                                </span>

                                <span className="text-sm font-medium text-foreground">
                                  {column.code}
                                </span>

                                <span className="text-sm text-muted-foreground">
                                  {column.label}
                                </span>

                                <Badge variant="secondary">{column.data_type}</Badge>

                                <Badge
                                  variant={column.is_required ? "success" : "secondary"}
                                >
                                  {column.is_required ? "Yes" : "No"}
                                </Badge>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No table columns are configured.
                        </p>
                      )}
                    </div>

                    {/* TABLE ROWS */}

                    <div>
                      <h4 className="mb-3 text-sm font-semibold text-foreground">
                        Rows
                      </h4>

                      {datapoint.table_rows && datapoint.table_rows.length > 0 ? (
                        <div className="overflow-hidden rounded-lg border border-border">
                          <div className="grid grid-cols-[80px_1fr_1fr] border-b bg-muted px-4 py-3 text-sm font-semibold text-foreground">
                            <span>Order</span>
                            <span>Code</span>
                            <span>Label</span>
                          </div>

                          {datapoint.table_rows
                            .slice()
                            .sort((a, b) => a.display_order - b.display_order)
                            .map((row) => (
                              <div
                                key={row.id}
                                className="grid grid-cols-[80px_1fr_1fr] items-center border-b px-4 py-3 last:border-b-0"
                              >
                                <span className="text-sm text-muted-foreground">
                                  {row.display_order}
                                </span>

                                <span className="text-sm font-medium text-foreground">
                                  {row.code}
                                </span>

                                <span className="text-sm text-muted-foreground">
                                  {row.label}
                                </span>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No table rows are configured.
                        </p>
                      )}
                    </div>

                  </div>
                </section>
              </>
            )}

            <Separator />

            {/* ==============================================
                SYSTEM INFORMATION
            ============================================== */}

            <section className="px-6 py-6">
              <h3 className="mb-5 text-lg font-semibold text-foreground">
                System Information
              </h3>

              <div className="grid gap-6 sm:grid-cols-2">
                <InfoItem
                  label="Created At"
                  value={formatDate(datapoint.created_at)}
                />
                <InfoItem
                  label="Updated At"
                  value={formatDate(datapoint.updated_at)}
                />
              </div>
            </section>

          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

/* ==========================================================
   INFO ITEM
========================================================== */

interface InfoItemProps {
  label: string;
  value: string;
}

function InfoItem({ label, value }: InfoItemProps) {
  return (
    <div>
      <p className="mb-1 text-sm text-muted-foreground">{label}</p>
      <p className="text-sm font-medium text-foreground">{value || "-"}</p>
    </div>
  );
}

/* ==========================================================
   DATE FORMATTER
========================================================== */

function formatDate(value: string) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}