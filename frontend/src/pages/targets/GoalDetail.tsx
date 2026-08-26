import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChevronRight, CircleAlert, ClipboardCheck, LineChart as LineChartIcon, Plus, Target as TargetIcon } from "lucide-react";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { TargetsApi } from "@/api/targets/TargetsApi";
import DatapointApi from "@/api/datapoints/DatapointApi";
import OrganizationApi from "@/api/organizations/OrganizationApi";
import ReportingPeriodApi from "@/api/reporting_periods/ReportingPeriodApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import type { Datapoint, Unit } from "@/types/datapoint";
import type { OrgNode } from "@/types/organization";
import type { ReportingPeriod } from "@/types/reporting-period";
import type { Direction, Goal, KPI, Target, TargetProgress } from "@/types/targets/targets";

type KpiForm = { code: string; name: string; description: string; datapoint: string; direction: Direction; aggregation: "SUM" | "AVG" | "LATEST" | "COUNT" };
type TargetForm = { org_node: string; baseline_period: string; baseline_value: string; baseline_unit: string; baseline_source: "SYSTEM_DATA" | "REFERENCE"; target_period: string; target_value: string; target_unit: string; target_type: "ABSOLUTE" | "INTENSITY" | "PERCENTAGE"; basis: string; rationale: string; methodology: string; status: string };

const emptyKpi: KpiForm = { code: "", name: "", description: "", datapoint: "", direction: "REDUCE", aggregation: "SUM" };
const emptyTarget: TargetForm = { org_node: "none", baseline_period: "", baseline_value: "", baseline_unit: "", baseline_source: "REFERENCE", target_period: "", target_value: "", target_unit: "", target_type: "ABSOLUTE", basis: "OTHER", rationale: "", methodology: "", status: "DRAFT" };
const targetBasis = ["PRIOR_YEAR_ACTUAL", "PRIOR_REPORT", "PEER_BENCHMARK", "REGULATORY_REQUIREMENT", "INDUSTRY_STANDARD", "SCIENCE_BASED", "CUSTOMER_REQUIREMENT", "MANAGEMENT_COMMITMENT", "OTHER"];

function formatMetric(value: string | number | null | undefined) {
  if (value == null || value === "") return "";
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numeric)
    : String(value);
}

