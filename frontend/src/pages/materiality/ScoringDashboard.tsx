import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { Toaster, toast } from "sonner";
import {
  ArrowLeft,
  Calculator,
  CircleAlert,
  Clock3,
  FileCheck2,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Save,
  ShieldAlert,
  ShieldCheck,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import AppShell from "@/components/layout/AppShell";
import AssessmentApi from "@/api/materiality/AssessmentApi";
import ScoringApi from "@/api/materiality/ScoringApi";

import type { MaterialityAssessment } from "@/types/materiality/assessment";
import type {
  GroupBreakdownEntry,
  InternalScore,
  InternalScoreUpdate,
  MaterialityResult,
  ScoreOverridePayload,
  ScoreRun,
} from "@/types/materiality/scoring";

type Classification =
  | "MATERIAL"
  | "DOUBLE_MATERIAL"
  | "IMPACT_MATERIAL"
  | "FINANCIAL_MATERIAL"
  | "NOT_MATERIAL"
  | "MONITOR";

type ScoreField =
  | "scale"
  | "scope"
  | "irremediability"
  | "likelihood"
  | "financial_magnitude"
  | "financial_likelihood";

const MATERIAL_CLASSIFICATIONS: Classification[] = [
  "MATERIAL",
  "DOUBLE_MATERIAL",
  "IMPACT_MATERIAL",
  "FINANCIAL_MATERIAL",
];

const SCALE_OPTIONS = [1, 2, 3, 4, 5];

// Human-readable labels for the raw dimension keys that come back on
// group_breakdown (IMPACT / FINANCIAL / STAKEHOLDER_IMPORTANCE). Kept
// local to this file since it's purely a display concern.
const DIMENSION_LABELS: Record<string, string> = {
  IMPACT: "Impact",
  FINANCIAL: "Financial",
  STAKEHOLDER_IMPORTANCE: "Stakeholder Importance",
};

// Shared classes for every popup so Run Scoring / Override / Score Details
// all look and behave the same: centered on screen, solid white background,
// never transparent regardless of the app's theme variables.
const DIALOG_CONTENT_CLASS =
  "bg-white text-slate-900 shadow-2xl border border-slate-200";

export default function ScoringDashboard() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();

  // ------------------------------------------------------------
  // Main state
  // ------------------------------------------------------------
  const [assessment, setAssessment] = useState<MaterialityAssessment | null>(null);
  const [results, setResults] = useState<MaterialityResult[]>([]);
  const [, setInternalScores] = useState<InternalScore[]>([]);
  const [lastScoreRun, setLastScoreRun] = useState<ScoreRun | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingInternal, setSavingInternal] = useState(false);
  const [runningScoring, setRunningScoring] = useState(false);
  const [overriding, setOverriding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ------------------------------------------------------------
  // Dialog state
  // ------------------------------------------------------------
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState<MaterialityResult | null>(null);

  // ------------------------------------------------------------
  // Override form state
  // ------------------------------------------------------------
  const [overrideClassification, setOverrideClassification] = useState<Classification | "">("");
  const [overrideReason, setOverrideReason] = useState("");

  // ------------------------------------------------------------
  // Internal expert score form state (frontend only —
  // calculations happen server-side)
  // ------------------------------------------------------------
  const [internalForm, setInternalForm] = useState<Record<string, Partial<InternalScore>>>({});

  // loadDashboard NEVER shows its own success toast. It's called both as
  // a silent refetch after actions (save / run / override) AND from the
  // explicit "Refresh" button. Each caller is responsible for its own
  // single success toast — that's what was causing the double toast.
 const loadDashboard = useCallback(
  async (refresh = false) => {
    if (!assessmentId) return;

    try {
      setError(null);

      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      // ==========================================================
      // 1. Load assessment + results
      // These APIs are valid for both SINGLE and DOUBLE
      // ==========================================================

      const [assessmentRes, resultsRes] =
        await Promise.all([
          AssessmentApi.getById(assessmentId),
          ScoringApi.getResults(assessmentId),
        ]);

      const loadedAssessment =
        assessmentRes.data;

      setAssessment(loadedAssessment);

      // ==========================================================
      // 2. Process scoring results
      // ==========================================================

      const resultsData = resultsRes.data;

      const topicResults =
        Array.isArray(resultsData.topic_results)
          ? resultsData.topic_results
          : [];

      const loadedResults: MaterialityResult[] =
        topicResults.map((t) => ({
          id: t.id,
          assessment_topic:
            t.assessment_topic,
          subtopic_name:
            t.subtopic_name,
          subtopic_code:
            t.subtopic_code,
          category_code:
            t.category_code,
          primary_score:
            Number(t.primary_score),
          secondary_score:
            Number(t.secondary_score),
          classification:
            t.classification,
          is_override:
            t.is_override,
          override_reason:
            t.override_reason,

          // Stakeholder group breakdown
          group_breakdown:
            t.group_breakdown,
        }));

      setResults(loadedResults);

      // ==========================================================
      // 3. Internal scoring
      //
      // IMPORTANT:
      // /internal-scores/ is ONLY called for DOUBLE.
      // ==========================================================

      if (
        loadedAssessment.mode === "DOUBLE"
      ) {
        const internalRes =
          await ScoringApi.getInternalScores(
            assessmentId
          );

        const loadedInternal =
          Array.isArray(internalRes.data)
            ? internalRes.data
            : [];

        setInternalScores(
          loadedInternal
        );

        // --------------------------------------------------------
        // Hydrate internal expert scoring form
        // --------------------------------------------------------

        const formState: Record<
          string,
          Partial<InternalScore>
        > = {};

        loadedInternal.forEach(
          (score) => {
            formState[
              score.assessment_topic
            ] = {
              ...score,
            };
          }
        );

        setInternalForm(
          formState
        );
      } else {
        // ========================================================
        // SINGLE MATERIALITY
        //
        // Never call /internal-scores/
        // Clear any previous internal state.
        // ========================================================

        setInternalScores([]);
        setInternalForm({});
      }

      // ==========================================================
      // 4. Store latest score run
      // ==========================================================

      if ("run_at" in resultsData) {
        setLastScoreRun(
          resultsData
        );
      } else {
        setLastScoreRun(null);
      }

    } catch (err: unknown) {
      console.error(
        "Failed to load scoring dashboard:",
        err
      );

      const message =
        extractErrorMessage(
          err,
          "Unable to load scoring information."
        );

      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  },
  [assessmentId]
);

useEffect(() => {
  loadDashboard();

  // loadDashboard is intentionally triggered
  // whenever assessmentId changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [assessmentId]);
  // The only place "Dashboard refreshed" is shown — the manual Refresh
  // button. Actions like Save / Run / Override show their own toast
  // instead and call loadDashboard(true) silently.
  const handleManualRefresh = useCallback(async () => {
    await loadDashboard(true);
    toast.success("Dashboard refreshed.");
  }, [loadDashboard]);

  const assessmentMode = assessment?.mode ?? "SINGLE";
  const isDoubleMode = assessmentMode === "DOUBLE";

  const kpis = useMemo(() => {
    const totalTopics = results.length;

    // primary_score / secondary_score are never null coming back from
    // /results/ — run_scoring() defaults them to 0.00 when data is
    // missing. The backend's own signal for "not enough data yet" is
    // classification === "INSUFFICIENT_DATA", so that's what "scored"
    // has to key off (same check works for both Single and Double mode).
    const scoredTopics = results.filter(
      (r) => r.classification !== "INSUFFICIENT_DATA",
    ).length;

    const materialTopics = results.filter((r) =>
      MATERIAL_CLASSIFICATIONS.includes(r.classification as Classification),
    ).length;

    const overriddenTopics = results.filter((r) => r.is_override === true).length;

    return { totalTopics, scoredTopics, materialTopics, overriddenTopics };
  }, [results]);

  const scoringProgress =
    kpis.totalTopics > 0 ? Math.round((kpis.scoredTopics / kpis.totalTopics) * 100) : 0;

  const getInternalScore = useCallback(
    (topicId: string) => internalForm[topicId] ?? {},
    [internalForm],
  );

  const updateInternalField = useCallback(
    (topicId: string, field: ScoreField, value: number) => {
      setInternalForm((current) => ({
        ...current,
        [topicId]: { ...current[topicId], [field]: value },
      }));
    },
    [],
  );

  const updateImpactType = useCallback((topicId: string, value: "ACTUAL" | "POTENTIAL") => {
    setInternalForm((current) => ({
      ...current,
      [topicId]: {
        ...current[topicId],
        impact_type: value,
        // Likelihood is only meaningful for potential impacts
        ...(value === "ACTUAL" ? { likelihood: undefined } : {}),
      },
    }));
  }, []);

  const updateRationale = useCallback((topicId: string, value: string) => {
    setInternalForm((current) => ({
      ...current,
      [topicId]: { ...current[topicId], rationale: value },
    }));
  }, []);

  const handleSaveInternalScores = useCallback(async () => {
    if (!assessmentId) return;

    try {
      setSavingInternal(true);
      setError(null);

      // The view does `items = request.data` and requires
      // `isinstance(items, list)` — this must be a bare array, not
      // wrapped in `{ scores: [...] }`.
      const payload: InternalScoreUpdate = Object.entries(internalForm).map(
        ([assessmentTopic, score]) => ({
          assessment_topic: assessmentTopic,
          impact_type: score.impact_type ?? "ACTUAL",
          scale: score.scale ?? 1,
          scope: score.scope ?? 1,
          irremediability: score.irremediability ?? 1,
          likelihood: score.likelihood ?? null,
          financial_magnitude: score.financial_magnitude ?? 1,
          financial_likelihood: score.financial_likelihood ?? 1,
          rationale: score.rationale ?? "",
        }),
      );

      await ScoringApi.updateInternalScores(assessmentId, payload);
      await loadDashboard(true); // silent — no toast here
      toast.success("Expert scores saved successfully.");
    } catch (err: unknown) {
      console.error("Failed to save internal scores:", err);
      const message = extractErrorMessage(err, "Unable to save internal scores.");
      setError(message);
      toast.error(message);
    } finally {
      setSavingInternal(false);
    }
  }, [assessmentId, internalForm, loadDashboard]);

  const handleRunScoring = useCallback(async () => {
    if (!assessmentId) return;

    try {
      setRunningScoring(true);
      setError(null);

      await ScoringApi.runScoring(assessmentId);
      setRunDialogOpen(false);
      await loadDashboard(true); // silent — no toast here
      toast.success("Scoring run completed successfully.");
    } catch (err: unknown) {
      console.error("Failed to run scoring:", err);
      const message = extractErrorMessage(err, "Unable to run scoring.");
      setError(message);
      toast.error(message);
    } finally {
      setRunningScoring(false);
    }
  }, [assessmentId, loadDashboard]);

  const handleOpenDetails = useCallback((result: MaterialityResult) => {
    setSelectedResult(result);
    setDetailDialogOpen(true);
  }, []);

  const handleOpenOverride = useCallback((result: MaterialityResult) => {
    setSelectedResult(result);
    setOverrideClassification((result.classification ?? "") as Classification);
    setOverrideReason(result.override_reason ?? "");
    setOverrideDialogOpen(true);
  }, []);

  const handleOverride = useCallback(async () => {
    if (!assessmentId || !selectedResult) return;

    const reason = overrideReason.trim();

    if (!overrideClassification) {
      const message = "Please select a classification.";
      setError(message);
      toast.error(message);
      return;
    }

    if (reason.length < 20) {
      const message = "Override reason must contain at least 20 characters.";
      setError(message);
      toast.error(message);
      return;
    }

    try {
      setOverriding(true);
      setError(null);

      const payload: ScoreOverridePayload = {
        classification: overrideClassification,
        override_reason: reason,
      };

      await ScoringApi.overrideClassification(
        assessmentId,
        selectedResult.assessment_topic,
        payload,
      );

      setOverrideDialogOpen(false);
      setSelectedResult(null);
      await loadDashboard(true); // silent — no toast here
      toast.success("Classification overridden successfully.");
    } catch (err: unknown) {
      console.error("Failed to override classification:", err);
      const message = extractErrorMessage(err, "Unable to override classification.");
      setError(message);
      toast.error(message);
    } finally {
      setOverriding(false);
    }
  }, [assessmentId, selectedResult, overrideClassification, overrideReason, loadDashboard]);

  if (loading) {
    return (
      <AppShell
        title="Materiality Scoring"
        description="Calculate, review and validate materiality results for your ESG assessment."
      >
        <Toaster richColors position="top-right" />
        <div className="flex min-h-[500px] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
            <p className="text-sm text-muted-foreground">Loading scoring dashboard...</p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!assessment) {
    return (
      <AppShell
        title="Materiality Scoring"
        description="Calculate, review and validate materiality results."
      >
        <Toaster richColors position="top-right" />
        <Alert>
          <CircleAlert className="h-4 w-4" />
          <AlertTitle>Assessment not found</AlertTitle>
          <AlertDescription>
            The requested materiality assessment could not be loaded.
          </AlertDescription>
        </Alert>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Materiality Scoring"
      description="Calculate, review and validate materiality results for your ESG assessment."
    >
      {/* Toaster is mounted here (scoped to this page) since AppShell is left untouched */}
      <Toaster richColors position="top-right" />

      {/*
        Containment wrapper: this is what actually stops the page-level
        horizontal scrollbar. min-w-0 lets this block shrink inside
        AppShell's flex layout instead of stretching to fit the wide
        table below it, and overflow-x-hidden is the hard backstop so
        nothing inside can force the page wider than the viewport.
        The scoring table keeps its own internal overflow-x-auto, so
        it still scrolls horizontally *within itself* when needed —
        only the outer page stays fixed.
      */}
      <div className="w-full min-w-0 max-w-full overflow-x-hidden space-y-6">
        <DashboardHeader
          assessment={assessment}
          isDoubleMode={isDoubleMode}
          refreshing={refreshing}
          savingInternal={savingInternal}
          runningScoring={runningScoring}
          onBack={() => navigate("/materiality/assessments")}
          onRefresh={handleManualRefresh}
          onSaveInternal={handleSaveInternalScores}
          onRunScoring={() => setRunDialogOpen(true)}
        />

        {error && (
          <Alert variant="destructive" className="border-red-200 bg-red-50">
            <CircleAlert className="h-4 w-4" />
            <AlertTitle>Scoring operation failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <KpiGrid kpis={kpis} scoringProgress={scoringProgress} />

        <StatusCard
          isDoubleMode={isDoubleMode}
          lastScoreRun={lastScoreRun}
          scoringProgress={scoringProgress}
          kpis={kpis}
        />

        <ModeBanner isDoubleMode={isDoubleMode} />

        {/*
          No tabs — both sections are shown stacked, one after another,
          so nothing is ever hidden behind a tab click and nothing ends
          up misaligned to one side the way the tab list did.
        */}
        <div className="min-w-0 space-y-6">
          {isDoubleMode && (
            <InternalScoringCard
              results={results}
              savingInternal={savingInternal}
              onSave={handleSaveInternalScores}
              getInternalScore={getInternalScore}
              updateInternalField={updateInternalField}
              updateImpactType={updateImpactType}
              updateRationale={updateRationale}
            />
          )}

          <ResultsCard
            results={results}
            onRunScoring={() => setRunDialogOpen(true)}
            onOpenDetails={handleOpenDetails}
            onOpenOverride={handleOpenOverride}
          />
        </div>
      </div>

      <RunScoringDialog
        open={runDialogOpen}
        onOpenChange={setRunDialogOpen}
        isDoubleMode={isDoubleMode}
        kpis={kpis}
        runningScoring={runningScoring}
        onConfirm={handleRunScoring}
      />

      <OverrideDialog
        open={overrideDialogOpen}
        onOpenChange={setOverrideDialogOpen}
        isDoubleMode={isDoubleMode}
        selectedResult={selectedResult}
        overrideClassification={overrideClassification}
        overrideReason={overrideReason}
        overriding={overriding}
        setOverrideClassification={setOverrideClassification}
        setOverrideReason={setOverrideReason}
        onConfirm={handleOverride}
      />

      <ScoreDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        isDoubleMode={isDoubleMode}
        selectedResult={selectedResult}
      />
    </AppShell>
  );
}

// ==================================================================
// Helpers
// ==================================================================

function extractErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const message = err.response?.data?.detail ?? err.response?.data?.message;
    return typeof message === "string" ? message : fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

function getClassificationBadge(classification: string) {
  switch (classification) {
    case "DOUBLE_MATERIAL":
      return (
        <Badge className="border border-purple-200 bg-purple-50 text-purple-700">
          Double Material
        </Badge>
      );
    case "IMPACT_MATERIAL":
      return (
        <Badge className="border border-blue-200 bg-blue-50 text-blue-700">
          Impact Material
        </Badge>
      );
    case "FINANCIAL_MATERIAL":
      return (
        <Badge className="border border-amber-200 bg-amber-50 text-amber-700">
          Financial Material
        </Badge>
      );
    case "MATERIAL":
      return (
        <Badge className="border border-emerald-200 bg-emerald-50 text-emerald-700">
          Material
        </Badge>
      );
    case "MONITOR":
      return (
        <Badge className="border border-orange-200 bg-orange-50 text-orange-700">Monitor</Badge>
      );
    case "NOT_MATERIAL":
      return <Badge variant="secondary">Not Material</Badge>;
    case "INSUFFICIENT_DATA":
      return (
        <Badge variant="outline" className="border-slate-300 text-slate-500">
          Insufficient Data
        </Badge>
      );
    default:
      return <Badge variant="secondary">{classification}</Badge>;
  }
}

// ==================================================================
// Header
// ==================================================================

function DashboardHeader({
  assessment,
  isDoubleMode,
  refreshing,
  savingInternal,
  runningScoring,
  onBack,
  onRefresh,
  onSaveInternal,
  onRunScoring,
}: {
  assessment: MaterialityAssessment;
  isDoubleMode: boolean;
  refreshing: boolean;
  savingInternal: boolean;
  runningScoring: boolean;
  onBack: () => void;
  onRefresh: () => void;
  onSaveInternal: () => void;
  onRunScoring: () => void;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <Button type="button" variant="ghost" size="icon" className="mt-1 shrink-0" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-2xl font-semibold tracking-tight text-slate-900">
              {assessment.name}
            </h1>
            <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
              {isDoubleMode ? "Double Materiality" : "Single Materiality"}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Review stakeholder results, internal expert scoring and final materiality
            classifications.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" disabled={refreshing} onClick={onRefresh}>
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>

        {isDoubleMode && (
          <Button type="button" variant="outline" onClick={onSaveInternal} disabled={savingInternal}>
            {savingInternal ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Expert Scores
          </Button>
        )}

        <Button
          type="button"
          onClick={onRunScoring}
          disabled={runningScoring}
          className="bg-emerald-600 hover:bg-emerald-700"
        >
          <Calculator className="mr-2 h-4 w-4" />
          Run Scoring
        </Button>
      </div>
    </div>
  );
}

// ==================================================================
// KPI grid
// ==================================================================

function KpiGrid({
  kpis,
  scoringProgress,
}: {
  kpis: { totalTopics: number; scoredTopics: number; materialTopics: number; overriddenTopics: number };
  scoringProgress: number;
}) {
  return (
    <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card className="min-w-0 border-slate-200 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Topics</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpis.totalTopics}</p>
            </div>
            <div className="rounded-xl bg-slate-100 p-3">
              <Target className="h-5 w-5 text-slate-700" />
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Sub-topics included in this assessment
          </p>
        </CardContent>
      </Card>

      <Card className="min-w-0 border-slate-200 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Scored Topics</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpis.scoredTopics}</p>
            </div>
            <div className="rounded-xl bg-blue-50 p-3">
              <FileCheck2 className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <div className="mt-3">
            <Progress value={scoringProgress} className="h-1.5" />
            <p className="mt-2 text-xs text-muted-foreground">
              {scoringProgress}% scoring completion
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="min-w-0 border-slate-200 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Material Topics</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpis.materialTopics}</p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Topics meeting materiality criteria</p>
        </CardContent>
      </Card>

      <Card className="min-w-0 border-slate-200 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Manual Overrides</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpis.overriddenTopics}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-3">
              <ShieldCheck className="h-5 w-5 text-amber-600" />
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Manager-reviewed classifications</p>
        </CardContent>
      </Card>
    </div>
  );
}

// ==================================================================
// Status card
// ==================================================================

function StatusCard({
  isDoubleMode,
  lastScoreRun,
  scoringProgress,
  kpis,
}: {
  isDoubleMode: boolean;
  lastScoreRun: ScoreRun | null;
  scoringProgress: number;
  kpis: { totalTopics: number; scoredTopics: number };
}) {
  return (
    <Card className="min-w-0 border-slate-200 shadow-sm">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between px-4">
          <div>
            <CardTitle className="text-lg">Scoring Status</CardTitle>
            <CardDescription>Current readiness of the materiality assessment.</CardDescription>
          </div>
          <Badge
            variant="outline"
            className={
              scoringProgress === 100
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-amber-200 bg-amber-50 text-amber-700"
            }
          >
            {scoringProgress === 100 ? "Ready" : "In Progress"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid gap-6 md:grid-cols-3  px-4">
          <div className="flex items-start gap-3 ">
            <div className="rounded-lg bg-blue-50 p-2  ">
              <Users className="h-4 w-4 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">Stakeholder Assessment</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Survey responses are aggregated using stakeholder group weights.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-purple-50 p-2">
              <ShieldCheck className="h-4 w-4 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">Internal Expert Review</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {isDoubleMode
                  ? "Expert impact and financial assessments are enabled."
                  : "Internal expert scoring is only available in Double Materiality mode."}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-emerald-50 p-2">
              <Clock3 className="h-4 w-4 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">Latest Score Run</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {lastScoreRun?.run_at
                  ? new Date(lastScoreRun.run_at).toLocaleString()
                  : "No scoring run recorded yet"}
              </p>
            </div>
          </div>
        </div>

        <Separator className="my-5" />

        <div className="space-y-2 px-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Scoring completion</span>
            <span className="text-muted-foreground">
              {kpis.scoredTopics} / {kpis.totalTopics}
            </span>
          </div>
          <Progress value={scoringProgress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}

// ==================================================================
// Mode banner
// ==================================================================

function ModeBanner({ isDoubleMode }: { isDoubleMode: boolean }) {
  return (
    <Card
      className={
        isDoubleMode
          ? "min-w-0 border-purple-200 bg-purple-50/40 shadow-sm"
          : "min-w-0 border-blue-200 bg-blue-50/40 shadow-sm"
      }
    >
      <CardContent className="p-5">
        <div className="flex gap-4">
          <div className={isDoubleMode ? "rounded-xl bg-purple-100 p-3" : "rounded-xl bg-blue-100 p-3"}>
            {isDoubleMode ? (
              <ShieldCheck className="h-5 w-5 text-purple-700" />
            ) : (
              <Target className="h-5 w-5 text-blue-700" />
            )}
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-900">
              {isDoubleMode ? "Double Materiality Scoring" : "Single Materiality Scoring"}
            </h3>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {isDoubleMode
                ? "Survey stakeholder results are combined with internal expert assessment. The backend blends impact and financial perspectives according to the configured internal blend weight before assigning the final classification."
                : "Stakeholder survey results are aggregated and evaluated against the configured materiality thresholds to determine the final classification."}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ==================================================================
// Internal expert scoring section (no longer a tab)
// ==================================================================

function InternalScoringCard({
  results,
  savingInternal,
  onSave,
  getInternalScore,
  updateInternalField,
  updateImpactType,
  updateRationale,
}: {
  results: MaterialityResult[];
  savingInternal: boolean;
  onSave: () => void;
  getInternalScore: (topicId: string) => Partial<InternalScore>;
  updateInternalField: (topicId: string, field: ScoreField, value: number) => void;
  updateImpactType: (topicId: string, value: "ACTUAL" | "POTENTIAL") => void;
  updateRationale: (topicId: string, value: string) => void;
}) {
  return (
    <Card className="min-w-0 border-slate-200 shadow-sm">
      <CardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Internal Expert Assessment</CardTitle>
            <CardDescription>
              Evaluate the severity and financial significance of each sub-topic.
            </CardDescription>
          </div>
          <Button type="button" onClick={onSave} disabled={savingInternal}>
            {savingInternal ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Expert Assessment
          </Button>
        </div>
      </CardHeader>

      <CardContent className="min-w-0">
        <Alert className="mb-5 border-purple-200 bg-purple-50">
          <ShieldCheck className="h-4 w-4 text-purple-700" />
          <AlertTitle>How expert scoring works</AlertTitle>
          <AlertDescription>
            Scale, Scope and Irremediability determine impact severity. Likelihood is used for
            potential impacts. Financial Magnitude and Financial Likelihood determine the
            financial score. The backend performs the final calculations and blending.
          </AlertDescription>
        </Alert>

        {/*
          This is the only element on the page that should ever scroll
          horizontally — it has its own bounded scroll container so the
          wide table (9 columns with min-widths) never pushes the rest
          of the page out of view.
        */}
        <div className="w-full min-w-0 max-w-full overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead className="min-w-[220px]">Sub-topic</TableHead>
                <TableHead className="min-w-[130px]">Impact Type</TableHead>
                <TableHead className="min-w-[110px] text-center">Scale</TableHead>
                <TableHead className="min-w-[110px] text-center">Scope</TableHead>
                <TableHead className="min-w-[140px] text-center">Irremediability</TableHead>
                <TableHead className="min-w-[120px] text-center">Likelihood</TableHead>
                <TableHead className="min-w-[160px] text-center">Financial Magnitude</TableHead>
                <TableHead className="min-w-[170px] text-center">Financial Likelihood</TableHead>
                <TableHead className="min-w-[250px]">Rationale</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {results.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">
                    No assessment topics are available.
                  </TableCell>
                </TableRow>
              ) : (
                results.map((result) => {
                  const topicId = result.assessment_topic;
                  const score = getInternalScore(topicId);
                  const impactType = score.impact_type ?? "ACTUAL";

                  return (
                    <TableRow key={topicId} className="align-top">
                      <TableCell>
                        <p className="font-medium text-slate-900">
                          {result.subtopic_name ?? "Assessment Topic"}
                        </p>
                        {result.subtopic_code && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {result.subtopic_code}
                          </p>
                        )}
                      </TableCell>

                      <TableCell>
                        <Select
                          value={impactType}
                          onValueChange={(value) =>
                            updateImpactType(topicId, value as "ACTUAL" | "POTENTIAL")
                          }
                        >
                          <SelectTrigger className="w-[120px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-white">
                            <SelectItem value="ACTUAL">Actual</SelectItem>
                            <SelectItem value="POTENTIAL">Potential</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>

                      <ScoreSelectCell
                        width="w-[90px]"
                        value={score.scale}
                        onChange={(value) => updateInternalField(topicId, "scale", value)}
                      />
                      <ScoreSelectCell
                        width="w-[90px]"
                        value={score.scope}
                        onChange={(value) => updateInternalField(topicId, "scope", value)}
                      />
                      <ScoreSelectCell
                        width="w-[90px]"
                        value={score.irremediability}
                        onChange={(value) => updateInternalField(topicId, "irremediability", value)}
                      />
                      <ScoreSelectCell
                        width="w-[90px]"
                        value={score.likelihood}
                        disabled={impactType !== "POTENTIAL"}
                        placeholder={impactType === "ACTUAL" ? "N/A" : "1–5"}
                        onChange={(value) => updateInternalField(topicId, "likelihood", value)}
                      />
                      <ScoreSelectCell
                        width="w-[110px]"
                        value={score.financial_magnitude}
                        onChange={(value) =>
                          updateInternalField(topicId, "financial_magnitude", value)
                        }
                      />
                      <ScoreSelectCell
                        width="w-[110px]"
                        value={score.financial_likelihood}
                        onChange={(value) =>
                          updateInternalField(topicId, "financial_likelihood", value)
                        }
                      />

                      <TableCell>
                        <Textarea
                          value={score.rationale ?? ""}
                          onChange={(event) => updateRationale(topicId, event.target.value)}
                          placeholder="Explain the evidence or judgement supporting this score..."
                          className="min-h-[80px] min-w-[230px] resize-none"
                        />
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreSelectCell({
  value,
  onChange,
  width,
  disabled,
  placeholder = "1–5",
}: {
  value: number | null | undefined;
  onChange: (value: number) => void;
  width: string;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <TableCell>
      <Select
        disabled={disabled}
        value={value ? String(value) : ""}
        onValueChange={(value) => onChange(Number(value))}
      >
        <SelectTrigger className={width}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="bg-white">
          {SCALE_OPTIONS.map((option) => (
            <SelectItem key={option} value={String(option)}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </TableCell>
  );
}

// ==================================================================
// Results section (no longer a tab)
// ==================================================================

function ResultsCard({
  results,
  onRunScoring,
  onOpenDetails,
  onOpenOverride,
}: {
  results: MaterialityResult[];
  onRunScoring: () => void;
  onOpenDetails: (result: MaterialityResult) => void;
  onOpenOverride: (result: MaterialityResult) => void;
}) {
  return (
    <Card className="min-w-0 border-slate-200 shadow-sm px-4">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Materiality Results</CardTitle>
            <CardDescription>
              Final scores and classifications returned by the scoring engine.
            </CardDescription>
          </div>
          <Badge variant="outline" className="w-fit">
            Backend calculated
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="min-w-0">
        {results.length === 0 ? (
          <div className="flex min-h-[250px] flex-col items-center justify-center text-center">
            <div className="rounded-full bg-slate-100 p-4">
              <Calculator className="h-6 w-6 text-slate-500" />
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">No scoring results yet</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Complete the required survey and internal expert assessment, then run scoring to
              generate materiality results.
            </p>
            <Button
              type="button"
              className="mt-4 bg-emerald-600 hover:bg-emerald-700"
              onClick={onRunScoring}
            >
              <Calculator className="mr-2 h-4 w-4" />
              Run Scoring
            </Button>
          </div>
        ) : (
          <div className="w-full min-w-0 max-w-full overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>Sub-topic</TableHead>
                  <TableHead className="text-center">Primary</TableHead>
                  <TableHead className="text-center">Secondary</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {results.map((result) => (
                  <TableRow key={result.assessment_topic}>
                    <TableCell>
                      <p className="font-medium text-slate-900">
                        {result.subtopic_name ?? "Assessment Topic"}
                      </p>
                      {result.subtopic_code && (
                        <p className="mt-1 max-w-md truncate text-xs text-muted-foreground">
                          {result.subtopic_code}
                        </p>
                      )}
                    </TableCell>

                    <TableCell className="text-center">
                      <span className="font-semibold text-slate-900">
                        {result.primary_score ?? "—"}
                      </span>
                    </TableCell>

                    <TableCell className="text-center">
                      <span className="font-semibold text-slate-900">
                        {result.secondary_score ?? "—"}
                      </span>
                    </TableCell>

                    <TableCell>{getClassificationBadge(result.classification)}</TableCell>

                    <TableCell>
                      {result.is_override ? (
                        <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
                          <ShieldCheck className="mr-1 h-3 w-3" />
                          Overridden
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="border-slate-200">
                          System Result
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button type="button" variant="outline" size="sm" className="h-8 gap-2">
                            Actions
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-white">
                          <DropdownMenuItem onClick={() => onOpenDetails(result)}>
                            View Score Details
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => onOpenOverride(result)}>
                            Override Classification
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ==================================================================
// Run scoring dialog — centered, solid white background
// ==================================================================

function RunScoringDialog({
  open,
  onOpenChange,
  isDoubleMode,
  kpis,
  runningScoring,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isDoubleMode: boolean;
  kpis: { totalTopics: number; scoredTopics: number; overriddenTopics: number };
  runningScoring: boolean;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={`sm:max-w-[500px] ${DIALOG_CONTENT_CLASS}`}>
        <DialogHeader>
          <DialogTitle>Run Materiality Scoring</DialogTitle>
          <DialogDescription>
            The scoring engine will calculate the latest materiality results using the current
            assessment configuration.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert className="border-emerald-200 bg-emerald-50">
            <Calculator className="h-4 w-4 text-emerald-700" />
            <AlertTitle>{isDoubleMode ? "Double Materiality" : "Single Materiality"}</AlertTitle>
            <AlertDescription>
              {isDoubleMode
                ? "Stakeholder survey scores will be combined with internal expert impact and financial scores according to the configured blend weight."
                : "Stakeholder survey scores will be aggregated using the configured stakeholder group weights."}
            </AlertDescription>
          </Alert>

          <div className="rounded-lg border bg-slate-50 p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Topics</p>
                <p className="mt-1 font-semibold text-slate-900">{kpis.totalTopics}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Scored</p>
                <p className="mt-1 font-semibold text-slate-900">{kpis.scoredTopics}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Mode</p>
                <p className="mt-1 font-semibold text-slate-900">
                  {isDoubleMode ? "Double" : "Single"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Current Overrides</p>
                <p className="mt-1 font-semibold text-slate-900">{kpis.overriddenTopics}</p>
              </div>
            </div>
          </div>

          <p className="text-xs leading-5 text-muted-foreground">
            A new score run will create a historical snapshot. Existing manual overrides will
            remain preserved.
          </p>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={runningScoring}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="bg-emerald-600 hover:bg-emerald-700"
            onClick={onConfirm}
            disabled={runningScoring}
          >
            {runningScoring ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Calculator className="mr-2 h-4 w-4" />
                Run Scoring
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================================================================
// Override dialog — centered, solid white background
// ==================================================================

function OverrideDialog({
  open,
  onOpenChange,
  isDoubleMode,
  selectedResult,
  overrideClassification,
  overrideReason,
  overriding,
  setOverrideClassification,
  setOverrideReason,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isDoubleMode: boolean;
  selectedResult: MaterialityResult | null;
  overrideClassification: Classification | "";
  overrideReason: string;
  overriding: boolean;
  setOverrideClassification: (value: Classification | "") => void;
  setOverrideReason: (value: string) => void;
  onConfirm: () => void;
}) {
  const reasonLength = overrideReason.trim().length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={`sm:max-w-[520px] ${DIALOG_CONTENT_CLASS}`}>
        <DialogHeader>
          <DialogTitle>Override Classification</DialogTitle>
          <DialogDescription>
            Manually promote or demote this topic's system-generated classification.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {selectedResult && (
            <div className="rounded-lg border bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Selected Topic
              </p>
              <p className="mt-1 font-semibold text-slate-900">
                {selectedResult.subtopic_name ?? "Assessment Topic"}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">Current classification:</span>
                {getClassificationBadge(selectedResult.classification)}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="override-classification">New Classification</Label>
            <Select
              value={overrideClassification}
              onValueChange={(value) => setOverrideClassification(value as Classification)}
            >
              <SelectTrigger id="override-classification">
                <SelectValue placeholder="Select classification" />
              </SelectTrigger>
              <SelectContent className="bg-white">
                {isDoubleMode ? (
                  <>
                    <SelectItem value="DOUBLE_MATERIAL">Double Material</SelectItem>
                    <SelectItem value="IMPACT_MATERIAL">Impact Material</SelectItem>
                    <SelectItem value="FINANCIAL_MATERIAL">Financial Material</SelectItem>
                    <SelectItem value="NOT_MATERIAL">Not Material</SelectItem>
                  </>
                ) : (
                  <>
                    <SelectItem value="MATERIAL">Material</SelectItem>
                    <SelectItem value="MONITOR">Monitor</SelectItem>
                    <SelectItem value="NOT_MATERIAL">Not Material</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="override-reason">
              Override Reason
              <span className="ml-1 text-red-500">*</span>
            </Label>
            <Textarea
              id="override-reason"
              value={overrideReason}
              onChange={(event) => setOverrideReason(event.target.value)}
              placeholder="Explain why the ESG manager is overriding the calculated classification..."
              className="min-h-[120px] resize-none"
            />
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Minimum 20 characters required.</p>
              <p
                className={`text-xs ${
                  reasonLength >= 20 ? "text-emerald-600" : "text-muted-foreground"
                }`}
              >
                {reasonLength}/20
              </p>
            </div>
          </div>

          <Alert className="border-amber-200 bg-amber-50">
            <ShieldAlert className="h-4 w-4 text-amber-700" />
            <AlertTitle>Audit trail</AlertTitle>
            <AlertDescription>
              This override will be recorded against the current user and will remain visible
              after future scoring runs.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={overriding}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="bg-amber-600 hover:bg-amber-700"
            onClick={onConfirm}
            disabled={overriding || reasonLength < 20 || !overrideClassification}
          >
            {overriding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <ShieldCheck className="mr-2 h-4 w-4" />
                Apply Override
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================================================================
// Score detail — now a centered Dialog (was a transparent side Sheet)
// ==================================================================

function ScoreDetailDialog({
  open,
  onOpenChange,
  isDoubleMode,
  selectedResult,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isDoubleMode: boolean;
  selectedResult: MaterialityResult | null;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={`max-h-[85vh] overflow-y-auto sm:max-w-xl ${DIALOG_CONTENT_CLASS}`}
      >
        <DialogHeader>
          <DialogTitle>Score Details</DialogTitle>
          <DialogDescription>
            Detailed scoring information for the selected materiality topic.
          </DialogDescription>
        </DialogHeader>

        {selectedResult && (
          <div className="space-y-6 py-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Sub-topic
              </p>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">
                {selectedResult.subtopic_name ?? "Assessment Topic"}
              </h3>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground">Primary Score</p>
                <p className="mt-2 text-2xl font-semibold">
                  {selectedResult.primary_score ?? "—"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Impact dimension</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground">Secondary Score</p>
                <p className="mt-2 text-2xl font-semibold">
                  {selectedResult.secondary_score ?? "—"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Financial dimension</p>
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium text-slate-900">Final Classification</p>
              <div className="mt-3">{getClassificationBadge(selectedResult.classification)}</div>
            </div>

            {/*
              Stakeholder group survey results — per-dimension breakdown
              of what each stakeholder group actually reported, plus the
              weight that was applied to them. Read-only, backend-computed
              snapshot from the score run (group_breakdown on
              ScoreRunTopic). Added as its own section inside this
              existing dialog — no new dialogs, tabs, or page elements.
            */}
            <StakeholderBreakdownSection groupBreakdown={selectedResult.group_breakdown} />

            {isDoubleMode && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-slate-900">
                    Double Materiality Interpretation
                  </h4>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                    The primary score represents the impact perspective while the secondary score
                    represents the financial perspective. Both are evaluated against the
                    configured materiality threshold.
                  </p>
                </div>

                <div className="grid gap-3">
                  <div className="flex items-start gap-3 rounded-lg bg-blue-50 p-3">
                    <Target className="mt-0.5 h-4 w-4 text-blue-600" />
                    <div>
                      <p className="text-sm font-medium text-blue-900">Impact Materiality</p>
                      <p className="text-xs leading-5 text-blue-800/80">
                        Determines whether the topic represents a significant impact on people or
                        the environment.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-3">
                    <TrendingUp className="mt-0.5 h-4 w-4 text-amber-600" />
                    <div>
                      <p className="text-sm font-medium text-amber-900">Financial Materiality</p>
                      <p className="text-xs leading-5 text-amber-800/80">
                        Determines whether the topic can create a significant financial effect for
                        the organization.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {selectedResult.is_override && (
              <Alert className="border-amber-200 bg-amber-50">
                <ShieldCheck className="h-4 w-4 text-amber-700" />
                <AlertTitle>Manual Override Applied</AlertTitle>
                <AlertDescription>
                  This classification has been manually changed by an ESG manager and is
                  protected from being replaced by a normal score recalculation.
                </AlertDescription>
              </Alert>
            )}

            <div className="rounded-lg border bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Scoring Governance
              </p>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Score source</span>
                  <span className="font-medium">Backend scoring engine</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Override status</span>
                  <span className="font-medium">
                    {selectedResult.is_override ? "Overridden" : "System calculated"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==================================================================
// Stakeholder group survey results — used inside ScoreDetailDialog
// ==================================================================

function StakeholderBreakdownSection({
  groupBreakdown,
}: {
  groupBreakdown?: Record<string, GroupBreakdownEntry[]>;
}) {
  const dimensions = groupBreakdown ? Object.keys(groupBreakdown) : [];

  if (dimensions.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2">
        <Users className="h-4 w-4 text-blue-600" />
        <p className="text-sm font-medium text-slate-900">Stakeholder Group Results</p>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Weighted survey responses by stakeholder group for this topic, snapshotted at the time
        scoring was last run.
      </p>

      <div className="mt-4 space-y-4">
        {dimensions.map((dimension) => {
          const entries = groupBreakdown?.[dimension] ?? [];
          if (entries.length === 0) return null;

          return (
            <div key={dimension}>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {DIMENSION_LABELS[dimension] ?? dimension}
              </p>

              <div className="mt-2 w-full min-w-0 max-w-full overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead className="min-w-[140px]">Stakeholder Group</TableHead>
                      <TableHead className="text-center">Weight</TableHead>
                      <TableHead className="text-center">Responses</TableHead>
                      <TableHead className="text-center">Average</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entries.map((entry) => (
                      <TableRow key={entry.group_id}>
                        <TableCell className="font-medium text-slate-900">
                          {entry.group_name}
                        </TableCell>
                        <TableCell className="text-center">{entry.weight}%</TableCell>
                        <TableCell className="text-center">{entry.response_count}</TableCell>
                        <TableCell className="text-center">
                          {entry.average ?? (
                            <span className="text-xs text-muted-foreground">No responses</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}