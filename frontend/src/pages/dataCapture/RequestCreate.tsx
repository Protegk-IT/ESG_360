import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, Loader2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import DataCaptureApi from "@/api/dataCapture/DataCaptureApi";
import DatapointApi from "@/api/datapoints/DatapointApi";
import OrganizationApi from "@/api/organizations/OrganizationApi";
import ReportingPeriodApi from "@/api/reporting_periods/ReportingPeriodApi";
import UserApi from "@/api/users/UserApi";

import { getApiErrorMessage } from "@/services/errors";

import type { CreateDataRequestPayload } from "@/types/dataCapture";
import type { Datapoint } from "@/types/datapoint";
import type { OrgNode } from "@/types/organization";
import type { ReportingPeriod } from "@/types/reporting-period";
import type { UserData } from "@/types/user";

const createRequestSchema = z.object({
  datapoint: z.string().min(1, "Datapoint is required."),
  org_node: z.string().min(1, "Organization / site is required."),
  reporting_period: z
    .string()
    .min(1, "Reporting period is required."),
  assignee: z.string().min(1, "Assignee is required."),
  due_date: z.string(),
  instructions: z.string().trim(),
});

type CreateRequestFormValues = z.infer<
  typeof createRequestSchema
>;

const defaultValues: CreateRequestFormValues = {
  datapoint: "",
  org_node: "",
  reporting_period: "",
  assignee: "",
  due_date: "",
  instructions: "",
};

function RequiredMark() {
  return (
    <span
      className="ml-0.5 text-red-600"
      aria-hidden="true"
    >
      *
    </span>
  );
}

function getOptionLabel(
  user: UserData,
): string {
  const fullName = [
    user.first_name,
    user.last_name,
  ]
    .filter(Boolean)
    .join(" ")
    .trim();

  return fullName
    ? `${fullName} (${user.username})`
    : user.username;
}

