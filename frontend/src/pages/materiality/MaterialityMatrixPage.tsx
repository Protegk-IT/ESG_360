import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { toPng } from "html-to-image";

import {
  AlertCircle,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  History,
  ImageIcon,
  Layers,
  RefreshCw,
  RotateCcw,
  Target,
  X,
} from "lucide-react";

import api from "@/services/api";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import ScoringApi from "@/api/materiality/ScoringApi";

import type { MaterialityAssessment } from "@/types/materiality/assessment";

import type {
  MaterialityClassification,
  MaterialityResult,
  ScoreRunDetail,
  ScoreRunResultsResponse,
  ScoreRunTopicResult,
} from "@/types/materiality/scoring";

import AppShell from "@/components/layout/AppShell";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

/* ============================================================
   NPM PACKAGES REQUIRED (install before using this file)
   npm install echarts echarts-for-react html-to-image
============================================================ */

/* ============================================================
   CONSTANTS
============================================================ */

const DEFAULT_THRESHOLD = 3;
const MATRIX_MIN = 1;
const MATRIX_MAX = 5;
const ESG_SCORE_METHOD = "1.0";
const ESG_ACCENT = "#059669"; // emerald-600, matches sidebar

/* ============================================================
   CLASSIFICATION HELPERS
============================================================ */

function getClassificationLabel(classification: MaterialityClassification): string {
  switch (classification) {
    case "MATERIAL":
      return "Material";
    case "MONITOR":
      return "Monitor";
    case "NOT_MATERIAL":
      return "Not Material";
    case "DOUBLE_MATERIAL":
      return "Double Material";
    case "IMPACT_MATERIAL":
      return "Impact Material";
    case "FINANCIAL_MATERIAL":
      return "Financial Material";
    case "INSUFFICIENT_DATA":
      return "Insufficient Data";
    default:
      return "Unknown";
  }
}

function getClassificationDotColor(classification: MaterialityClassification): string {
  switch (classification) {
    case "MATERIAL":
    case "DOUBLE_MATERIAL":
      return "#ef4444";
    case "MONITOR":
    case "IMPACT_MATERIAL":
    case "FINANCIAL_MATERIAL":
      return "#f59e0b";
    case "NOT_MATERIAL":
      return "#22c55e";
    case "INSUFFICIENT_DATA":
    default:
      return "#9ca3af";
  }
}

const LEGEND_ITEMS = [
  { label: "Material", color: "#ef4444" },
  { label: "Monitor", color: "#f59e0b" },
  { label: "Not Material", color: "#22c55e" },
  { label: "Insufficient Data", color: "#9ca3af" },
] as const;

function calculatePreviewClassification(
  mode: string,
  primary: number,
  secondary: number,
  primaryThreshold: number,
  secondaryThreshold: number,
): MaterialityClassification {
  if (!Number.isFinite(primary) || !Number.isFinite(secondary)) return "INSUFFICIENT_DATA";

  const primaryMaterial = primary >= primaryThreshold;
  const secondaryMaterial = secondary >= secondaryThreshold;

  if (mode === "SINGLE") {
    if (primaryMaterial && secondaryMaterial) return "MATERIAL";
    if (primaryMaterial || secondaryMaterial) return "MONITOR";
    return "NOT_MATERIAL";
  }

  if (primaryMaterial && secondaryMaterial) return "DOUBLE_MATERIAL";
  if (primaryMaterial) return "IMPACT_MATERIAL";
  if (secondaryMaterial) return "FINANCIAL_MATERIAL";
  return "NOT_MATERIAL";
}

/* ============================================================
   ERROR / NUMBER HELPERS
============================================================ */

function extractErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null) {
    const possible = error as {
      response?: { data?: { detail?: unknown; message?: unknown; errors?: unknown } };
      message?: unknown;
    };
    const detail = possible.response?.data?.detail;
    if (typeof detail === "string") return detail;
    const message = possible.response?.data?.message;
    if (typeof message === "string") return message;
    const errors = possible.response?.data?.errors;
    if (Array.isArray(errors) && typeof errors[0] === "string") return errors[0];
    if (typeof possible.message === "string") return possible.message;
  }
  return fallback;
}

