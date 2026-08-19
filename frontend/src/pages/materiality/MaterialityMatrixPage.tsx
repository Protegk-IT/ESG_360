import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { toPng } from "html-to-image";
import {
  FileSpreadsheet,
  FileText,
  History,
  ImageIcon,
  RefreshCw,
  Target,
  Users,
} from "lucide-react";

import api from "@/services/api";
import AssessmentApi from "@/api/materiality/AssessmentApi";
import ScoringApi from "@/api/materiality/ScoringApi";
import AppShell from "@/components/layout/AppShell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { MaterialityAssessment } from "@/types/materiality/assessment";
import type {
  GroupBreakdownEntry,
  MaterialityResult,
  ScoreRunDetail,
  ScoreRunListItem,
  ScoreRunResultsResponse,
  ScoreRunTopicResult,
} from "@/types/materiality/scoring";

const colors: Record<string, string> = {
  MATERIAL: "#dc2626",
  DOUBLE_MATERIAL: "#dc2626",
  IMPACT_MATERIAL: "#2563eb",
  FINANCIAL_MATERIAL: "#d97706",
  MONITOR: "#d97706",
  NOT_MATERIAL: "#16a34a",
  INSUFFICIENT_DATA: "#64748b",
};
const classificationOrder = [
  "DOUBLE_MATERIAL",
  "IMPACT_MATERIAL",
  "FINANCIAL_MATERIAL",
  "NOT_MATERIAL",
  "INSUFFICIENT_DATA",
];
const score = (value: unknown) =>
  Number.isFinite(Number(value)) ? Number(value) : 0;
const labelFor = (value: string) =>
  value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
const compactTopicLabel = (value: string) =>
  value.length > 21 ? `${value.slice(0, 19).trimEnd()}…` : value;
const isScoreRunDetail = (
  value: ScoreRunResultsResponse,
): value is ScoreRunDetail => "run_at" in value;

type MatrixPoint = MaterialityResult & {
  chart_primary_score: number;
  chart_secondary_score: number;
  overlap_count: number;
};

function ClassificationBadge({ classification }: { classification: string }) {
  return (
    <Badge
      className="border-0 text-white hover:bg-inherit"
      style={{ backgroundColor: colors[classification] ?? "#64748b" }}
    >
      {labelFor(classification)}
    </Badge>
  );
}

function MatrixMarker({
  cx,
  cy,
  fill,
  payload,
}: {
  cx?: number;
  cy?: number;
  fill?: string;
  payload?: MatrixPoint;
}) {
  if (cx == null || cy == null || !payload) return null;
  const labelOnLeft = score(payload.chart_secondary_score) >= 4;
  return (
    <g className="cursor-pointer">
      <title>{`${payload.subtopic_name}: impact ${score(payload.primary_score).toFixed(2)}, financial ${score(payload.secondary_score).toFixed(2)}`}</title>
      <circle
        cx={cx}
        cy={cy}
        r={8}
        fill={fill}
        stroke="white"
        strokeWidth={2.5}
      />
      <text
        x={cx + (labelOnLeft ? -11 : 11)}
        y={cy - 10}
        textAnchor={labelOnLeft ? "end" : "start"}
        fill="#334155"
        fontSize={11}
        fontWeight={600}
        stroke="white"
        strokeWidth={3}
        paintOrder="stroke"
      >
        {compactTopicLabel(payload.subtopic_name ?? "Assessment topic")}
      </text>
    </g>
  );
}