export default function GoalDetail() {
  const { id = "" } = useParams();
  const [goal, setGoal] = useState<Goal>();
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [selected, setSelected] = useState("");
  const [targets, setTargets] = useState<Target[]>([]);
  const [progress, setProgress] = useState<TargetProgress>();
  const [periods, setPeriods] = useState<ReportingPeriod[]>([]);
  const [datapoints, setDatapoints] = useState<Datapoint[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [orgNodes, setOrgNodes] = useState<OrgNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [kpiOpen, setKpiOpen] = useState(false);
  const [targetOpen, setTargetOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<Target | null>(null);
  const [kpiForm, setKpiForm] = useState<KpiForm>(emptyKpi);
  const [targetForm, setTargetForm] = useState<TargetForm>(emptyTarget);
  const [saving, setSaving] = useState(false);

  const loadGoal = useCallback(async () => {
    try {
      setLoading(true); setError("");
      const [loadedGoal, loadedKpis] = await Promise.all([TargetsApi.goal(id), TargetsApi.kpis(id)]);
      setGoal(loadedGoal); setKpis(loadedKpis); setSelected((current) => current || loadedKpis[0]?.id || "");
    } catch { setError("This goal could not be loaded. It may be outside your target scope."); }
    finally { setLoading(false); }
  }, [id]);

  // Remote loading intentionally writes state after the request settles.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void loadGoal(); }, [loadGoal]);
  useEffect(() => {
    void Promise.all([ReportingPeriodApi.getAll(), DatapointApi.getAll(), DatapointApi.getUnits(), OrganizationApi.getAll()]).then(([periodResult, datapointResult, unitResult, nodeResult]) => {
      setPeriods(periodResult.data.filter((period) => period.period_type === "ANNUAL" && period.is_active).sort((a, b) => a.start_date.localeCompare(b.start_date)));
      setDatapoints(datapointResult.data.filter((datapoint) => datapoint.is_active && ["DECIMAL", "INTEGER"].includes(datapoint.data_type)));
      setUnits(unitResult.data.filter((unit) => unit.is_active)); setOrgNodes(nodeResult.data.filter((node) => node.is_active));
    }).catch(() => undefined);
  }, []);
  const loadTarget = useCallback(async () => {
    if (!selected) return;
    try {
      const rows = await TargetsApi.targets(selected); setTargets(rows);
      setProgress(rows[0] ? await TargetsApi.progress(rows[0].id) : undefined);
    } catch { setTargets([]); setProgress(undefined); }
  }, [selected]);
  // Remote loading intentionally writes state after the request settles.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void loadTarget(); }, [loadTarget]);

  const activeTarget = targets[0];
  const selectedKpi = kpis.find((kpi) => kpi.id === selected);
  const selectedDatapoint = datapoints.find((datapoint) => datapoint.id === kpiForm.datapoint);
  const applicableUnits = useMemo(() => units.filter((unit) => unit.family === (selectedKpi?.unit_family ?? selectedDatapoint?.unit_family)), [units, selectedKpi?.unit_family, selectedDatapoint?.unit_family]);
  const graph = useMemo(() => progress?.trajectory.map((item, index) => ({ name: item.name.replace("DEMO M10 ", ""), trajectory: item.value == null ? undefined : Number(item.value), actual: progress.progress[index]?.actual_value == null ? undefined : Number(progress.progress[index].actual_value), target: index === (progress.trajectory.length - 1) ? Number(item.value) : undefined })) ?? [], [progress]);
  const actual = progress?.progress.filter((row) => row.actual_value != null).at(-1);
  const visibleKpis = kpis.slice(0, 5);

  function selectDatapoint(datapointId: string) {
    const datapoint = datapoints.find((item) => item.id === datapointId);
    setKpiForm((current) => ({ ...current, datapoint: datapointId, code: datapoint?.code.toLowerCase().replaceAll(/[^a-z0-9]+/g, ".") ?? current.code, name: datapoint?.label ?? current.name }));
  }
  function openTarget(target?: Target) {
    setEditingTarget(target ?? null);
    setTargetForm(target ? { org_node: target.org_node ?? "none", baseline_period: target.baseline_period, baseline_value: target.baseline_value, baseline_unit: target.baseline_unit ?? "", baseline_source: target.baseline_source, target_period: target.target_period, target_value: target.target_value, target_unit: target.target_unit ?? "", target_type: target.target_type, basis: target.basis, rationale: target.rationale, methodology: target.methodology, status: target.status } : { ...emptyTarget, baseline_unit: selectedKpi?.default_unit ?? "", target_unit: selectedKpi?.default_unit ?? "" });
    setTargetOpen(true);
  }
  async function saveKpi() {
    if (!kpiForm.code || !kpiForm.name || !kpiForm.datapoint) return;
    try { setSaving(true); await TargetsApi.createKpi(id, { ...kpiForm, metric_source_type: "DATAPOINT" }); setKpiOpen(false); setKpiForm(emptyKpi); await loadGoal(); toast.success("KPI added"); }
    catch { toast.error("Unable to add KPI. Review the canonical datapoint and try again."); }
    finally { setSaving(false); }
  }
  async function saveTarget() {
    if (!selected || !targetForm.baseline_period || !targetForm.target_period || !targetForm.baseline_value || !targetForm.target_value) return;
    try {
      setSaving(true);
      const payload = { ...targetForm, org_node: targetForm.org_node === "none" ? null : targetForm.org_node, baseline_unit: targetForm.baseline_unit || null, target_unit: targetForm.target_unit || null };
      if (editingTarget) await TargetsApi.updateTarget(editingTarget.id, payload); else await TargetsApi.createTarget(selected, payload);
      setTargetOpen(false); await loadTarget(); toast.success(editingTarget ? "Target updated" : "Target configured");
    } catch { toast.error("Unable to save target configuration. Ensure the baseline precedes the target period."); }
    finally { setSaving(false); }
  }

  return <AppShell title={goal?.name ?? "Goal"} description="KPI target planning and approved-data progress.">
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 pb-10 sm:px-6 lg:px-8">
      {loading ? <DetailSkeleton /> : error ? <Card><CardContent className="py-14 text-center text-destructive"><CircleAlert className="mx-auto mb-3 size-7" />{error}</CardContent></Card> : <>
        <nav className="flex items-center gap-1 text-sm text-muted-foreground"><Link to="/goals" className="hover:text-foreground">Goals</Link><ChevronRight className="size-4" /><span className="truncate text-foreground">{goal?.name}</span></nav>
        <section className="flex flex-col justify-between gap-5 rounded-2xl border bg-card p-5 shadow-sm sm:flex-row sm:items-end sm:p-7"><div className="space-y-3"><div className="flex flex-wrap items-center gap-2"><Badge variant={goal?.status === "ACTIVE" ? "active" : "draft"}>{goal?.status.toLowerCase()}</Badge>{goal?.material_topic_name ? <Badge variant="secondary">{goal.material_topic_name}</Badge> : <Badge variant="default">Independent goal</Badge>}</div><div><h1 className="text-3xl font-semibold tracking-tight">{goal?.name}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{goal?.description || "Define outcomes and connect their KPIs to approved ESG data."}</p></div></div><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={!selected}><ClipboardCheck className="mr-2 size-4" />Initiatives</Button><Button onClick={() => { setKpiForm(emptyKpi); setKpiOpen(true); }}><Plus className="mr-2 size-4" />Add KPI</Button></div></section>
        {kpis.length ? <>
          <section className="space-y-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Key performance indicators</p><Tabs value={selected} onValueChange={setSelected}><TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto p-1">{visibleKpis.map((kpi) => <TabsTrigger key={kpi.id} value={kpi.id} className="shrink-0">{kpi.name}</TabsTrigger>)}{kpis.length > visibleKpis.length && <Select value={selected} onValueChange={setSelected}><SelectTrigger className="h-9 w-36 shrink-0"><SelectValue placeholder={`+${kpis.length - visibleKpis.length} more`} /></SelectTrigger><SelectContent>{kpis.slice(visibleKpis.length).map((kpi) => <SelectItem key={kpi.id} value={kpi.id}>{kpi.name}</SelectItem>)}</SelectContent></Select>}</TabsList></Tabs></section>
          <section className="grid gap-4 md:grid-cols-3"><MetricCard title="Actual" value={actual?.actual_value ?? "No approved data"} unit={activeTarget?.baseline_unit_code ?? selectedKpi?.default_unit_code} subtitle={actual ? "Latest approved M5 value" : "Only approved M5 submissions appear here"} icon={<LineChartIcon className="size-5" />} /><MetricCard title="Target trajectory" value={activeTarget ? `${formatMetric(activeTarget.baseline_value)} → ${formatMetric(activeTarget.target_value)}` : "Not configured"} unit={activeTarget?.baseline_unit_code} subtitle="Straight-line plan between baseline and endpoint" icon={<TargetIcon className="size-5" />} /><MetricCard title="Target" value={activeTarget?.target_value ?? "Not configured"} unit={activeTarget?.target_unit_code} subtitle={activeTarget?.target_period_name ?? "Configure target to begin"} icon={<TargetIcon className="size-5" />} /></section>
          <section className="grid gap-5 lg:grid-cols-[minmax(320px,0.78fr)_minmax(0,1.6fr)]"><BaselinePanel target={activeTarget} onConfigure={() => openTarget(activeTarget)} /><ProgressPanel kpi={selectedKpi} target={activeTarget} graph={graph} progress={progress} /></section>
        </> : <Card className="border-dashed"><CardContent className="flex min-h-64 flex-col items-center justify-center p-8 text-center"><span className="mb-4 grid size-12 place-items-center rounded-full bg-primary/10"><TargetIcon className="size-6 text-primary" /></span><h2 className="text-lg font-semibold">Add a KPI to begin planning</h2><p className="mt-2 max-w-md text-sm text-muted-foreground">Choose an active canonical M4 datapoint. Its approved M5 values will become the KPI’s actuals.</p><Button className="mt-5" onClick={() => setKpiOpen(true)}><Plus className="mr-2 size-4" />Add KPI</Button></CardContent></Card>}
      </>}
    </main>
    <Dialog open={kpiOpen} onOpenChange={setKpiOpen}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl"><DialogHeader><DialogTitle>Add KPI</DialogTitle></DialogHeader><div className="space-y-4"><Field label="Canonical M4 datapoint"><Select value={kpiForm.datapoint} onValueChange={selectDatapoint}><SelectTrigger><SelectValue placeholder="Select a numeric datapoint" /></SelectTrigger><SelectContent>{datapoints.map((datapoint) => <SelectItem key={datapoint.id} value={datapoint.id}>{datapoint.label} · {datapoint.code}</SelectItem>)}</SelectContent></Select></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="KPI name"><Input value={kpiForm.name} onChange={(event) => setKpiForm({ ...kpiForm, name: event.target.value })} /></Field><Field label="Stable KPI code"><Input value={kpiForm.code} onChange={(event) => setKpiForm({ ...kpiForm, code: event.target.value })} /></Field></div><Field label="Direction"><Select value={kpiForm.direction} onValueChange={(value) => setKpiForm({ ...kpiForm, direction: value as Direction })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="REDUCE">Reduce</SelectItem><SelectItem value="INCREASE">Increase</SelectItem><SelectItem value="MAINTAIN">Maintain</SelectItem></SelectContent></Select></Field><Field label="Aggregation"><Select value={kpiForm.aggregation} onValueChange={(value) => setKpiForm({ ...kpiForm, aggregation: value as KpiForm["aggregation"] })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="SUM">Sum approved values</SelectItem><SelectItem value="AVG">Average approved values</SelectItem><SelectItem value="LATEST">Latest approved value</SelectItem><SelectItem value="COUNT">Count approved answers</SelectItem></SelectContent></Select></Field><Field label="Description"><Textarea className="min-h-20" value={kpiForm.description} onChange={(event) => setKpiForm({ ...kpiForm, description: event.target.value })} /></Field></div><DialogFooter><Button variant="outline" onClick={() => setKpiOpen(false)}>Cancel</Button><Button disabled={saving || !kpiForm.datapoint || !kpiForm.name || !kpiForm.code} onClick={() => void saveKpi()}>{saving ? "Saving…" : "Add KPI"}</Button></DialogFooter></DialogContent></Dialog>
    <Dialog open={targetOpen} onOpenChange={setTargetOpen}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"><DialogHeader><DialogTitle>{editingTarget ? "Edit target" : "Configure target"}</DialogTitle></DialogHeader><TargetFields form={targetForm} periods={periods} units={applicableUnits} orgNodes={orgNodes} onChange={setTargetForm} /><DialogFooter><Button variant="outline" onClick={() => setTargetOpen(false)}>Cancel</Button><Button disabled={saving || !targetForm.baseline_period || !targetForm.target_period || !targetForm.baseline_value || !targetForm.target_value} onClick={() => void saveTarget()}>{saving ? "Saving…" : editingTarget ? "Save target" : "Configure target"}</Button></DialogFooter></DialogContent></Dialog>
  </AppShell>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div>; }
function MetricCard({ title, value, unit, subtitle, icon }: { title: string; value: string; unit?: string; subtitle: string; icon: React.ReactNode }) { const isState = value === "No approved data" || value === "Not configured"; return <Card><CardHeader className="pb-2"><div className="flex items-center gap-2 text-muted-foreground">{icon}<CardTitle className="text-base font-medium">{title}</CardTitle></div></CardHeader><CardContent><p className="text-2xl font-semibold tracking-tight">{isState ? value : formatMetric(value)}{!isState && unit ? <span className="ml-2 text-sm font-medium text-muted-foreground">{unit}</span> : null}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{subtitle}</p></CardContent></Card>; }
function BaselinePanel({ target, onConfigure }: { target?: Target; onConfigure: () => void }) { return <Card><CardHeader><CardTitle>Baseline & target</CardTitle><CardDescription>Where this KPI starts, why the target was set, and where it should reach.</CardDescription></CardHeader><CardContent className="space-y-5">{target ? <dl className="space-y-4 text-sm"><div><dt className="text-muted-foreground">Baseline</dt><dd className="mt-1 font-medium">{formatMetric(target.baseline_value)} {target.baseline_unit_code} · {target.baseline_period_name}</dd><p className="mt-1 text-xs text-muted-foreground">{target.baseline_source === "SYSTEM_DATA" ? "Frozen from approved system data" : "Reference/manual baseline"}</p></div><div><dt className="text-muted-foreground">Target endpoint</dt><dd className="mt-1 font-medium">{formatMetric(target.target_value)} {target.target_unit_code} · {target.target_period_name}</dd></div><div><dt className="text-muted-foreground">Basis</dt><dd className="mt-1">{target.basis.replaceAll("_", " ").toLowerCase()}</dd></div>{target.org_node_name && <div><dt className="text-muted-foreground">Scope</dt><dd className="mt-1">{target.org_node_name}</dd></div>}</dl> : <p className="text-sm leading-6 text-muted-foreground">Set a frozen baseline and an endpoint to make this KPI’s target trajectory visible.</p>}<Button className="w-full" variant={target ? "outline" : "default"} onClick={onConfigure}>{target ? "Edit target configuration" : "Configure target"}</Button></CardContent></Card>; }
function ProgressPanel({ kpi, target, graph, progress }: { kpi?: KPI; target?: Target; graph: Array<{ name: string; trajectory?: number; actual?: number; target?: number }>; progress?: TargetProgress }) { return <Card><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle>{kpi?.name ?? "KPI"} progress</CardTitle><CardDescription>Approved actuals and a deterministic target trajectory by reporting period.</CardDescription></div>{target && <Badge variant="info">{target.target_type.toLowerCase()}</Badge>}</div></CardHeader><CardContent className="h-[360px]">{graph.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={graph} margin={{ top: 16, right: 20, left: 0, bottom: 8 }}><XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip formatter={(value: number | string | undefined) => value == null ? "No data" : formatMetric(value)} /><Line type="linear" dataKey="trajectory" name="Target trajectory" stroke="#4A3FD6" strokeWidth={2.5} dot={{ r: 3 }} connectNulls /><Line type="monotone" dataKey="actual" name="Approved actual" stroke="#168A5B" strokeWidth={3} dot={{ r: 4 }} connectNulls /><Line type="linear" dataKey="target" name="Target endpoint" stroke="#C87913" strokeWidth={3} dot={{ r: 5 }} /></LineChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-center"><div><LineChartIcon className="mx-auto mb-3 size-7 text-muted-foreground" /><p className="font-medium">No target trajectory yet</p><p className="mt-1 text-sm text-muted-foreground">Configure a baseline and target to show the planned path. Approved actuals will appear as they are collected.</p></div></div>}</CardContent>{progress && !progress.progress.some((row) => row.actual_value != null) && <div className="border-t px-6 py-3 text-xs text-muted-foreground">No approved M5 data is available in this target window yet. Values are never shown as zero.</div>}</Card>; }
function TargetFields({ form, periods, units, orgNodes, onChange }: { form: TargetForm; periods: ReportingPeriod[]; units: Unit[]; orgNodes: OrgNode[]; onChange: (value: TargetForm) => void }) { const update = (key: keyof TargetForm, value: string) => onChange({ ...form, [key]: value }); return <div className="space-y-4"><div className="grid gap-4 sm:grid-cols-2"><Field label="Target scope"><Select value={form.org_node} onValueChange={(value) => update("org_node", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Company-wide</SelectItem>{orgNodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Target type"><Select value={form.target_type} onValueChange={(value) => update("target_type", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ABSOLUTE">Absolute</SelectItem><SelectItem value="INTENSITY">Intensity</SelectItem><SelectItem value="PERCENTAGE">Percentage</SelectItem></SelectContent></Select></Field></div><div className="grid gap-4 rounded-xl border bg-muted/20 p-4 sm:grid-cols-2"><Field label="Baseline reporting period"><Select value={form.baseline_period} onValueChange={(value) => update("baseline_period", value)}><SelectTrigger><SelectValue placeholder="Choose baseline period" /></SelectTrigger><SelectContent>{periods.map((period) => <SelectItem key={period.id} value={period.id}>{period.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Baseline value"><Input inputMode="decimal" value={form.baseline_value} onChange={(event) => update("baseline_value", event.target.value)} placeholder="e.g. 120000" /></Field><Field label="Target reporting period"><Select value={form.target_period} onValueChange={(value) => update("target_period", value)}><SelectTrigger><SelectValue placeholder="Choose target period" /></SelectTrigger><SelectContent>{periods.map((period) => <SelectItem key={period.id} value={period.id}>{period.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Target value"><Input inputMode="decimal" value={form.target_value} onChange={(event) => update("target_value", event.target.value)} placeholder="e.g. 90000" /></Field></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Unit"><Select value={form.baseline_unit} onValueChange={(value) => onChange({ ...form, baseline_unit: value, target_unit: value })}><SelectTrigger><SelectValue placeholder="Choose unit" /></SelectTrigger><SelectContent>{units.map((unit) => <SelectItem key={unit.id} value={unit.id}>{unit.name} ({unit.code})</SelectItem>)}</SelectContent></Select></Field><Field label="Target basis"><Select value={form.basis} onValueChange={(value) => update("basis", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{targetBasis.map((basis) => <SelectItem key={basis} value={basis}>{basis.replaceAll("_", " ").toLowerCase()}</SelectItem>)}</SelectContent></Select></Field></div><Field label="Rationale"><Textarea className="min-h-20" value={form.rationale} onChange={(event) => update("rationale", event.target.value)} placeholder="Why is this endpoint appropriate?" /></Field><Field label="Methodology"><Textarea className="min-h-20" value={form.methodology} onChange={(event) => update("methodology", event.target.value)} placeholder="Optional target methodology or assumptions" /></Field></div>; }
function DetailSkeleton() { return <div className="space-y-6"><Skeleton className="h-5 w-52" /><Skeleton className="h-44 w-full" /><div className="grid gap-4 md:grid-cols-3">{[1, 2, 3].map((key) => <Skeleton key={key} className="h-36" />)}</div><Skeleton className="h-96 w-full" /></div>; }