export default function DataCaptureRequestCreate() {
  const navigate = useNavigate();

  const [datapoints, setDatapoints] = useState<
    Datapoint[]
  >([]);

  const [orgNodes, setOrgNodes] = useState<OrgNode[]>(
    [],
  );

  const [reportingPeriods, setReportingPeriods] =
    useState<ReportingPeriod[]>([]);

  const [users, setUsers] = useState<UserData[]>([]);

  const [loadingOptions, setLoadingOptions] =
    useState(true);

  const [submitting, setSubmitting] =
    useState(false);

  const form = useForm<CreateRequestFormValues>({
    resolver: zodResolver(createRequestSchema),
    defaultValues,
    mode: "onSubmit",
  });

  const {
    control,
    handleSubmit,
  } = form;

  useEffect(() => {
    let cancelled = false;

    const loadOptions = async () => {
  try {
    setLoadingOptions(true);

    const [
      datapointResult,
      organizationResult,
      reportingPeriodResult,
      usersResult,
    ] = await Promise.allSettled([
      DatapointApi.getAll(),
      OrganizationApi.getAll({ is_active: true }),
      ReportingPeriodApi.getAll(),
      UserApi.getAll(),
    ]);

    if (cancelled) {
      return;
    }

    // Each option group degrades independently instead of
    // one failure (e.g. assignee list) blocking the whole form.
    setDatapoints(
      datapointResult.status === "fulfilled"
        ? datapointResult.value.data
        : [],
    );

    setOrgNodes(
      organizationResult.status === "fulfilled"
        ? organizationResult.value.data
        : [],
    );

    setReportingPeriods(
      reportingPeriodResult.status === "fulfilled"
        ? reportingPeriodResult.value.data
        : [],
    );

    setUsers(
      usersResult.status === "fulfilled"
        ? usersResult.value.data.filter((user) => user.is_active)
        : [],
    );

    // Surface individual failures instead of one generic toast.
    const failures = [
      { label: "datapoints", result: datapointResult },
      { label: "organizations / sites", result: organizationResult },
      { label: "reporting periods", result: reportingPeriodResult },
      { label: "assignees", result: usersResult },
    ].filter((entry) => entry.result.status === "rejected");

    if (failures.length > 0) {
      const labels = failures.map((f) => f.label).join(", ");
      toast.error(
        `Could not load: ${labels}. You may not have permission to view this data, or it's temporarily unavailable.`,
      );
    }
  } catch (error) {
    if (cancelled) {
      return;
    }

    console.error(
      "Failed to load data-request form options:",
      error,
    );

    toast.error(
      getApiErrorMessage(
        error,
        "Failed to load request form options.",
      ),
    );

    setDatapoints([]);
    setOrgNodes([]);
    setReportingPeriods([]);
    setUsers([]);
  } finally {
    if (!cancelled) {
      setLoadingOptions(false);
    }
  }
};

    void loadOptions();

    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = async (
    values: CreateRequestFormValues,
  ) => {
    setSubmitting(true);

    try {
      const payload: CreateDataRequestPayload = {
        datapoint: values.datapoint,
        org_node: values.org_node,
        reporting_period:
          values.reporting_period,
        assignee: values.assignee,
        due_date:
          values.due_date.trim() === ""
            ? null
            : values.due_date,
        instructions:
          values.instructions.trim(),
      };

      const response =
        await DataCaptureApi.create(payload);

      const createdRequest =
        response.data.data;

      toast.success(
        "Data request created successfully.",
      );

      navigate(
        `/data-capture/manage/${createdRequest.id}`,
      );
    } catch (error) {
      console.error(
        "Failed to create data request:",
        error,
      );

      toast.error(
        getApiErrorMessage(
          error,
          "Failed to create data request. Please try again.",
        ),
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingOptions) {
    return (
      <AppShell
        title="Create Data Request"
        description="Create and assign a new data-capture request."
      >
        <div className="mt-6">
          <Card>
            <CardContent className="flex min-h-48 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Create Data Request"
      description="Create and assign a new data-capture request."
    >
      <div className="mt-6">
        <Button
          type="button"
          variant="ghost"
          className="mb-4 px-0"
          onClick={() =>
            navigate("/data-capture/manage")
          }
          disabled={submitting}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Data Capture
        </Button>

        <Card className="overflow-hidden">
          <CardHeader className="px-6 py-6">
            <CardTitle>
              Data Request Details
            </CardTitle>
          </CardHeader>

          <Separator />

          <CardContent className="px-6 py-6">
            <Form {...form}>
              <form
                onSubmit={handleSubmit(onSubmit)}
                noValidate
                className="space-y-8"
              >
                {/* ==================================================
                    REQUEST SELECTION
                ================================================== */}

                <div className="grid gap-6 md:grid-cols-2">
                  {/* DATAPOINT */}
                  <FormField
                    control={control}
                    name="datapoint"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Datapoint
                          <RequiredMark />
                        </FormLabel>

                        <Select
                          value={
                            field.value || undefined
                          }
                          onValueChange={
                            field.onChange
                          }
                          disabled={
                            submitting ||
                            datapoints.length === 0
                          }
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select datapoint" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {datapoints
                              .filter(
                                (datapoint) =>
                                  datapoint.is_active,
                              )
                              .map((datapoint) => (
                                <SelectItem
                                  key={datapoint.id}
                                  value={String(
                                    datapoint.id,
                                  )}
                                >
                                  {datapoint.label} (
                                  {datapoint.code})
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>

                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* ORGANIZATION */}
                  <FormField
                    control={control}
                    name="org_node"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Organization / Site
                          <RequiredMark />
                        </FormLabel>

                        <Select
                          value={
                            field.value || undefined
                          }
                          onValueChange={
                            field.onChange
                          }
                          disabled={
                            submitting ||
                            orgNodes.length === 0
                          }
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select organization / site" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {orgNodes
                              .filter(
                                (node) =>
                                  node.is_active,
                              )
                              .map((node) => (
                                <SelectItem
                                  key={String(node.id)}
                                  value={String(
                                    node.id,
                                  )}
                                >
                                  {node.name}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>

                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* REPORTING PERIOD */}
                  <FormField
                    control={control}
                    name="reporting_period"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Reporting Period
                          <RequiredMark />
                        </FormLabel>

                        <Select
                          value={
                            field.value || undefined
                          }
                          onValueChange={
                            field.onChange
                          }
                          disabled={
                            submitting ||
                            reportingPeriods.length ===
                              0
                          }
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select reporting period" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {reportingPeriods
                              .filter(
                                (period) =>
                                  period.is_active,
                              )
                              .map((period) => (
                                <SelectItem
                                  key={String(
                                    period.id,
                                  )}
                                  value={String(
                                    period.id,
                                  )}
                                >
                                  {period.name}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>

                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* ASSIGNEE */}
                  <FormField
                    control={control}
                    name="assignee"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Assignee
                          <RequiredMark />
                        </FormLabel>

                        <Select
                          value={
                            field.value || undefined
                          }
                          onValueChange={
                            field.onChange
                          }
                          disabled={
                            submitting ||
                            users.length === 0
                          }
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select assignee" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {users.map((user) => (
                              <SelectItem
                                key={String(
                                  user.id,
                                )}
                                value={String(
                                  user.id,
                                )}
                              >
                                {getOptionLabel(user)}
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
                    REQUEST SETTINGS
                ================================================== */}

                <div className="grid gap-6 md:grid-cols-2">
                  {/* DUE DATE */}
                  <FormField
                    control={control}
                    name="due_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Due Date
                        </FormLabel>

                        <FormControl>
                          <Input
                            type="date"
                            {...field}
                            disabled={submitting}
                          />
                        </FormControl>

                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* ==================================================
                    INSTRUCTIONS
                ================================================== */}

                <FormField
                  control={control}
                  name="instructions"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Instructions
                      </FormLabel>

                      <FormControl>
                        <Textarea
                          rows={5}
                          placeholder="Provide instructions for the person completing this data request."
                          {...field}
                          disabled={submitting}
                        />
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* ==================================================
                    ACTIONS
                ================================================== */}

                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      navigate("/data-capture")
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

                    Create Request
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