function StakeholderContribution({
  breakdown,
}: {
  breakdown?: Record<string, GroupBreakdownEntry[]>;
}) {
  const dimensions = Object.entries(breakdown ?? {}).filter(
    ([, entries]) => entries.length > 0,
  );
  if (!dimensions.length)
    return (
      <p className="text-sm text-muted-foreground">
        No stakeholder-group response snapshot is available for this topic.
      </p>
    );
  return (
    <div className="space-y-5">
      {dimensions.map(([dimension, entries]) => (
        <div key={dimension} className="overflow-x-auto">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {dimension === "IMPACT"
              ? "Impact"
              : dimension === "FINANCIAL"
                ? "Financial"
                : labelFor(dimension)}{" "}
            stakeholder input
          </p>
          <Table className="min-w-155">
            <TableHeader>
              <TableRow className="border-slate-200 bg-slate-50 hover:bg-slate-50">
                <TableHead className="px-4 py-3">Stakeholder group</TableHead>
                <TableHead className="px-4 py-3 text-center">Weight</TableHead>
                <TableHead className="px-4 py-3 text-center">
                  Responses
                </TableHead>
                <TableHead className="px-4 py-3 text-center">Average</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow
                  key={entry.group_id}
                  className="border-slate-100 hover:bg-slate-50/70"
                >
                  <TableCell className="px-4 py-4 font-medium text-slate-900">
                    {entry.group_name}
                  </TableCell>
                  <TableCell className="px-4 py-4 text-center text-slate-600">
                    {entry.weight}%
                  </TableCell>
                  <TableCell className="px-4 py-4 text-center text-slate-600">
                    {entry.response_count}
                  </TableCell>
                  <TableCell className="px-4 py-4 text-center font-medium text-slate-900">
                    {entry.average ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ))}
    </div>
  );
}

export default function MaterialityMatrixPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const chartRef = useRef<HTMLDivElement>(null);
  const [assessment, setAssessment] = useState<MaterialityAssessment | null>(
    null,
  );
  const [run, setRun] = useState<ScoreRunDetail | null>(null);
  const [results, setResults] = useState<MaterialityResult[]>([]);
  const [selected, setSelected] = useState<MaterialityResult | null>(null);
  const [runs, setRuns] = useState<ScoreRunListItem[] | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!assessmentId) return;
    try {
      setLoading(true);
      setError(null);
      const [assessmentResponse, resultResponse] = await Promise.all([
        AssessmentApi.getById(assessmentId),
        ScoringApi.getResults(assessmentId),
      ]);
      setAssessment(assessmentResponse.data);
      if (isScoreRunDetail(resultResponse.data)) {
        setRun(resultResponse.data);
        setResults(
          resultResponse.data.topic_results.map(
            (topic: ScoreRunTopicResult) => ({
              ...topic,
              primary_score: score(topic.primary_score),
              secondary_score: score(topic.secondary_score),
            }),
          ),
        );
      } else {
        setRun(null);
        setResults([]);
      }
    } catch {
      setError(
        "Unable to load materiality results. Refresh the page to try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);
  useEffect(() => {
    const requestId = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(requestId);
  }, [load]);

  const readOnly = Boolean(
    assessment?.is_locked ||
    ["COMPLETED", "APPROVED"].includes(assessment?.status ?? ""),
  );
  const primaryThreshold = score(
    run?.thresholds_snapshot?.primary_threshold ??
      assessment?.primary_threshold ??
      3,
  );
  const secondaryThreshold = score(
    run?.thresholds_snapshot?.secondary_threshold ??
      assessment?.secondary_threshold ??
      3,
  );
  const counts = useMemo(
    () =>
      results.reduce<Record<string, number>>(
        (all, result) => ({
          ...all,
          [result.classification]: (all[result.classification] ?? 0) + 1,
        }),
        {},
      ),
    [results],
  );
  const classifications = useMemo(
    () =>
      classificationOrder.filter((classification) => counts[classification]),
    [counts],
  );
  const chartPoints = useMemo<MatrixPoint[]>(() => {
    const clusters = new Map<string, MaterialityResult[]>();
    results.forEach((result) => {
      const key = `${score(result.primary_score).toFixed(3)}:${score(result.secondary_score).toFixed(3)}`;
      clusters.set(key, [...(clusters.get(key) ?? []), result]);
    });
    return Array.from(clusters.values()).flatMap((cluster) =>
      cluster.map((result, index) => ({
        ...result,
        overlap_count: cluster.length,
        chart_primary_score: Math.max(
          1,
          Math.min(
            5,
            score(result.primary_score) +
              (Math.floor(index / 3) - 1) * (cluster.length > 1 ? 0.06 : 0),
          ),
        ),
        chart_secondary_score: Math.max(
          1,
          Math.min(
            5,
            score(result.secondary_score) +
              ((index % 3) - 1) * (cluster.length > 1 ? 0.06 : 0),
          ),
        ),
      })),
    );
  }, [results]);

  const exportFile = async (type: "csv" | "pdf") => {
    if (!assessmentId) return;
    const response = await api.get(
      `/materiality/assessments/${assessmentId}/export/${type}/`,
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data as Blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `materiality-results.${type}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const toggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && !runs && assessmentId) {
      const response = await ScoringApi.getScoreRuns(assessmentId);
      setRuns(response.data);
    }
  };

  return (
    <AppShell
      title="Results & Matrix"
      description="Review the recorded materiality outcome and supporting evidence."
    >
      <div className="mx-auto max-w-7xl space-y-6 pb-10">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <Badge>
              {assessment?.mode === "DOUBLE"
                ? "Double materiality"
                : "Single materiality"}
            </Badge>
            {readOnly && (
              <Badge variant="outline" className="ml-2">
                Historical record
              </Badge>
            )}
            <h2 className="mt-3 text-2xl font-semibold text-foreground">
              {assessment?.name ?? "Materiality assessment"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {run
                ? `Latest calculation: ${new Date(run.run_at).toLocaleString()}`
                : "Complete evidence collection and internal review, then run scoring."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => void load()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void toggleHistory()}
            >
              <History className="mr-2 h-4 w-4" />
              Score-run history
            </Button>
            {run && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void exportFile("csv")}
                >
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void exportFile("pdf")}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  PDF
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    if (!chartRef.current) return;
                    const image = await toPng(chartRef.current);
                    const anchor = document.createElement("a");
                    anchor.href = image;
                    anchor.download = "materiality-matrix.png";
                    anchor.click();
                  }}
                >
                  <ImageIcon className="mr-2 h-4 w-4" />
                  PNG
                </Button>
              </>
            )}
            {!readOnly && (
              <Button
                size="sm"
                onClick={async () => {
                  if (!assessmentId) return;
                  await ScoringApi.runScoring(assessmentId);
                  await load();
                }}
              >
                <Target className="mr-2 h-4 w-4" />
                Run scoring
              </Button>
            )}
          </div>
        </div>

        {showHistory && (
          <Card className="border-slate-200 px-4 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Score-run history</CardTitle>
              <CardDescription>
                Each run is an immutable record of its inputs and calculation.
              </CardDescription>
            </CardHeader>
            <Separator />
            <CardContent className="p-0">
              {runs?.length ? (
                <div className="overflow-x-auto">
                  <Table className="min-w-155">
                    <TableHeader>
                      <TableRow className="border-slate-200 bg-slate-50 hover:bg-slate-50">
                        <TableHead className="px-6 py-3">Run date</TableHead>
                        <TableHead className="px-4 py-3 text-right">
                          Identified responses
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runs.map((item) => (
                        <TableRow
                          key={item.id}
                          className="border-slate-100 hover:bg-slate-50/70"
                        >
                          <TableCell className="px-6 py-4 font-medium text-slate-900">
                            {new Date(item.run_at).toLocaleString()}
                          </TableCell>
                          <TableCell className="px-4 py-4 text-right text-slate-600">
                            {item.response_count}/{item.invited_count}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <p className="p-6 text-sm text-muted-foreground">
                  No score runs yet.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {loading ? (
          <Card>
            <CardContent className="p-10 text-center text-sm text-muted-foreground">
              Loading results…
            </CardContent>
          </Card>
        ) : !run ? (
          <Card>
            <CardContent className="p-10 text-center">
              <Target className="mx-auto h-8 w-8 text-muted-foreground" />
              <h3 className="mt-3 font-semibold">No results yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Selected topics can be scored from Scoring &amp; Review before
                the first score run.
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-5">
                  <p className="text-sm text-muted-foreground">
                    Topics assessed
                  </p>
                  <p className="mt-1 text-3xl font-semibold">
                    {results.length}
                  </p>
                </CardContent>
              </Card>
              {classifications.map((classification) => (
                <Card
                  key={classification}
                  className="border-slate-200 shadow-sm"
                >
                  <CardContent className="p-5">
                    <p className="text-sm text-muted-foreground">
                      {labelFor(classification)}
                    </p>
                    <p
                      className="mt-1 text-3xl font-semibold"
                      style={{ color: colors[classification] }}
                    >
                      {counts[classification]}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card
              ref={chartRef}
              className="overflow-hidden border-slate-200 shadow-sm"
            >
              <CardHeader className="border-b bg-slate-50/70">
                <CardTitle>Materiality Matrix</CardTitle>
                <CardDescription>
                  Impact rises vertically; financial materiality rises
                  horizontally. Select a marker or use Topic review for its
                  supporting evidence.
                </CardDescription>
              </CardHeader>
              <CardContent className="px-6 pb-6 pt-6">
                <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
                  <span>
                    Impact threshold{" "}
                    <strong className="text-foreground">
                      {primaryThreshold.toFixed(2)}
                    </strong>
                  </span>
                  <span>
                    Financial threshold{" "}
                    <strong className="text-foreground">
                      {secondaryThreshold.toFixed(2)}
                    </strong>
                  </span>
                  {classifications.map((classification) => (
                    <span
                      className="inline-flex items-center gap-1.5"
                      key={classification}
                    >
                      <i
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: colors[classification] }}
                      />
                      {labelFor(classification)}
                    </span>
                  ))}
                </div>
                <div className="mx-auto aspect-square w-full max-w-190 rounded-xl bg-white p-2 sm:p-4">
                  <div className="relative h-full w-full">
                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                      minWidth={1}
                      minHeight={1}
                    >
                      <ScatterChart
                        margin={{ top: 28, right: 28, bottom: 28, left: 28 }}
                      >
                        <CartesianGrid stroke="#cbd5e1" strokeDasharray="3 4" />
                        <XAxis
                          type="number"
                          dataKey="chart_secondary_score"
                          domain={[1, 5]}
                          tickCount={5}
                          tickLine={false}
                          height={28}
                          axisLine={{ stroke: "#94a3b8" }}
                          name="Financial materiality"
                        />
                        <YAxis
                          type="number"
                          dataKey="chart_primary_score"
                          domain={[1, 5]}
                          tickCount={5}
                          tickLine={false}
                          width={28}
                          axisLine={{ stroke: "#94a3b8" }}
                          name="Impact materiality"
                        />
                        <ZAxis type="number" range={[196, 196]} />
                        <ReferenceArea
                          x1={1}
                          x2={secondaryThreshold}
                          y1={1}
                          y2={primaryThreshold}
                          fill="#f8fafc"
                          fillOpacity={1}
                        />
                        <ReferenceArea
                          x1={secondaryThreshold}
                          x2={5}
                          y1={1}
                          y2={primaryThreshold}
                          fill="#fff7ed"
                          fillOpacity={1}
                        />
                        <ReferenceArea
                          x1={1}
                          x2={secondaryThreshold}
                          y1={primaryThreshold}
                          y2={5}
                          fill="#eff6ff"
                          fillOpacity={1}
                        />
                        <ReferenceArea
                          x1={secondaryThreshold}
                          x2={5}
                          y1={primaryThreshold}
                          y2={5}
                          fill="#fef2f2"
                          fillOpacity={1}
                        />
                        <ReferenceLine
                          x={secondaryThreshold}
                          stroke="#0f766e"
                          strokeWidth={2}
                          strokeDasharray="6 5"
                        />
                        <ReferenceLine
                          y={primaryThreshold}
                          stroke="#0f766e"
                          strokeWidth={2}
                          strokeDasharray="6 5"
                        />
                        <Tooltip
                          cursor={false}
                          content={({ active, payload }) =>
                            active && payload?.[0] ? (
                              <div className="min-w-62.5 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-950 shadow-xl ring-1 ring-slate-950/5">
                                <p className="font-semibold text-slate-950">
                                  {String(payload[0].payload.subtopic_name)}
                                </p>
                                <div className="mt-2 flex items-center justify-between gap-6 text-slate-600">
                                  <span>Impact</span>
                                  <strong className="text-slate-950">
                                    {score(
                                      payload[0].payload.primary_score,
                                    ).toFixed(2)}
                                  </strong>
                                </div>
                                <div className="mt-1 flex items-center justify-between gap-6 text-slate-600">
                                  <span>Financial</span>
                                  <strong className="text-slate-950">
                                    {score(
                                      payload[0].payload.secondary_score,
                                    ).toFixed(2)}
                                  </strong>
                                </div>
                                <div className="mt-3">
                                  <ClassificationBadge
                                    classification={String(
                                      payload[0].payload.classification,
                                    )}
                                  />
                                </div>
                                {payload[0].payload.is_override && (
                                  <p className="mt-2 text-xs font-medium text-amber-700">
                                    Documented management override
                                  </p>
                                )}
                              </div>
                            ) : null
                          }
                        />
                        {classifications.map((classification) => (
                          <Scatter
                            id={`matrix-${classification}`}
                            key={classification}
                            name={labelFor(classification)}
                            data={chartPoints.filter(
                              (result) =>
                                result.classification === classification,
                            )}
                            fill={colors[classification]}
                            isAnimationActive={false}
                            shape={(point: {
                              cx?: number;
                              cy?: number;
                              fill?: string;
                              payload?: MatrixPoint;
                            }) => <MatrixMarker {...point} />}
                            onClick={(point: { payload?: MatrixPoint }) =>
                              point.payload && setSelected(point.payload)
                            }
                          />
                        ))}
                      </ScatterChart>
                    </ResponsiveContainer>
                    <span className="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 text-xs font-medium text-slate-600">
                      Financial materiality
                    </span>
                    <span className="pointer-events-none absolute -left-5 top-1/2 -translate-y-1/2 -rotate-90 whitespace-nowrap text-xs font-medium text-slate-600">
                      Impact materiality
                    </span>
                  </div>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Topics with identical scores are offset slightly for display
                  only; exports and recorded scores are unchanged.
                </p>
              </CardContent>
            </Card>

            <Card className="border-slate-200 px-4 shadow-sm">
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle className="text-base">Topic review</CardTitle>
                    <CardDescription>
                      Recorded scores, classifications, and a direct path to the
                      supporting stakeholder snapshot.
                    </CardDescription>
                  </div>
                  <Badge
                    variant="outline"
                    className="w-fit border-[#DDD8FF] bg-[#FBFAFF] text-[#4A3FD6]"
                  >
                    {results.length} topics
                  </Badge>
                </div>
              </CardHeader>
              <Separator />
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table className="min-w-225">
                    <TableHeader>
                      <TableRow className="border-slate-200 bg-slate-50 hover:bg-slate-50">
                        <TableHead className="px-6 py-3">Topic</TableHead>
                        <TableHead className="px-4 py-3 text-center">
                          Impact
                        </TableHead>
                        <TableHead className="px-4 py-3 text-center">
                          Financial
                        </TableHead>
                        <TableHead className="px-4 py-3">
                          Classification
                        </TableHead>
                        <TableHead className="px-6 py-3 text-right">
                          Action
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((result) => (
                        <TableRow
                          key={result.id}
                          className="border-slate-100 transition-colors hover:bg-slate-50/70"
                        >
                          <TableCell className="px-6 py-4 font-medium text-slate-900">
                            {result.subtopic_name}
                          </TableCell>
                          <TableCell className="px-4 py-4 text-center font-medium text-slate-900">
                            {score(result.primary_score).toFixed(2)}
                          </TableCell>
                          <TableCell className="px-4 py-4 text-center font-medium text-slate-900">
                            {score(result.secondary_score).toFixed(2)}
                          </TableCell>
                          <TableCell className="px-4 py-4">
                            <ClassificationBadge
                              classification={result.classification}
                            />
                          </TableCell>
                          <TableCell className="px-6 py-4 text-right">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => setSelected(result)}
                            >
                              Inspect
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {selected && (
              <Card className="border-slate-200 px-4 shadow-sm">
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <div className="rounded-full bg-indigo-50 p-2.5">
                      <Users className="h-5 w-5 text-indigo-700" />
                    </div>
                    <div>
                      <CardTitle className="text-base">
                        {selected.subtopic_name}
                      </CardTitle>
                      <CardDescription>
                        {labelFor(selected.classification)}
                        {selected.is_override
                          ? " · Documented management override"
                          : " · System classification"}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <Separator />
                <CardContent className="px-6 py-5">
                  <StakeholderContribution
                    breakdown={selected.group_breakdown}
                  />
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
