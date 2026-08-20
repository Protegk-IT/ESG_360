import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import axios from "axios";

import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock3,
  Eye,
  FileCheck2,
  Gauge,
  Info,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Target,
  TrendingUp,
  Users,
  WalletCards,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";

import { Button } from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";

import { Separator } from "@/components/ui/separator";

import { Progress } from "@/components/ui/progress";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import ScoringApi from "@/api/materiality/ScoringApi";

import type {
  MaterialityAssessment,
} from "@/types/materiality/assessment";

import type {
  ScoreRunDetail,
  ScoreRunTopicResult,
  MaterialityClassification,
} from "@/types/materiality/scoring";


/* ============================================================
   SNAPSHOT TYPES

   Your backend returns:

   group_weights_snapshot: {
     "<group-id>": {
       name: "Employees",
       weight: "100.00"
     }
   }
============================================================ */

interface StakeholderWeightSnapshot {
  name: string;
  weight: string | number;
}

interface ThresholdSnapshot {
  primary_threshold?: string | number;
  secondary_threshold?: string | number;
  internal_blend_weight?: string | number;
}


/* ============================================================
   CLASSIFICATION LABELS
============================================================ */

const classificationLabels: Record<
  MaterialityClassification,
  string
> = {
  MATERIAL: "Material",
  MONITOR: "Monitor",
  NOT_MATERIAL: "Not Material",
  DOUBLE_MATERIAL: "Double Material",
  IMPACT_MATERIAL: "Impact Material",
  FINANCIAL_MATERIAL: "Financial Material",
  INSUFFICIENT_DATA: "Insufficient Data",
};


/* ============================================================
   PAGE
============================================================ */