function numericValue(value: number | string | null | undefined): number {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : 0;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

/* ============================================================
   SCORE RUN HISTORY (GET /assessments/{id}/score-runs/)
============================================================ */

interface ScoreRunHistoryItem {
  id: string | number;
  run_at: string;
  response_count?: number | null;
  invited_count?: number | null;
  method_version?: string | number | null;
}

/* ============================================================
   ANIMATION STYLES
============================================================ */

function MatrixAnimationStyles() {
  return (
    <style>{`
      @keyframes mm-fade-up {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .mm-fade-up { animation: mm-fade-up 0.45s ease-out both; }
      @media (prefers-reduced-motion: reduce) {
        .mm-fade-up { animation: none !important; }
      }
    `}</style>
  );
}

/* ============================================================
   MAIN PAGE
============================================================ */

interface DotDatum {
  id: string | number;
  primary_score: number;
  secondary_score: number;
  subtopic_name: string | null;
  subtopic_code: string | null;
  previewClassification: MaterialityClassification;
}

export default function MaterialityMatrixPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();

  const [assessment, setAssessment] = useState<MaterialityAssessment | null>(null);
  const [scoreRun, setScoreRun] = useState<ScoreRunDetail | null>(null);
  const [results, setResults] = useState<MaterialityResult[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningScoring, setRunningScoring] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingPng, setExportingPng] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [primaryThreshold, setPrimaryThreshold] = useState(DEFAULT_THRESHOLD);
  const [secondaryThreshold, setSecondaryThreshold] = useState(DEFAULT_THRESHOLD);

  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyRuns, setHistoryRuns] = useState<ScoreRunHistoryItem[] | null>(null);

  const chartRef = useRef<ReactECharts | null>(null);
  const matrixCardRef = useRef<HTMLDivElement | null>(null);
  const chartWrapperRef = useRef<HTMLDivElement | null>(null);

  const assessmentMode = assessment?.mode ?? "SINGLE";
  const isDoubleMode = assessmentMode === "DOUBLE";

  const loadDashboard = useCallback(
    async (refresh = false) => {
      if (!assessmentId) return;
      try {
        setError(null);
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        refresh ? setRefreshing(true) : setLoading(true);

        const [assessmentResponse, resultsResponse] = await Promise.all([
          AssessmentApi.getById(assessmentId),
          ScoringApi.getResults(assessmentId),
        ]);

        setAssessment(assessmentResponse.data);

        const resultsData = resultsResponse.data as ScoreRunResultsResponse;
        const topicResults = Array.isArray(resultsData.topic_results) ? resultsData.topic_results : [];

        const loadedResults: MaterialityResult[] = topicResults.map((topic: ScoreRunTopicResult) => ({
          id: topic.id,
          assessment_topic: topic.assessment_topic,
          subtopic_name: topic.subtopic_name,
          subtopic_code: topic.subtopic_code,
          category_code: topic.category_code,
          primary_score: numericValue(topic.primary_score),
          secondary_score: numericValue(topic.secondary_score),
          classification: topic.classification,
          is_override: topic.is_override,
          override_reason: topic.override_reason,
          group_breakdown: topic.group_breakdown,
        }));

        setResults(loadedResults);

        if ("run_at" in resultsData && Array.isArray(resultsData.topic_results)) {
          setScoreRun(resultsData as ScoreRunDetail);
          const thresholds = resultsData.thresholds_snapshot;
          if (typeof thresholds === "object" && thresholds !== null) {
            const primary = Number(thresholds.primary_threshold);
            const secondary = Number(thresholds.secondary_threshold);
            if (Number.isFinite(primary)) setPrimaryThreshold(primary);
            if (Number.isFinite(secondary)) setSecondaryThreshold(secondary);
          }
        } else {
          setScoreRun(null);
        }
      } catch (err: unknown) {
        console.error("Failed to load materiality matrix:", err);
        setError(extractErrorMessage(err, "Unable to load materiality matrix."));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [assessmentId],
  );

  useEffect(() => {
    if (!assessmentId) return;
    void loadDashboard();
  }, [assessmentId, loadDashboard]);

  // Keep the chart correctly sized when the sidebar collapses/expands
  // or the window resizes — ResizeObserver catches container changes
  // that a plain window "resize" listener misses.
  useEffect(() => {
    const node = chartWrapperRef.current;
    if (!node) return;

    const observer = new ResizeObserver(() => {
      chartRef.current?.getEchartsInstance().resize();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const previewResults: DotDatum[] = useMemo(() => {
    return results.map((result) => ({
      id: result.id,
      primary_score: numericValue(result.primary_score),
      secondary_score: numericValue(result.secondary_score),
      subtopic_name: result.subtopic_name ?? null,
      subtopic_code: result.subtopic_code ?? null,
      previewClassification: calculatePreviewClassification(
        assessmentMode,
        numericValue(result.primary_score),
        numericValue(result.secondary_score),
        primaryThreshold,
        secondaryThreshold,
      ),
    }));
  }, [results, assessmentMode, primaryThreshold, secondaryThreshold]);

  const thresholdChanged =
    scoreRun !== null &&
    (primaryThreshold !== numericValue(scoreRun.thresholds_snapshot.primary_threshold) ||
      secondaryThreshold !== numericValue(scoreRun.thresholds_snapshot.secondary_threshold));

  const primaryWord = isDoubleMode ? "Impact" : "Primary";
  const secondaryWord = isDoubleMode ? "Financial" : "Secondary";

  /* ----------------------------------------------------------
     CHART OPTION (ECharts) — quadrant shading + threshold lines
     animate smoothly on their own whenever the option updates,
     no manual CSS transition wiring needed.
  ---------------------------------------------------------- */
  const chartOption: EChartsOption = useMemo(() => {
    const seriesData = previewResults.map((d) => ({
      value: [d.secondary_score, d.primary_score],
      name: d.subtopic_name ?? "Unnamed topic",
      code: d.subtopic_code,
      classification: d.previewClassification,
      itemStyle: { color: getClassificationDotColor(d.previewClassification) },
    }));

    const axisNameStyle = { fontSize: 12, fontWeight: 600, color: "#334155" };
    const axisLabelStyle = { fontSize: 11, color: "#64748b" };
    const splitLineStyle = { lineStyle: { color: "#e2e8f0", type: "dashed" as const } };

    return {
      backgroundColor: "transparent",
      animationDurationUpdate: 500,
      animationEasingUpdate: "cubicOut",
      grid: { left: 56, right: 24, top: 24, bottom: 56, containLabel: false },
      xAxis: {
        type: "value",
        min: MATRIX_MIN,
        max: MATRIX_MAX,
        interval: 1,
        name: `${secondaryWord} Materiality →`,
        nameLocation: "middle",
        nameGap: 32,
        nameTextStyle: axisNameStyle,
        axisLabel: axisLabelStyle,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        splitLine: splitLineStyle,
      },
      yAxis: {
        type: "value",
        min: MATRIX_MIN,
        max: MATRIX_MAX,
        interval: 1,
        name: `${primaryWord} Materiality →`,
        nameLocation: "middle",
        nameGap: 40,
        nameRotate: 90,
        nameTextStyle: axisNameStyle,
        axisLabel: axisLabelStyle,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        splitLine: splitLineStyle,
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "#ffffff",
        borderColor: "#e2e8f0",
        borderWidth: 1,
        borderRadius: 12,
        padding: 0,
        extraCssText: "box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15); overflow: hidden;",
        formatter: (params: unknown) => {
          const p = params as { data: { name: string; code: string | null; classification: MaterialityClassification; value: [number, number] } };
          const color = getClassificationDotColor(p.data.classification);
          return `
            <div style="box-sizing:border-box;width:220px;max-width:220px;padding:14px 16px;font-family:inherit;white-space:normal;overflow-wrap:break-word;">
              <div style="font-size:13px;font-weight:600;line-height:1.4;color:#0f172a;">${p.data.name}</div>
              ${p.data.code ? `<div style="font-size:11px;color:#94a3b8;margin-top:3px;">${p.data.code}</div>` : ""}
              <div style="font-size:12px;color:#64748b;margin-top:8px;line-height:1.6;">${secondaryWord}: <span style="font-weight:600;color:#0f172a;">${p.data.value[0].toFixed(2)}</span></div>
              <div style="font-size:12px;color:#64748b;line-height:1.6;">${primaryWord}: <span style="font-weight:600;color:#0f172a;">${p.data.value[1].toFixed(2)}</span></div>
              <div style="font-size:12px;color:#64748b;margin-top:6px;line-height:1.6;">Classification: <span style="font-weight:600;color:${color};">${getClassificationLabel(p.data.classification)}</span></div>
            </div>
          `;
        },
      },
      series: [
        {
          type: "scatter",
          data: seriesData,
          symbolSize: 15,
          itemStyle: { borderColor: "#ffffff", borderWidth: 1.5, shadowBlur: 6, shadowColor: "rgba(15,23,42,0.15)" },
          emphasis: { scale: 1.35, itemStyle: { shadowBlur: 10 } },
          animationDuration: 550,
          animationEasing: "elasticOut",
          markArea: {
            silent: true,
            data: [
              [
                { coord: [MATRIX_MIN, primaryThreshold], itemStyle: { color: "#fef3c7", opacity: 0.55 } },
                { coord: [secondaryThreshold, MATRIX_MAX] },
              ],
              [
                { coord: [secondaryThreshold, primaryThreshold], itemStyle: { color: "#fee2e2", opacity: 0.55 } },
                { coord: [MATRIX_MAX, MATRIX_MAX] },
              ],
              [
                { coord: [MATRIX_MIN, MATRIX_MIN], itemStyle: { color: "#dcfce7", opacity: 0.55 } },
                { coord: [secondaryThreshold, primaryThreshold] },
              ],
              [
                { coord: [secondaryThreshold, MATRIX_MIN], itemStyle: { color: "#fef3c7", opacity: 0.55 } },
                { coord: [MATRIX_MAX, primaryThreshold] },
              ],
            ],
          },
          markLine: {
            silent: true,
            symbol: "none",
            label: { show: false },
            lineStyle: { color: ESG_ACCENT, type: "dashed", width: 1.5 },
            data: [{ xAxis: secondaryThreshold }, { yAxis: primaryThreshold }],
          },
        },
      ],
    };
  }, [previewResults, primaryThreshold, secondaryThreshold, primaryWord, secondaryWord]);

  const handleRunScoring = useCallback(async () => {
    if (!assessmentId) return;
    try {
      setRunningScoring(true);
      setError(null);
      await ScoringApi.runScoring(assessmentId);
      await loadDashboard(true);
    } catch (err: unknown) {
      console.error("Failed to run scoring:", err);
      setError(extractErrorMessage(err, "Unable to run scoring."));
    } finally {
      setRunningScoring(false);
    }
  }, [assessmentId, loadDashboard]);

  const handleExportCsv = useCallback(async () => {
    if (!assessmentId) return;
    try {
      setExportingCsv(true);
      setError(null);
      const response = await api.get(`/materiality/assessments/${assessmentId}/export/csv/`, {
        responseType: "blob",
      });
      downloadBlob(response.data as Blob, "materiality-results.csv");
    } catch (err: unknown) {
      console.error("CSV export failed:", err);
      setError(extractErrorMessage(err, "Unable to export CSV."));
    } finally {
      setExportingCsv(false);
    }
  }, [assessmentId]);

  const handleExportPdf = useCallback(async () => {
    if (!assessmentId) return;
    try {
      setExportingPdf(true);
      setError(null);
      const response = await api.get(`/materiality/assessments/${assessmentId}/export/pdf/`, {
        responseType: "blob",
      });
      downloadBlob(response.data as Blob, "materiality-summary.pdf");
    } catch (err: unknown) {
      console.error("PDF export failed:", err);
      setError(extractErrorMessage(err, "Unable to export PDF."));
    } finally {
      setExportingPdf(false);
    }
  }, [assessmentId]);

  const handleExportPng = useCallback(async () => {
    if (!matrixCardRef.current) return;
    try {
      setExportingPng(true);
      setError(null);
      // Rasterizes the whole card — title, legend and chart together —
      // so the exported PNG carries the same context you see on screen.
      const dataUrl = await toPng(matrixCardRef.current, {
        backgroundColor: "#ffffff",
        pixelRatio: 2,
      });
      const anchor = document.createElement("a");
      anchor.href = dataUrl;
      anchor.download = `materiality-matrix-${assessment?.name?.replace(/\s+/g, "-").toLowerCase() ?? "export"}.png`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch (err: unknown) {
      console.error("PNG export failed:", err);
      setError(extractErrorMessage(err, "Unable to export the matrix as an image."));
    } finally {
      setExportingPng(false);
    }
  }, [assessment]);

  const handleResetThresholds = useCallback(() => {
    const snapshot = scoreRun?.thresholds_snapshot;
    const primary = snapshot ? Number(snapshot.primary_threshold) : DEFAULT_THRESHOLD;
    const secondary = snapshot ? Number(snapshot.secondary_threshold) : DEFAULT_THRESHOLD;
    setPrimaryThreshold(Number.isFinite(primary) ? primary : DEFAULT_THRESHOLD);
    setSecondaryThreshold(Number.isFinite(secondary) ? secondary : DEFAULT_THRESHOLD);
  }, [scoreRun]);

  const handleToggleHistory = useCallback(async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && historyRuns === null && assessmentId) {
      try {
        setHistoryLoading(true);
        const response = await api.get(`/materiality/assessments/${assessmentId}/score-runs/`);
        setHistoryRuns(Array.isArray(response.data) ? response.data : []);
      } catch (err: unknown) {
        console.error("Failed to load score run history:", err);
        setError(extractErrorMessage(err, "Unable to load score run history."));
        setHistoryRuns([]);
      } finally {
        setHistoryLoading(false);
      }
    }
  }, [showHistory, historyRuns, assessmentId]);

  if (!assessmentId) {
    return (
      <AppShell title="Materiality Matrix" description="Visualise materiality results.">
        <div className="flex min-h-[400px] items-center justify-center">
          <Card className="max-w-md">
            <CardContent className="p-8 text-center">
              <AlertCircle className="mx-auto mb-4 h-10 w-10 text-destructive" />
              <h2 className="text-lg font-semibold">Assessment not found</h2>
              <p className="mt-2 text-sm text-muted-foreground">A valid materiality assessment is required.</p>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  if (loading && !assessment) {
    return (
      <AppShell title="Materiality Matrix" description="Visualise materiality results.">
        <div className="space-y-6">
          <div className="h-20 animate-pulse rounded-xl bg-muted" />
          <div className="h-40 animate-pulse rounded-xl bg-muted" />
          <div className="mx-auto aspect-[4/3] w-full max-w-3xl animate-pulse rounded-2xl bg-muted" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Materiality Matrix"
      description={
        isDoubleMode
          ? "Review impact and financial materiality results."
          : "Review materiality results and classification thresholds."
      }
    >
      <MatrixAnimationStyles />

      <div id="materiality-matrix-page" className="space-y-6 pb-10">
        {/* HEADER */}
        <div className="mm-fade-up flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
                ESG Materiality
              </Badge>
              <Badge
                variant="outline"
                className={
                  isDoubleMode
                    ? "border-purple-200 bg-purple-50 text-purple-700"
                    : "border-sky-200 bg-sky-50 text-sky-700"
                }
              >
                {isDoubleMode ? "Double Materiality" : "Single Materiality"}
              </Badge>
              {scoreRun && (
                <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-600">
                  Method v{scoreRun.method_version ?? ESG_SCORE_METHOD}
                </Badge>
              )}
            </div>

            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              {assessment?.name ?? "Materiality Assessment"}
            </h1>

            <p className="mt-1.5 max-w-3xl text-sm text-muted-foreground">
              {isDoubleMode
                ? "Compare the significance of organisational impacts with the significance of financial effects."
                : "Evaluate which ESG topics are material based on the assessment's primary and secondary dimensions."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void loadDashboard(true)} disabled={refreshing}>
              <RefreshCw className={`h-4 w-4 sm:mr-2 ${refreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>

            <Button variant="outline" size="sm" onClick={() => void handleToggleHistory()}>
              <History className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">History</span>
              <ChevronDown className={`ml-1 h-3.5 w-3.5 transition-transform ${showHistory ? "rotate-180" : ""}`} />
            </Button>

            <span className="mx-1 hidden h-6 w-px bg-border sm:inline-block" aria-hidden="true" />

            <Button variant="outline" size="sm" onClick={() => void handleExportPng()} disabled={exportingPng}>
              <ImageIcon className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">{exportingPng ? "Exporting..." : "PNG"}</span>
            </Button>
            <Button variant="outline" size="sm" onClick={() => void handleExportCsv()} disabled={exportingCsv}>
              <FileSpreadsheet className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">{exportingCsv ? "Exporting..." : "CSV"}</span>
            </Button>
            <Button variant="outline" size="sm" onClick={() => void handleExportPdf()} disabled={exportingPdf}>
              <FileText className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">{exportingPdf ? "Exporting..." : "PDF"}</span>
            </Button>

            <span className="mx-1 hidden h-6 w-px bg-border sm:inline-block" aria-hidden="true" />

            <Button size="sm" onClick={handleRunScoring} disabled={runningScoring} className="bg-emerald-600 hover:bg-emerald-700">
              <Target className="h-4 w-4 sm:mr-2" />
              {runningScoring ? "Running..." : "Run Scoring"}
            </Button>
          </div>
        </div>

        {/* SCORE RUN HISTORY */}
        {showHistory && (
          <Card className="mm-fade-up">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-base">Score Run History</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => setShowHistory(false)}>
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="pt-0">
              {historyLoading ? (
                <div className="space-y-2">
                  <div className="h-10 animate-pulse rounded-lg bg-muted" />
                  <div className="h-10 animate-pulse rounded-lg bg-muted" />
                </div>
              ) : historyRuns && historyRuns.length > 0 ? (
                <div className="overflow-hidden rounded-lg border">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-2.5">Run date</th>
                        <th className="px-4 py-2.5">Responses</th>
                        <th className="px-4 py-2.5">Method</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {historyRuns.map((run) => (
                        <tr key={run.id} className="hover:bg-slate-50/60">
                          <td className="px-4 py-2.5 text-foreground">
                            {new Date(run.run_at).toLocaleString(undefined, {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">
                            {run.response_count ?? "-"} / {run.invited_count ?? "-"}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">v{run.method_version ?? ESG_SCORE_METHOD}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">No score runs yet for this assessment.</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* ERROR */}
        {error && (
          <div className="mm-fade-up flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">Unable to complete the request</p>
              <p className="mt-1 text-sm">{error}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setError(null)} className="text-red-700 hover:bg-red-100">
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* THRESHOLD ADJUSTMENT */}
        <Card className="mm-fade-up" style={{ animationDelay: "60ms" }}>
          <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0 pb-6 px-4">
            <div className="space-y-1.5">
              <CardTitle className="text-base">Threshold Adjustment</CardTitle>
              <p className="text-sm text-muted-foreground">
                Adjust thresholds to reclassify topics in real-time. Changes reflect instantly on the matrix.
              </p>
            </div>
            {thresholdChanged && (
              <Button variant="outline" size="sm" onClick={handleResetThresholds} className="shrink-0">
                <RotateCcw className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Reset</span>
              </Button>
            )}
          </CardHeader>

          <CardContent className="pt-0 py-5">
            <div className="mx-auto grid max-w-2xl gap-8 sm:grid-cols-2  ">
              <ThresholdControl
                label={`${primaryWord} Materiality Threshold (Y-Axis)`}
                value={primaryThreshold}
                onChange={setPrimaryThreshold}
              />
              <ThresholdControl
                label={`${secondaryWord} Materiality Threshold (X-Axis)`}
                value={secondaryThreshold}
                onChange={setSecondaryThreshold}
              />
            </div>

            <div className="mt-6 flex justify-center">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                <Layers className="h-3.5 w-3.5" />
                {results.length} Topics
              </span>
            </div>
          </CardContent>
        </Card>

        {/* MATRIX GRAPH */}
        <Card className="mm-fade-up" style={{ animationDelay: "120ms" }}>
          <div ref={matrixCardRef} className="bg-card">
            <CardHeader className="space-y-1.5 pb-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between px-4">
                <div>
                  <CardTitle className="text-base">Materiality Matrix</CardTitle>
                  <p className="mt-1.5 text-sm text-muted-foreground">Hover a point to see topic details.</p>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 lg:pt-0.5">
                  {LEGEND_ITEMS.map((item) => (
                    <div key={item.label} className="flex items-center gap-1.5 text-xs text-slate-600">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                      {item.label}
                    </div>
                  ))}
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-1">
              <div className="mx-auto w-full rounded-2xl border bg-white p-4 sm:p-7">
                <div ref={chartWrapperRef} className="aspect-[16/10] w-full sm:aspect-[16/9]">
                  <ReactECharts
                    ref={chartRef}
                    option={chartOption}
                    notMerge={false}
                    lazyUpdate
                    opts={{ renderer: "svg" }}
                    style={{ height: "100%", width: "100%" }}
                  />
                </div>
              </div>
            </CardContent>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

/* ============================================================
   THRESHOLD CONTROL
============================================================ */

function ThresholdControl({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Label className="text-sm font-medium">{label}</Label>
        <span className="w-16 shrink-0 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-center text-sm font-semibold tabular-nums text-emerald-700">
          {value.toFixed(2)}
        </span>
      </div>

      <Slider
        min={1}
        max={5}
        step={0.25}
        value={[value]}
        onValueChange={(values) => {
          const next = values[0];
          if (typeof next === "number") onChange(next);
        }}
      />

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>1.00</span>
        <span>5.00</span>
      </div>
    </div>
  );
}