export default function MaterialityResults() {
  const { assessmentId } =
    useParams<{
      assessmentId: string;
    }>();

  const navigate = useNavigate();


  /* ============================================================
     STATE
  ============================================================ */

  const [assessment, setAssessment] =
    useState<MaterialityAssessment | null>(
      null
    );

  const [scoreRun, setScoreRun] =
    useState<ScoreRunDetail | null>(
      null
    );

  const [selectedResult, setSelectedResult] =
    useState<ScoreRunTopicResult | null>(
      null
    );

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [detailOpen, setDetailOpen] =
    useState(false);


  /* ============================================================
     LOAD RESULTS
  ============================================================ */

  const loadResults = useCallback(
    async (refresh = false) => {
      if (!assessmentId) {
        setError(
          "Assessment ID is missing."
        );

        setLoading(false);

        return;
      }

      try {
        setError(null);

        if (refresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        const [
          assessmentResponse,
          resultsResponse,
        ] = await Promise.all([
          AssessmentApi.getById(
            assessmentId
          ),

          ScoringApi.getResults(
            assessmentId
          ),
        ]);

        setAssessment(
          assessmentResponse.data
        );

        const data =
          resultsResponse.data;

        /*
         * Backend returns:
         *
         * ScoreRunDetail
         *
         * OR
         *
         * {
         *   detail: "...",
         *   topic_results: []
         * }
         */

        if (
          "topic_results" in data &&
          Array.isArray(
            data.topic_results
          )
        ) {
          setScoreRun(
            data as ScoreRunDetail
          );
        } else {
          setScoreRun(null);
        }

      } catch (err: unknown) {
        console.error(
          "Failed to load materiality results:",
          err
        );

        if (
          axios.isAxiosError(err)
        ) {
          const message =
            err.response?.data?.detail ??
            err.response?.data?.message ??
            "Unable to load materiality results.";

          setError(
            typeof message === "string"
              ? message
              : "Unable to load materiality results."
          );
        } else if (
          err instanceof Error
        ) {
          setError(err.message);
        } else {
          setError(
            "Unable to load materiality results."
          );
        }

        setScoreRun(null);

      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [assessmentId]
  );


  /* ============================================================
     INITIAL LOAD
  ============================================================ */

  useEffect(() => {
    void loadResults();
  }, [loadResults]);


  /* ============================================================
     TOPIC RESULTS

     Backend:
       scoreRun.topic_results

     This is the actual table data.
  ============================================================ */

  const topicResults =
    useMemo<ScoreRunTopicResult[]>(
      () =>
        scoreRun?.topic_results ?? [],
      [scoreRun]
    );


  /* ============================================================
     MODE

     Double mode:
       primary = impact
       secondary = financial

     Single mode:
       primary = materiality
       secondary is hidden
  ============================================================ */

  const assessmentMode =
    scoreRun?.mode ??
    assessment?.mode ??
    "SINGLE";

const assessmentName =
  assessment?.name ?? "This assessment";

  const isDoubleMode =
    assessmentMode === "DOUBLE";


  /* ============================================================
     RESPONSE RATE
  ============================================================ */

  const responseRate =
    scoreRun &&
    scoreRun.invited_count > 0
      ? (
          scoreRun.response_count /
          scoreRun.invited_count
        ) * 100
      : 0;


  /* ============================================================
     CLASSIFICATION COUNTS
  ============================================================ */

  const classificationCounts =
    useMemo(() => {
      const counts: Record<
        MaterialityClassification,
        number
      > = {
        MATERIAL: 0,
        MONITOR: 0,
        NOT_MATERIAL: 0,
        DOUBLE_MATERIAL: 0,
        IMPACT_MATERIAL: 0,
        FINANCIAL_MATERIAL: 0,
        INSUFFICIENT_DATA: 0,
      };

      topicResults.forEach(
        (result) => {
          if (
            result.classification in
            counts
          ) {
            counts[
              result.classification
            ] += 1;
          }
        }
      );

      return counts;
    }, [topicResults]);


  /* ============================================================
     KPI VALUES
  ============================================================ */

  const totalTopics =
    topicResults.length;

  const materialTopics =
    isDoubleMode
      ? classificationCounts.DOUBLE_MATERIAL
      : classificationCounts.MATERIAL;

  const impactMaterialTopics =
    isDoubleMode
      ? classificationCounts.IMPACT_MATERIAL
      : 0;

  const financialMaterialTopics =
    isDoubleMode
      ? classificationCounts.FINANCIAL_MATERIAL
      : 0;

  const notMaterialTopics =
    classificationCounts.NOT_MATERIAL;

  const insufficientDataTopics =
    classificationCounts.INSUFFICIENT_DATA;

  const overriddenTopics =
    topicResults.filter(
      (result) =>
        result.is_override === true
    ).length;


  /* ============================================================
     SNAPSHOT VALUES

     IMPORTANT:
     scoreRun is checked before this section because
     scoreRun is nullable.
  ============================================================ */

  const thresholds =
    (
      scoreRun?.thresholds_snapshot ??
      {}
    ) as ThresholdSnapshot;

  const groupWeights =
    (
      scoreRun?.group_weights_snapshot ??
      {}
    ) as Record<
      string,
      StakeholderWeightSnapshot
    >;

  const primaryThreshold =
    Number(
      thresholds.primary_threshold ?? 0
    );

  const secondaryThreshold =
    Number(
      thresholds.secondary_threshold ?? 0
    );

  const internalBlendWeight =
    Number(
      thresholds.internal_blend_weight ?? 0
    );


  /* ============================================================
     OPEN RESULT DETAILS
  ============================================================ */

  const handleViewResult = (
    result: ScoreRunTopicResult
  ) => {
    setSelectedResult(result);
    setDetailOpen(true);
  };


  /* ============================================================
     CLOSE RESULT DETAILS
  ============================================================ */

  const handleDetailOpenChange = (
    open: boolean
  ) => {
    setDetailOpen(open);

    if (!open) {
      setSelectedResult(null);
    }
  };


  /* ============================================================
     NAVIGATION
  ============================================================ */

  const handleBack = () => {
    if (!assessmentId) {
      return;
    }

    navigate(
      `/materiality/assessments/${assessmentId}/scoring`
    );
  };


  /* ============================================================
     MISSING ASSESSMENT
  ============================================================ */

  if (!assessmentId) {
    return (
      <AppShell
        title="Materiality Results"
        description="Review final materiality scoring results."
      >
        <div className="flex min-h-[500px] items-center justify-center p-6">
          <Card className="w-full max-w-md">
            <CardContent className="p-8 text-center">

              <BarChart3 className="mx-auto h-10 w-10 text-muted-foreground" />

              <h2 className="mt-4 text-lg font-semibold">
                Assessment not found
              </h2>

              <p className="mt-2 text-sm text-muted-foreground">
                A valid assessment ID is required
                to view scoring results.
              </p>

            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }


  /* ============================================================
     LOADING
  ============================================================ */

  if (loading) {
    return (
      <AppShell
        title="Materiality Results"
        description="Review final materiality scoring results."
      >
        <div className="space-y-6">

          <div className="flex items-center gap-3">
            <div className="h-10 w-10 animate-pulse rounded-lg bg-muted" />

            <div className="space-y-2">
              <div className="h-5 w-64 animate-pulse rounded bg-muted" />
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            </div>
          </div>


          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({
              length: 4,
            }).map((_, index) => (
              <Card key={index}>
                <CardContent className="p-6">
                  <div className="space-y-3">
                    <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                    <div className="h-8 w-16 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-32 animate-pulse rounded bg-muted" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>


          <Card>
            <CardContent className="p-6">
              <div className="h-64 animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>

        </div>
      </AppShell>
    );
  }


  /* ============================================================
     ERROR
  ============================================================ */

  if (error) {
    return (
      <AppShell
        title="Materiality Results"
        description="Review final materiality scoring results."
      >
        <Card className="border-destructive/30">
          <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">

            <div className="rounded-full bg-destructive/10 p-4">
              <BarChart3 className="h-8 w-8 text-destructive" />
            </div>

            <div>
              <h2 className="text-lg font-semibold">
                Unable to load scoring results
              </h2>

              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                {error}
              </p>
            </div>

            <Button
              type="button"
              onClick={() =>
                void loadResults(true)
              }
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>

          </CardContent>
        </Card>
      </AppShell>
    );
  }


  /* ============================================================
     NO SCORE RUN

     This guard is IMPORTANT.

     After this point TypeScript knows that
     scoreRun is not null.
  ============================================================ */

  if (!scoreRun) {
    return (
      <AppShell
        title="Materiality Results"
        description="Review final materiality scoring results."
      >
        <div className="flex min-h-[500px] items-center justify-center">
          <Card className="w-full max-w-md">
            <CardContent className="flex flex-col items-center p-8 text-center">

              <div className="rounded-full bg-slate-100 p-4">
                <BarChart3 className="h-10 w-10 text-slate-500" />
              </div>

              <h2 className="mt-4 text-lg font-semibold">
                No Scoring Results
              </h2>

              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                No completed scoring run is available
                for this assessment yet.
              </p>

              <Button
                type="button"
                className="mt-5"
                onClick={handleBack}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Scoring
              </Button>

            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }


  /* ============================================================
     MAIN PAGE

     scoreRun is GUARANTEED non-null from here.
  ============================================================ */

  return (
    <AppShell
      title="Materiality Results"
      description="Review the final scoring results, classifications and audit snapshot for this ESG assessment."
    >

      <div className="space-y-6">


        {/* ======================================================
            HEADER
        ====================================================== */}

        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

          <div className="flex items-start gap-3">

            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleBack}
              className="mt-1 shrink-0"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>

            <div>

              <div className="flex flex-wrap items-center gap-2">

                <h1 className="text-2xl font-semibold tracking-tight">
                  Materiality Results
                </h1>

                <Badge
                  variant="outline"
                  className="border-emerald-200 bg-emerald-50 text-emerald-700"
                >
                  <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                  Scoring Complete
                </Badge>

                <Badge
                  variant="outline"
                  className="border-slate-200 bg-slate-50 text-slate-700"
                >
                  {isDoubleMode
                    ? "Double Materiality"
                    : "Single Materiality"}
                </Badge>

              </div>

              <p className="mt-1 text-sm text-muted-foreground">
                Final backend-calculated results for{" "}
                <span className="font-medium text-foreground">
                    {assessmentName}
                </span>
              </p>

            </div>

          </div>


          {/* HEADER ACTIONS */}

          <div className="flex items-center gap-2">

            <Button
              type="button"
              variant="outline"
              disabled={refreshing}
              onClick={() =>
                void loadResults(true)
              }
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${
                  refreshing
                    ? "animate-spin"
                    : ""
                }`}
              />

              {refreshing
                ? "Refreshing..."
                : "Refresh"}
            </Button>

            <Button
              type="button"
              onClick={handleBack}
            >
              <Gauge className="mr-2 h-4 w-4" />
              Scoring
            </Button>

          </div>

        </div>


        {/* ======================================================
            ASSESSMENT CONTEXT
        ====================================================== */}

        <Card className="border-slate-200 bg-gradient-to-r from-slate-50 to-white">
          <CardContent className="p-5">

            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">

              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Assessment
                </p>

                <p className="mt-1 truncate text-sm font-semibold">
                   {assessmentName}
                </p>
              </div>


              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Mode
                </p>

                <p className="mt-1 text-sm font-semibold">
                  {isDoubleMode
                    ? "Double Materiality"
                    : "Single Materiality"}
                </p>
              </div>


              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Method Version
                </p>

                <p className="mt-1 text-sm font-semibold">
                  {scoreRun.method_version}
                </p>
              </div>


              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Latest Score Run
                </p>

                <p className="mt-1 text-sm font-semibold">
                  {new Date(
                    scoreRun.run_at
                  ).toLocaleString(
                    undefined,
                    {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }
                  )}
                </p>
              </div>

            </div>

          </CardContent>
        </Card>


        {/* ======================================================
            KPI CARDS
        ====================================================== */}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          {/* TOTAL */}

          <Card className="border-slate-200">
            <CardContent className="p-5">

              <div className="flex items-start justify-between">

                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Total Sub-topics
                  </p>

                  <p className="mt-2 text-3xl font-semibold">
                    {totalTopics}
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Included in this score run
                  </p>
                </div>

                <div className="rounded-lg bg-slate-100 p-2.5">
                  <Target className="h-5 w-5 text-slate-600" />
                </div>

              </div>

            </CardContent>
          </Card>


          {/* RESPONSE */}

          <Card className="border-slate-200">
            <CardContent className="p-5">

              <div className="flex items-start justify-between">

                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Response Coverage
                  </p>

                  <p className="mt-2 text-3xl font-semibold">
                    {responseRate.toFixed(0)}%
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {scoreRun.response_count} of{" "}
                    {scoreRun.invited_count} invited
                  </p>
                </div>

                <div className="rounded-lg bg-emerald-50 p-2.5">
                  <Users className="h-5 w-5 text-emerald-600" />
                </div>

              </div>

              <Progress
                value={Math.min(
                  responseRate,
                  100
                )}
                className="mt-4 h-1.5"
              />

            </CardContent>
          </Card>


          {/* MATERIAL */}

          <Card className="border-slate-200">
            <CardContent className="p-5">

              <div className="flex items-start justify-between">

                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    {isDoubleMode
                      ? "Double Material"
                      : "Material Topics"}
                  </p>

                  <p className="mt-2 text-3xl font-semibold">
                    {materialTopics}
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {isDoubleMode
                      ? "Both dimensions are material"
                      : "Classified as material"}
                  </p>
                </div>

                <div className="rounded-lg bg-amber-50 p-2.5">
                  <BarChart3 className="h-5 w-5 text-amber-600" />
                </div>

              </div>

            </CardContent>
          </Card>


          {/* OVERRIDES */}

          <Card className="border-slate-200">
            <CardContent className="p-5">

              <div className="flex items-start justify-between">

                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Manual Overrides
                  </p>

                  <p className="mt-2 text-3xl font-semibold">
                    {overriddenTopics}
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Manager reclassifications
                  </p>
                </div>

                <div className="rounded-lg bg-violet-50 p-2.5">
                  <FileCheck2 className="h-5 w-5 text-violet-600" />
                </div>

              </div>

            </CardContent>
          </Card>

        </div>


        {/* ======================================================
            DOUBLE MATERIALITY CLASSIFICATION SUMMARY
        ====================================================== */}

        <Card className="border-slate-200">

          <CardHeader>
            <CardTitle className="text-base">
              Classification Summary
            </CardTitle>

            <CardDescription>
              Distribution of the final classifications
              returned by the backend scoring engine.
            </CardDescription>
          </CardHeader>


          <CardContent>

            <div
              className={`grid gap-3 ${
                isDoubleMode
                  ? "md:grid-cols-4"
                  : "md:grid-cols-3"
              }`}
            >

              {/* DOUBLE */}

              {isDoubleMode && (
                <ClassificationSummaryCard
                  title="Double Material"
                  count={
                    classificationCounts.DOUBLE_MATERIAL
                  }
                  description="Both impact and financial thresholds are met."
                  badge="Both"
                  className="border-emerald-200 bg-emerald-50/60"
                  textClassName="text-emerald-800"
                />
              )}


              {/* IMPACT */}

              {isDoubleMode && (
                <ClassificationSummaryCard
                  title="Impact Material"
                  count={
                    impactMaterialTopics
                  }
                  description="Impact threshold is met while financial threshold is not."
                  badge="Impact"
                  className="border-blue-200 bg-blue-50/60"
                  textClassName="text-blue-800"
                />
              )}


              {/* FINANCIAL */}

              {isDoubleMode && (
                <ClassificationSummaryCard
                  title="Financial Material"
                  count={
                    financialMaterialTopics
                  }
                  description="Financial threshold is met while impact threshold is not."
                  badge="Financial"
                  className="border-purple-200 bg-purple-50/60"
                  textClassName="text-purple-800"
                />
              )}


              {/* NOT MATERIAL */}

              <ClassificationSummaryCard
                title="Not Material"
                count={
                  notMaterialTopics
                }
                description="Neither applicable materiality threshold is met."
                badge="Neither"
                className="border-slate-200 bg-slate-50/70"
                textClassName="text-slate-800"
              />

            </div>


            {/* INSUFFICIENT DATA */}

            {insufficientDataTopics > 0 && (
              <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-4">

                <div className="flex items-center gap-2">

                  <Clock3 className="h-4 w-4 text-orange-600" />

                  <p className="text-sm font-medium text-orange-800">
                    {insufficientDataTopics} topic
                    {insufficientDataTopics !== 1
                      ? "s"
                      : ""}{" "}
                    with insufficient data
                  </p>

                </div>

                <p className="mt-1 text-xs text-orange-700">
                  These topics have an{" "}
                  <strong>
                    INSUFFICIENT_DATA
                  </strong>{" "}
                  classification and should not be interpreted
                  as a genuine score of zero.
                </p>

              </div>
            )}

          </CardContent>
        </Card>


        {/* ======================================================
            SCORE CONFIGURATION SNAPSHOT
        ====================================================== */}

        <div className="grid gap-6 lg:grid-cols-2">


          {/* THRESHOLDS */}

          <Card className="border-slate-200">

            <CardHeader>
              <CardTitle className="text-base">
                Scoring Configuration
              </CardTitle>

              <CardDescription>
                Configuration captured when this score run
                was executed.
              </CardDescription>
            </CardHeader>


            <CardContent>

              <div className="space-y-4">

                <SnapshotRow
                  label="Primary Threshold"
                  description="Impact materiality threshold"
                  value={primaryThreshold.toFixed(2)}
                />

                <Separator />

                <SnapshotRow
                  label="Secondary Threshold"
                  description="Financial materiality threshold"
                  value={secondaryThreshold.toFixed(2)}
                />

                <Separator />

                <SnapshotRow
                  label="Internal Blend Weight"
                  description="Weight applied to internal expert scoring"
                  value={`${(
                    internalBlendWeight * 100
                  ).toFixed(0)}%`}
                />

                <Separator />

                <SnapshotRow
                  label="Scoring Mode"
                  description="Materiality calculation model"
                  value={
                    isDoubleMode
                      ? "DOUBLE"
                      : "SINGLE"
                  }
                />

              </div>

            </CardContent>
          </Card>


          {/* STAKEHOLDER WEIGHTS */}

          <Card className="border-slate-200">

            <CardHeader>
              <CardTitle className="text-base">
                Stakeholder Weight Snapshot
              </CardTitle>

              <CardDescription>
                Stakeholder group weights captured during
                this score run.
              </CardDescription>
            </CardHeader>


            <CardContent>

              {Object.keys(
                groupWeights
              ).length === 0 ? (

                <div className="rounded-lg border border-dashed p-6 text-center">

                  <Users className="mx-auto h-6 w-6 text-muted-foreground" />

                  <p className="mt-2 text-sm font-medium">
                    No stakeholder weights available
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    This score run does not contain
                    stakeholder weight information.
                  </p>

                </div>

              ) : (

                <div className="space-y-3">

                  {Object.entries(
                    groupWeights
                  ).map(
                    ([
                      groupId,
                      group,
                    ]) => {

                      const weight =
                        Number(
                          group.weight ?? 0
                        );

                      return (
                        <div
                          key={groupId}
                          className="rounded-lg border border-slate-200 bg-slate-50/50 p-4"
                        >

                          <div className="flex items-center justify-between gap-4">

                            <div className="min-w-0">

                              <p className="truncate text-sm font-medium">
                                {group.name ||
                                  "Stakeholder Group"}
                              </p>

                              <p className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground">
                                {groupId}
                              </p>

                            </div>

                            <Badge
                              variant="outline"
                              className="shrink-0 font-mono"
                            >
                              {weight.toFixed(2)}%
                            </Badge>

                          </div>


                          <Progress
                            value={Math.min(
                              Math.max(
                                weight,
                                0
                              ),
                              100
                            )}
                            className="mt-3 h-1.5"
                          />

                        </div>
                      );
                    }
                  )}

                </div>

              )}

            </CardContent>
          </Card>

        </div>


        {/* ======================================================
            SCORE RUN DETAILS
        ====================================================== */}

        <Card className="border-slate-200">

          <CardHeader>
            <CardTitle className="text-base">
              Score Run Details
            </CardTitle>

            <CardDescription>
              Audit information captured when the backend
              generated these results.
            </CardDescription>
          </CardHeader>


          <CardContent>

            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">

              <AuditField
                label="Run ID"
                value={scoreRun.id}
                mono
              />

              <AuditField
                label="Run By"
                value={String(
                  scoreRun.run_by
                )}
              />

              <AuditField
                label="Method Version"
                value={
                  scoreRun.method_version
                }
              />

              <AuditField
                label="Run At"
                value={new Date(
                  scoreRun.run_at
                ).toLocaleString(
                  undefined,
                  {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }
                )}
              />

            </div>

          </CardContent>
        </Card>


        {/* ======================================================
            FINAL SCORING RESULTS
        ====================================================== */}

        <Card className="border-slate-200">

          <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <CardTitle className="text-base">
                Final Scoring Results
              </CardTitle>

              <CardDescription>
                Final backend-calculated scores and
                classifications for every selected sub-topic.
              </CardDescription>

            </div>


            <div className="flex items-center gap-2">

              <Badge
                variant="outline"
                className="border-slate-200 bg-slate-50"
              >
                {topicResults.length}{" "}
                {topicResults.length === 1
                  ? "Sub-topic"
                  : "Sub-topics"}
              </Badge>

              {isDoubleMode && (
                <Badge
                  variant="outline"
                  className="border-emerald-200 bg-emerald-50 text-emerald-700"
                >
                  Impact + Financial
                </Badge>
              )}

            </div>

          </CardHeader>


          <CardContent>

            {topicResults.length === 0 ? (

              <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center">

                <BarChart3 className="mx-auto h-8 w-8 text-muted-foreground" />

                <h3 className="mt-3 text-sm font-semibold">
                  No scoring results available
                </h3>

                <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                  There are currently no topic-level results
                  available for this assessment.
                </p>

              </div>

            ) : (

              <div className="overflow-x-auto rounded-lg border border-slate-200">

                <Table>

                  <TableHeader>

                    <TableRow className="bg-slate-50/80">

                      <TableHead className="w-[80px]">
                        Code
                      </TableHead>

                      <TableHead>
                        Sub-topic
                      </TableHead>

                      <TableHead className="w-[90px]">
                        Category
                      </TableHead>

                      <TableHead className="text-right">
                        Impact
                      </TableHead>

                      {isDoubleMode && (
                        <TableHead className="text-right">
                          Financial
                        </TableHead>
                      )}

                      <TableHead>
                        Classification
                      </TableHead>

                      <TableHead className="text-center">
                        Status
                      </TableHead>

                      <TableHead className="w-[70px] text-right">
                        Details
                      </TableHead>

                    </TableRow>

                  </TableHeader>


                  <TableBody>

                    {topicResults.map(
                      (result) => {

                        const isInsufficient =
                          result.classification ===
                          "INSUFFICIENT_DATA";

                        return (
                          <TableRow
                            key={result.id}
                            className="cursor-pointer transition-colors hover:bg-slate-50"
                            onClick={() =>
                              handleViewResult(
                                result
                              )
                            }
                          >

                            {/* CODE */}

                            <TableCell>

                              <span className="rounded bg-slate-100 px-2 py-1 font-mono text-xs font-medium text-slate-700">
                                {result.subtopic_code ||
                                  "—"}
                              </span>

                            </TableCell>


                            {/* SUBTOPIC */}

                            <TableCell>

                              <div className="min-w-[240px]">

                                <p className="font-medium">
                                  {result.subtopic_name ||
                                    "Unnamed sub-topic"}
                                </p>

                                <p className="mt-0.5 max-w-[280px] truncate font-mono text-[10px] text-muted-foreground">
                                  {result.assessment_topic}
                                </p>

                              </div>

                            </TableCell>


                            {/* CATEGORY */}

                            <TableCell>

                              <Badge
                                variant="outline"
                                className="font-mono text-xs"
                              >
                                {result.category_code ||
                                  "—"}
                              </Badge>

                            </TableCell>


                            {/* IMPACT */}

                            <TableCell className="text-right">

                              <ScoreValue
                                value={
                                  toNumberOrNull(
                                    result.primary_score
                                  )
                                }
                                threshold={
                                  primaryThreshold
                                }
                              />

                            </TableCell>


                            {/* FINANCIAL */}

                            {isDoubleMode && (
                              <TableCell className="text-right">

                                <ScoreValue
                                  value={
                                    toNumberOrNull(
                                      result.secondary_score
                                    )
                                  }
                                  threshold={
                                    secondaryThreshold
                                  }
                                />

                              </TableCell>
                            )}


                            {/* CLASSIFICATION */}

                            <TableCell>

                              <ClassificationBadge
                                classification={
                                  result.classification
                                }
                              />

                            </TableCell>


                            {/* STATUS */}

                            <TableCell className="text-center">

                              {result.is_override ? (

                                <TooltipProvider>

                                  <Tooltip>

                                    <TooltipTrigger asChild>

                                      <Badge
                                        variant="outline"
                                        className="border-amber-300 bg-amber-50 text-amber-700"
                                      >
                                        <ShieldAlert className="mr-1 h-3 w-3" />
                                        Override
                                      </Badge>

                                    </TooltipTrigger>

                                    <TooltipContent>
                                      Classification manually
                                      overridden by ESG manager.
                                    </TooltipContent>

                                  </Tooltip>

                                </TooltipProvider>

                              ) : isInsufficient ? (

                                <Badge
                                  variant="outline"
                                  className="border-orange-200 bg-orange-50 text-orange-700"
                                >
                                  <Clock3 className="mr-1 h-3 w-3" />
                                  Data Needed
                                </Badge>

                              ) : (

                                <Badge
                                  variant="outline"
                                  className="border-emerald-200 bg-emerald-50 text-emerald-700"
                                >
                                  <CheckCircle2 className="mr-1 h-3 w-3" />
                                  Calculated
                                </Badge>

                              )}

                            </TableCell>


                            {/* DETAILS */}

                            <TableCell className="text-right">

                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={(event) => {
                                  event.stopPropagation();

                                  handleViewResult(
                                    result
                                  );
                                }}
                              >

                                <Eye className="h-4 w-4" />

                                <span className="sr-only">
                                  View scoring details
                                </span>

                              </Button>

                            </TableCell>

                          </TableRow>
                        );
                      }
                    )}

                  </TableBody>

                </Table>

              </div>

            )}

          </CardContent>

        </Card>


        {/* ======================================================
            HOW TO READ RESULTS
        ====================================================== */}

        <Card className="border-slate-200 bg-slate-50/50">

          <CardHeader>

            <CardTitle className="text-base">
              How to Read These Results
            </CardTitle>

            <CardDescription>
              These are the final values returned by the
              backend scoring engine.
            </CardDescription>

          </CardHeader>


          <CardContent>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

              <ExplanationCard
                icon={
                  <TrendingUp className="h-4 w-4 text-blue-600" />
                }
                title="Impact Score"
                description="Final primary score after stakeholder aggregation and, in double mode, internal expert blending."
              />

              {isDoubleMode && (
                <ExplanationCard
                  icon={
                    <WalletCards className="h-4 w-4 text-purple-600" />
                  }
                  title="Financial Score"
                  description="Final secondary score representing financial materiality after backend calculation and blending."
                />
              )}

              <ExplanationCard
                icon={
                  <Gauge className="h-4 w-4 text-amber-600" />
                }
                title="Threshold"
                description="A score at or above the configured threshold contributes to a material classification."
              />

              <ExplanationCard
                icon={
                  <ShieldAlert className="h-4 w-4 text-amber-600" />
                }
                title="Manual Override"
                description="An override means the ESG manager manually changed the classification and supplied an audit reason."
              />

            </div>

          </CardContent>

        </Card>


        {/* ======================================================
            RESULT DETAIL SHEET
        ====================================================== */}

        <Sheet
          open={detailOpen}
          onOpenChange={
            handleDetailOpenChange
          }
        >

          <SheetContent
            side="right"
            className="w-full overflow-y-auto sm:max-w-xl"
          >

            {selectedResult && (

              <>

                <SheetHeader>

                  <div className="flex items-center gap-2">

                    <SheetTitle>
                      Scoring Details
                    </SheetTitle>

                    {selectedResult.is_override && (
                      <Badge
                        variant="outline"
                        className="border-amber-300 bg-amber-50 text-amber-700"
                      >
                        Override
                      </Badge>
                    )}

                  </div>

                  <SheetDescription>
                    Detailed final scoring information for{" "}
                    <strong>
                      {selectedResult.subtopic_name ||
                        "this sub-topic"}
                    </strong>
                    .
                  </SheetDescription>

                </SheetHeader>


                <div className="mt-6 space-y-6">


                  {/* TOPIC IDENTITY */}

                  <div className="rounded-lg border bg-slate-50 p-4">

                    <div className="flex items-start justify-between gap-4">

                      <div className="min-w-0">

                        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Sub-topic
                        </p>

                        <p className="mt-1 text-base font-semibold">
                          {selectedResult.subtopic_name ||
                            "Unnamed sub-topic"}
                        </p>

                      </div>

                      <Badge
                        variant="outline"
                        className="shrink-0 font-mono"
                      >
                        {selectedResult.subtopic_code ||
                          "—"}
                      </Badge>

                    </div>


                    <div className="mt-4 flex flex-wrap gap-2">

                      <Badge
                        variant="outline"
                        className="font-mono"
                      >
                        Category{" "}
                        {selectedResult.category_code ||
                          "—"}
                      </Badge>

                      <ClassificationBadge
                        classification={
                          selectedResult.classification
                        }
                      />

                    </div>

                  </div>


                  {/* FINAL SCORES */}

                  <div>

                    <h3 className="text-sm font-semibold">
                      Final Scores
                    </h3>

                    <p className="mt-1 text-xs text-muted-foreground">
                      Values calculated and returned by
                      the backend scoring engine.
                    </p>


                    <div
                      className={`mt-3 grid gap-3 ${
                        isDoubleMode
                          ? "grid-cols-2"
                          : "grid-cols-1"
                      }`}
                    >

                      {/* IMPACT */}

                      <ScoreDetailCard
                        label="Impact Score"
                        value={toNumberOrNull(
                          selectedResult.primary_score
                        )}
                        threshold={
                          primaryThreshold
                        }
                      />


                      {/* FINANCIAL */}

                      {isDoubleMode && (
                        <ScoreDetailCard
                          label="Financial Score"
                          value={toNumberOrNull(
                            selectedResult.secondary_score
                          )}
                          threshold={
                            secondaryThreshold
                          }
                        />
                      )}

                    </div>

                  </div>


                  <Separator />


                  {/* CLASSIFICATION */}

                  <div>

                    <h3 className="text-sm font-semibold">
                      Final Classification
                    </h3>


                    <div className="mt-3 rounded-lg border p-4">

                      <div className="flex items-center justify-between gap-3">

                        <span className="text-sm text-muted-foreground">
                          Classification
                        </span>

                        <ClassificationBadge
                          classification={
                            selectedResult.classification
                          }
                        />

                      </div>


                      {isDoubleMode && (
                        <>
                          <Separator className="my-3" />

                          <ThresholdStatus
                            label="Impact threshold"
                            score={toNumberOrNull(
                              selectedResult.primary_score
                            )}
                            threshold={
                              primaryThreshold
                            }
                          />

                          <div className="mt-3">

                            <ThresholdStatus
                              label="Financial threshold"
                              score={toNumberOrNull(
                                selectedResult.secondary_score
                              )}
                              threshold={
                                secondaryThreshold
                              }
                            />

                          </div>

                        </>
                      )}

                    </div>

                  </div>


                  {/* OVERRIDE */}

                  {selectedResult.is_override && (
                    <>
                      <Separator />

                      <div>

                        <div className="flex items-center gap-2">

                          <ShieldAlert className="h-4 w-4 text-amber-600" />

                          <h3 className="text-sm font-semibold">
                            Manual Override
                          </h3>

                        </div>


                        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4">

                          <p className="text-xs font-medium uppercase tracking-wide text-amber-700">
                            Override Reason
                          </p>

                          <p className="mt-2 text-sm leading-relaxed text-amber-900">
                            {selectedResult.override_reason ||
                              "No override reason was provided."}
                          </p>

                        </div>

                      </div>
                    </>
                  )}


                  {/* AUDIT NOTE */}

                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">

                    <div className="flex items-start gap-3">

                      <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />

                      <p className="text-xs leading-relaxed text-slate-600">
                        These values represent the final result
                        stored in the score-run snapshot. Changes
                        to stakeholder weights or scoring
                        configuration later do not modify this
                        historical run.
                      </p>

                    </div>

                  </div>

                </div>

              </>
            )}

          </SheetContent>

        </Sheet>


        {/* ======================================================
            FOOTER / AUDIT NOTICE
        ====================================================== */}

        <div className="flex flex-col gap-2 border-t pt-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">

          <div className="flex items-center gap-2">

            <ShieldCheck className="h-4 w-4" />

            <span>
              Results are based on score run{" "}
              <span className="font-mono">
                {scoreRun.id}
              </span>
            </span>

          </div>


          <span>
            Method version{" "}
            <span className="font-medium text-foreground">
              {scoreRun.method_version}
            </span>
          </span>

        </div>


      </div>

    </AppShell>
  );
}


/* ============================================================
   HELPERS
============================================================ */

function toNumberOrNull(
  value: number | string | null | undefined
): number | null {
  if (
    value === null ||
    value === undefined
  ) {
    return null;
  }

  const parsed =
    typeof value === "number"
      ? value
      : Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}


/* ============================================================
   SNAPSHOT ROW
============================================================ */

function SnapshotRow({
  label,
  description,
  value,
}: {
  label: string;
  description: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">

      <div>

        <p className="text-sm font-medium">
          {label}
        </p>

        <p className="text-xs text-muted-foreground">
          {description}
        </p>

      </div>

      <Badge
        variant="outline"
        className="font-mono text-sm"
      >
        {value}
      </Badge>

    </div>
  );
}


/* ============================================================
   AUDIT FIELD
============================================================ */

function AuditField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>

      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>

      <p
        className={`mt-1 text-sm font-medium ${
          mono
            ? "break-all font-mono text-xs"
            : ""
        }`}
      >
        {value}
      </p>

    </div>
  );
}


/* ============================================================
   CLASSIFICATION SUMMARY CARD
============================================================ */

function ClassificationSummaryCard({
  title,
  count,
  description,
  badge,
  className,
  textClassName,
}: {
  title: string;
  count: number;
  description: string;
  badge: string;
  className: string;
  textClassName: string;
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${className}`}
    >

      <div className="flex items-center justify-between">

        <div>

          <p className="text-xs font-medium uppercase tracking-wide">
            {title}
          </p>

          <p
            className={`mt-2 text-2xl font-semibold ${textClassName}`}
          >
            {count}
          </p>

        </div>

        <Badge
          variant="outline"
          className="bg-white/70"
        >
          {badge}
        </Badge>

      </div>

      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        {description}
      </p>

    </div>
  );
}


/* ============================================================
   EXPLANATION CARD
============================================================ */

function ExplanationCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-white p-4">

      <div className="flex items-center gap-2">

        <div className="rounded-md bg-slate-50 p-2">
          {icon}
        </div>

        <p className="text-sm font-semibold">
          {title}
        </p>

      </div>

      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        {description}
      </p>

    </div>
  );
}


/* ============================================================
   SCORE DETAIL CARD
============================================================ */

function ScoreDetailCard({
  label,
  value,
  threshold,
}: {
  label: string;
  value: number | null;
  threshold: number;
}) {
  const safeValue =
    value === null
      ? 0
      : Math.max(
          0,
          Math.min(value, 5)
        );

  return (
    <div className="rounded-lg border p-4">

      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>

      <div className="mt-2 flex items-end justify-between">

        <p className="text-3xl font-semibold">
          {value === null
            ? "—"
            : value.toFixed(2)}
        </p>

        <span className="text-xs text-muted-foreground">
          / 5.00
        </span>

      </div>

      <Progress
        value={safeValue * 20}
        className="mt-3 h-2"
      />

      <div className="mt-2 flex items-center justify-between">

        <p className="text-xs text-muted-foreground">
          Threshold
        </p>

        <p className="font-mono text-xs font-medium">
          {threshold.toFixed(2)}
        </p>

      </div>

    </div>
  );
}


/* ============================================================
   THRESHOLD STATUS
============================================================ */

function ThresholdStatus({
  label,
  score,
  threshold,
}: {
  label: string;
  score: number | null;
  threshold: number;
}) {
  const met =
    score !== null &&
    score >= threshold;

  return (
    <div className="flex items-center justify-between">

      <span className="text-sm text-muted-foreground">
        {label}
      </span>

      <Badge
        variant="outline"
        className={
          met
            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : "border-slate-200 bg-slate-50 text-slate-600"
        }
      >
        {score === null
          ? "No data"
          : met
            ? "Met"
            : "Not met"}
      </Badge>

    </div>
  );
}


/* ============================================================
   SCORE VALUE
============================================================ */

function ScoreValue({
  value,
  threshold,
}: {
  value: number | null;
  threshold: number;
}) {
  if (value === null) {
    return (
      <span className="text-sm text-muted-foreground">
        —
      </span>
    );
  }

  const meetsThreshold =
    value >= threshold;

  return (
    <div className="flex items-center justify-end gap-2">

      <span
        className={`font-mono text-sm font-semibold ${
          meetsThreshold
            ? "text-emerald-700"
            : "text-slate-700"
        }`}
      >
        {value.toFixed(2)}
      </span>

      {meetsThreshold && (
        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
      )}

    </div>
  );
}


/* ============================================================
   CLASSIFICATION BADGE
============================================================ */

function ClassificationBadge({
  classification,
}: {
  classification: MaterialityClassification;
}) {
  switch (classification) {

    case "DOUBLE_MATERIAL":
      return (
        <Badge className="border-emerald-200 bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
          <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
          Double Material
        </Badge>
      );


    case "IMPACT_MATERIAL":
      return (
        <Badge className="border-blue-200 bg-blue-100 text-blue-800 hover:bg-blue-100">
          <TrendingUp className="mr-1.5 h-3.5 w-3.5" />
          Impact Material
        </Badge>
      );


    case "FINANCIAL_MATERIAL":
      return (
        <Badge className="border-purple-200 bg-purple-100 text-purple-800 hover:bg-purple-100">
          <WalletCards className="mr-1.5 h-3.5 w-3.5" />
          Financial Material
        </Badge>
      );


    case "MATERIAL":
      return (
        <Badge className="border-emerald-200 bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
          <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
          Material
        </Badge>
      );


    case "MONITOR":
      return (
        <Badge className="border-amber-200 bg-amber-100 text-amber-800 hover:bg-amber-100">
          Monitor
        </Badge>
      );


    case "INSUFFICIENT_DATA":
      return (
        <Badge className="border-orange-200 bg-orange-100 text-orange-800 hover:bg-orange-100">
          <Clock3 className="mr-1.5 h-3.5 w-3.5" />
          Insufficient Data
        </Badge>
      );


    case "NOT_MATERIAL":
    default:
      return (
        <Badge
          variant="outline"
          className="border-slate-300 bg-slate-50 text-slate-700"
        >
          {classificationLabels[
            classification
          ] ?? "Not Material"}
        </Badge>
      );
  }
}