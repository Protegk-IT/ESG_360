import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChevronRight, CircleAlert, ClipboardCheck, LineChart as LineChartIcon, Pencil, Plus, Target as TargetIcon } from "lucide-react";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { TargetsApi } from "@/api/targets/TargetsApi";
import DatapointApi from "@/api/datapoints/DatapointApi";
import OrganizationApi from "@/api/organizations/OrganizationApi";
import ReportingPeriodApi from "@/api/reporting_periods/ReportingPeriodApi";
import UserApi from "@/api/users/UserApi";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Datapoint, Unit } from "@/types/datapoint";
import type { OrgNode } from "@/types/organization";
import type { ReportingPeriod } from "@/types/reporting-period";
import type { Direction, Goal, Initiative, KPI, Target, TargetProgress } from "@/types/targets/targets";
import type { UserData } from "@/types/user";
import GoalEditorDialog, { type GoalForm } from "./GoalEditorDialog";

type KpiForm = { code: string; name: string; description: string; datapoint: string; direction: Direction; aggregation: "SUM" | "AVG" | "LATEST" | "COUNT" };
type TargetForm = { org_node: string; baseline_period: string; baseline_value: string; baseline_unit: string; baseline_source: "SYSTEM_DATA" | "REFERENCE"; target_period: string; target_value: string; target_unit: string; target_type: "ABSOLUTE" | "INTENSITY" | "PERCENTAGE"; basis: string; rationale: string; methodology: string; status: string };
type InitiativeForm = { name: string; description: string; org_node: string; owner: string; status: Initiative["status"]; due_date: string; anticipated_impact: string };

const emptyKpi: KpiForm = { code: "", name: "", description: "", datapoint: "", direction: "REDUCE", aggregation: "SUM" };
const emptyTarget: TargetForm = { org_node: "none", baseline_period: "", baseline_value: "", baseline_unit: "", baseline_source: "REFERENCE", target_period: "", target_value: "", target_unit: "", target_type: "ABSOLUTE", basis: "OTHER", rationale: "", methodology: "", status: "DRAFT" };
const targetBasis = ["PRIOR_YEAR_ACTUAL", "PRIOR_REPORT", "PEER_BENCHMARK", "REGULATORY_REQUIREMENT", "INDUSTRY_STANDARD", "SCIENCE_BASED", "CUSTOMER_REQUIREMENT", "MANAGEMENT_COMMITMENT", "OTHER"];
const emptyInitiative: InitiativeForm = { name: "", description: "", org_node: "none", owner: "none", status: "PLANNED", due_date: "", anticipated_impact: "" };

function formatMetric(value: string | number | null | undefined) {
  if (value == null || value === "") return "";
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numeric)
    : String(value);
}

function editableDecimal(value: string) {
  return value.includes(".") ? value.replace(/0+$/, "").replace(/\.$/, "") : value;
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
  const [users, setUsers] = useState<UserData[]>([]);
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [kpiOpen, setKpiOpen] = useState(false);
  const [targetOpen, setTargetOpen] = useState(false);
  const [goalEditorOpen, setGoalEditorOpen] = useState(false);
  const [initiativesOpen, setInitiativesOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<Target | null>(null);
  const [editingInitiative, setEditingInitiative] = useState<Initiative | null>(null);
  const [initiativeFormOpen, setInitiativeFormOpen] = useState(false);
  const [kpiForm, setKpiForm] = useState<KpiForm>(emptyKpi);
  const [targetForm, setTargetForm] = useState<TargetForm>(emptyTarget);
  const [initiativeForm, setInitiativeForm] = useState<InitiativeForm>(emptyInitiative);
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
    void UserApi.getAll().then((result) => setUsers(result.data.filter((user) => user.is_active))).catch(() => setUsers([]));
  }, []);
  const loadTarget = useCallback(async () => {
    if (!selected) return;
    try {
      const [rows, initiativeRows] = await Promise.all([TargetsApi.targets(selected), TargetsApi.initiatives(selected)]); setTargets(rows); setInitiatives(initiativeRows);
      setProgress(rows[0] ? await TargetsApi.progress(rows[0].id) : undefined);
    } catch { setTargets([]); setInitiatives([]); setProgress(undefined); }
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
    setTargetForm(target ? { org_node: target.org_node ?? "none", baseline_period: target.baseline_period, baseline_value: editableDecimal(target.baseline_value), baseline_unit: target.baseline_unit ?? "", baseline_source: target.baseline_source, target_period: target.target_period, target_value: editableDecimal(target.target_value), target_unit: target.target_unit ?? "", target_type: target.target_type, basis: target.basis, rationale: target.rationale, methodology: target.methodology, status: target.status } : { ...emptyTarget, baseline_unit: selectedKpi?.default_unit ?? "", target_unit: selectedKpi?.default_unit ?? "" });
    setTargetOpen(true);
  }
  function openInitiative(initiative?: Initiative) {
    setEditingInitiative(initiative ?? null);
    setInitiativeForm(initiative ? { name: initiative.name, description: initiative.description, org_node: initiative.org_node ?? "none", owner: initiative.owner ? String(initiative.owner) : "none", status: initiative.status, due_date: initiative.due_date ?? "", anticipated_impact: initiative.anticipated_impact ? editableDecimal(initiative.anticipated_impact) : "" } : emptyInitiative);
    setInitiativeFormOpen(true);
    setInitiativesOpen(true);
  }
  function setInitiativesDialogOpen(open: boolean) {
    setInitiativesOpen(open);
    if (!open) {
      setEditingInitiative(null);
      setInitiativeFormOpen(false);
    }
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
  async function saveGoal(form: GoalForm) {
    if (!goal) return;
    try {
      setSaving(true);
      const payload = { ...form };
      delete payload.assessment_id;
      const updated = await TargetsApi.updateGoal(goal.id, { ...payload, name: form.name.trim(), description: form.description.trim(), material_topic: form.material_topic || null, material_subtopic: form.material_subtopic || null, source_assessment_topic: form.source_assessment_topic || null, owner: form.owner || null });
      setGoal(updated); setGoalEditorOpen(false); toast.success("Goal updated");
    } catch { toast.error("Unable to update this goal. Review the Materiality context and try again."); }
    finally { setSaving(false); }
  }
  async function saveInitiative() {
    if (!selected || !initiativeForm.name.trim()) return;
    const impact = initiativeForm.anticipated_impact ? Number(initiativeForm.anticipated_impact) : undefined;
    if (impact != null && (!Number.isFinite(impact) || impact < 0 || impact > 100)) { toast.error("Anticipated impact must be between 0 and 100."); return; }
    try {
      setSaving(true);
      const payload = { ...initiativeForm, name: initiativeForm.name.trim(), description: initiativeForm.description.trim(), org_node: initiativeForm.org_node === "none" ? null : initiativeForm.org_node, owner: initiativeForm.owner === "none" ? null : initiativeForm.owner, due_date: initiativeForm.due_date || null, anticipated_impact: initiativeForm.anticipated_impact || null };
      if (editingInitiative) await TargetsApi.updateInitiative(editingInitiative.id, payload); else await TargetsApi.createInitiative(selected, payload);
      await loadTarget(); setInitiativeFormOpen(false); toast.success(editingInitiative ? "Initiative updated" : "Initiative added");
    } catch { toast.error("Unable to save this initiative. Review the details and try again."); }
    finally { setSaving(false); }
  }

  return <AppShell title={goal?.name ?? "Goal"} description="KPI target planning and approved-data progress.">
    <main className="mx-auto w-full max-w-7xl space-y-4 px-0 pb-6">
      {loading ? <DetailSkeleton /> : error ? <Card><CardContent className="py-14 text-center text-destructive"><CircleAlert className="mx-auto mb-3 size-7" />{error}</CardContent></Card> : <>
        <nav className="flex items-center gap-1 text-xs text-muted-foreground"><Link to="/goals" className="font-medium hover:text-primary">Goals</Link><ChevronRight className="size-3.5" /><span className="truncate text-foreground">{goal?.name}</span></nav>
        <section className="flex flex-col justify-between gap-4 rounded-xl border border-[#D9DEE8] bg-white px-5 py-4 shadow-sm sm:flex-row sm:items-center"><div className="min-w-0 space-y-2"><div className="flex flex-wrap items-center gap-1.5"><Badge variant={goal?.status === "ACTIVE" ? "active" : "draft"}>{goal?.status.toLowerCase()}</Badge>{goal?.material_topic_name ? <Badge variant="secondary">{goal.material_topic_name}</Badge> : <Badge variant="default">Independent goal</Badge>}{goal?.owner_name && <span className="text-xs text-muted-foreground">Owner: {goal.owner_name}</span>}</div><div><h1 className="truncate text-2xl font-semibold tracking-tight text-[#22243A]">{goal?.name}</h1><p className="mt-1 max-w-3xl text-sm leading-5 text-muted-foreground">{goal?.description || "Define outcomes and connect their KPIs to approved ESG data."}</p></div></div><div className="flex shrink-0 flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => setGoalEditorOpen(true)}><Pencil className="mr-2 size-4" />Edit goal</Button><Button size="sm" variant="outline" disabled={!selected} onClick={() => openInitiative()}><ClipboardCheck className="mr-2 size-4" />Initiatives{initiatives.length ? ` (${initiatives.length})` : ""}</Button><Button size="sm" onClick={() => { setKpiForm(emptyKpi); setKpiOpen(true); }}><Plus className="mr-2 size-4" />Add KPI</Button></div></section>
        {kpis.length ? <>
          <section className="space-y-1"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Key performance indicators</p><Tabs value={selected} onValueChange={setSelected}><TabsList variant="line" className="h-10 w-full justify-start gap-5 overflow-x-auto rounded-none border-b border-[#D9DEE8] p-0">{visibleKpis.map((kpi) => <TabsTrigger key={kpi.id} value={kpi.id} className="!flex-none h-10 shrink-0 rounded-none border-b-2 border-transparent px-1 text-sm data-[state=active]:border-[#4A3FD6] data-[state=active]:text-[#4A3FD6] data-[state=active]:font-semibold">{kpi.name}</TabsTrigger>)}{kpis.length > visibleKpis.length && <Select value={selected} onValueChange={setSelected}><SelectTrigger size="sm" className="mb-1 h-8 w-36 shrink-0"><SelectValue placeholder={`+${kpis.length - visibleKpis.length} more`} /></SelectTrigger><SelectContent>{kpis.slice(visibleKpis.length).map((kpi) => <SelectItem key={kpi.id} value={kpi.id}>{kpi.name}</SelectItem>)}</SelectContent></Select>}</TabsList></Tabs></section>
          <section className="grid gap-3 md:grid-cols-3"><MetricCard title="Actual" value={actual?.actual_value ?? "No approved data"} unit={activeTarget?.baseline_unit_code ?? selectedKpi?.default_unit_code} subtitle={actual ? "Latest approved M5 value" : "Only approved M5 submissions appear here"} icon={<LineChartIcon className="size-4" />} /><MetricCard title="Target trajectory" value={activeTarget ? `${formatMetric(activeTarget.baseline_value)} → ${formatMetric(activeTarget.target_value)}` : "Not configured"} unit={activeTarget?.baseline_unit_code} subtitle="Straight-line plan between baseline and endpoint" icon={<TargetIcon className="size-4" />} /><MetricCard title="Target" value={activeTarget?.target_value ?? "Not configured"} unit={activeTarget?.target_unit_code} subtitle={activeTarget?.target_period_name ?? "Configure target to begin"} icon={<TargetIcon className="size-4" />} /></section>
          <section className="grid gap-4 lg:grid-cols-[minmax(280px,0.72fr)_minmax(0,1.8fr)]"><BaselinePanel target={activeTarget} onConfigure={() => openTarget(activeTarget)} /><ProgressPanel kpi={selectedKpi} target={activeTarget} graph={graph} progress={progress} /></section>
        </> : <Card className="border-dashed"><CardContent className="flex min-h-64 flex-col items-center justify-center p-8 text-center"><span className="mb-4 grid size-12 place-items-center rounded-full bg-primary/10"><TargetIcon className="size-6 text-primary" /></span><h2 className="text-lg font-semibold">Add a KPI to begin planning</h2><p className="mt-2 max-w-md text-sm text-muted-foreground">Choose an active canonical M4 datapoint. Its approved M5 values will become the KPI’s actuals.</p><Button className="mt-5" onClick={() => setKpiOpen(true)}><Plus className="mr-2 size-4" />Add KPI</Button></CardContent></Card>}
      </>}
    </main>
    <Dialog open={kpiOpen} onOpenChange={setKpiOpen}><DialogContent className="max-h-[90vh] gap-3 overflow-y-auto p-5 sm:max-w-xl"><DialogHeader className="pr-8"><DialogTitle className="text-lg font-semibold">Add KPI</DialogTitle></DialogHeader><div className="space-y-3"><Field label="Canonical M4 datapoint"><Select value={kpiForm.datapoint} onValueChange={selectDatapoint}><SelectTrigger><SelectValue placeholder="Select a numeric datapoint" /></SelectTrigger><SelectContent>{datapoints.map((datapoint) => <SelectItem key={datapoint.id} value={datapoint.id}>{datapoint.label} · {datapoint.code}</SelectItem>)}</SelectContent></Select></Field><div className="grid gap-3 sm:grid-cols-2"><Field label="KPI name"><Input value={kpiForm.name} onChange={(event) => setKpiForm({ ...kpiForm, name: event.target.value })} /></Field><Field label="Stable KPI code"><Input value={kpiForm.code} onChange={(event) => setKpiForm({ ...kpiForm, code: event.target.value })} /></Field></div><div className="grid gap-3 sm:grid-cols-2"><Field label="Direction"><Select value={kpiForm.direction} onValueChange={(value) => setKpiForm({ ...kpiForm, direction: value as Direction })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="REDUCE">Reduce</SelectItem><SelectItem value="INCREASE">Increase</SelectItem><SelectItem value="MAINTAIN">Maintain</SelectItem></SelectContent></Select></Field><Field label="Aggregation"><Select value={kpiForm.aggregation} onValueChange={(value) => setKpiForm({ ...kpiForm, aggregation: value as KpiForm["aggregation"] })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="SUM">Sum approved values</SelectItem><SelectItem value="AVG">Average approved values</SelectItem><SelectItem value="LATEST">Latest approved value</SelectItem><SelectItem value="COUNT">Count approved answers</SelectItem></SelectContent></Select></Field></div><Field label="Description"><Textarea className="min-h-18" value={kpiForm.description} onChange={(event) => setKpiForm({ ...kpiForm, description: event.target.value })} /></Field></div><DialogFooter className="-mx-5 -mb-5 px-5 py-3"><Button variant="outline" onClick={() => setKpiOpen(false)}>Cancel</Button><Button disabled={saving || !kpiForm.datapoint || !kpiForm.name || !kpiForm.code} onClick={() => void saveKpi()}>{saving ? "Saving…" : "Add KPI"}</Button></DialogFooter></DialogContent></Dialog>
    <Dialog open={targetOpen} onOpenChange={setTargetOpen}><DialogContent className="max-h-[90vh] gap-3 overflow-y-auto p-5 sm:max-w-xl"><DialogHeader className="pr-8"><DialogTitle className="text-lg font-semibold">{editingTarget ? "Edit target" : "Configure target"}</DialogTitle></DialogHeader><TargetFields form={targetForm} periods={periods} units={applicableUnits} orgNodes={orgNodes} onChange={setTargetForm} /><DialogFooter className="-mx-5 -mb-5 px-5 py-3"><Button variant="outline" onClick={() => setTargetOpen(false)}>Cancel</Button><Button disabled={saving || !targetForm.baseline_period || !targetForm.target_period || !targetForm.baseline_value || !targetForm.target_value} onClick={() => void saveTarget()}>{saving ? "Saving…" : editingTarget ? "Save target" : "Configure target"}</Button></DialogFooter></DialogContent></Dialog>
    <GoalEditorDialog open={goalEditorOpen} goal={goal} saving={saving} onOpenChange={setGoalEditorOpen} onSave={(form) => void saveGoal(form)} />
    <InitiativesDialog open={initiativesOpen} onOpenChange={setInitiativesDialogOpen} kpi={selectedKpi} initiatives={initiatives} users={users} orgNodes={orgNodes} editing={editingInitiative} formOpen={initiativeFormOpen} form={initiativeForm} saving={saving} onEdit={openInitiative} onChange={setInitiativeForm} onSave={() => void saveInitiative()} />
  </AppShell>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>; }
function MetricCard({ title, value, unit, subtitle, icon }: { title: string; value: string; unit?: string; subtitle: string; icon: React.ReactNode }) { const isState = value === "No approved data" || value === "Not configured"; return <Card size="sm" className="border-[#D9DEE8] shadow-none"><CardHeader className="border-b-0 px-4 py-3"><div className="flex items-center gap-2 text-muted-foreground">{icon}<CardTitle className="text-sm font-medium">{title}</CardTitle></div></CardHeader><CardContent className="px-4 py-1 pb-3"><p className="text-xl font-semibold tracking-tight text-[#22243A]">{isState ? value : formatMetric(value)}{!isState && unit ? <span className="ml-1.5 text-xs font-medium text-muted-foreground">{unit}</span> : null}</p><p className="mt-1 text-xs leading-4 text-muted-foreground">{subtitle}</p></CardContent></Card>; }
function BaselinePanel({ target, onConfigure }: { target?: Target; onConfigure: () => void }) { return <Card size="sm" className="border-[#D9DEE8] shadow-none"><CardHeader className="border-b-0 px-4 py-4"><CardTitle className="text-base">Baseline & target</CardTitle><CardDescription className="mt-1 text-xs leading-5">Where this KPI starts, why the target was set, and where it should reach.</CardDescription></CardHeader><CardContent className="space-y-4 px-4 py-0 pb-4">{target ? <dl className="space-y-3 text-sm"><div><dt className="text-xs text-muted-foreground">Baseline</dt><dd className="mt-0.5 font-medium">{formatMetric(target.baseline_value)} {target.baseline_unit_code} · {target.baseline_period_name}</dd><p className="mt-0.5 text-xs text-muted-foreground">{target.baseline_source === "SYSTEM_DATA" ? "Frozen from approved system data" : "Reference/manual baseline"}</p></div><div><dt className="text-xs text-muted-foreground">Target endpoint</dt><dd className="mt-0.5 font-medium">{formatMetric(target.target_value)} {target.target_unit_code} · {target.target_period_name}</dd></div><div><dt className="text-xs text-muted-foreground">Basis</dt><dd className="mt-0.5">{target.basis.replaceAll("_", " ").toLowerCase()}</dd></div>{target.org_node_name && <div><dt className="text-xs text-muted-foreground">Scope</dt><dd className="mt-0.5">{target.org_node_name}</dd></div>}</dl> : <p className="text-sm leading-5 text-muted-foreground">Set a frozen baseline and an endpoint to make this KPI’s target trajectory visible.</p>}<Button size="sm" className="w-full" variant={target ? "outline" : "default"} onClick={onConfigure}>{target ? "Edit target configuration" : "Configure target"}</Button></CardContent></Card>; }
function ProgressPanel({ kpi, target, graph, progress }: { kpi?: KPI; target?: Target; graph: Array<{ name: string; trajectory?: number; actual?: number; target?: number }>; progress?: TargetProgress }) { return <Card size="sm" className="border-[#D9DEE8] shadow-none"><CardHeader className="px-4 py-3"><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-base">{kpi?.name ?? "KPI"} progress</CardTitle><CardDescription className="mt-1 text-xs leading-5">Approved actuals and a deterministic target trajectory by reporting period.</CardDescription></div>{target && <Badge variant="info">{target.target_type.toLowerCase()}</Badge>}</div></CardHeader><CardContent className="h-[300px] px-3 py-2 sm:px-4">{graph.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={graph} margin={{ top: 16, right: 12, left: 2, bottom: 4 }}><CartesianGrid vertical={false} stroke="#ECEEF5" /><XAxis dataKey="name" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={{ stroke: "#D9DEE8" }} tickLine={false} /><YAxis tick={{ fontSize: 11, fill: "#6B7280" }} tickFormatter={formatMetric} axisLine={false} tickLine={false} width={64} /><Tooltip contentStyle={{ border: "1px solid #D9DEE8", borderRadius: 8, boxShadow: "0 4px 12px rgba(30, 33, 48, 0.12)" }} formatter={(value: number | string | undefined) => value == null ? "No data" : formatMetric(value)} /><Line type="linear" dataKey="trajectory" name="Target trajectory" stroke="#4A3FD6" strokeWidth={2.5} dot={{ r: 3, fill: "#FFFFFF", strokeWidth: 2 }} connectNulls /><Line type="monotone" dataKey="actual" name="Approved actual" stroke="#22C55E" strokeWidth={2.5} dot={{ r: 3.5, fill: "#FFFFFF", strokeWidth: 2 }} connectNulls /><Line type="linear" dataKey="target" name="Target endpoint" stroke="#4A3FD6" strokeWidth={0} dot={{ r: 4.5, fill: "#FFFFFF", stroke: "#4A3FD6", strokeWidth: 2.5 }} /></LineChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-center"><div><LineChartIcon className="mx-auto mb-2 size-6 text-muted-foreground" /><p className="font-medium">No target trajectory yet</p><p className="mt-1 text-sm text-muted-foreground">Configure a baseline and target to show the planned path. Approved actuals will appear as they are collected.</p></div></div>}</CardContent>{progress && !progress.progress.some((row) => row.actual_value != null) && <div className="border-t border-[#ECEEF5] px-4 py-2 text-xs text-muted-foreground">No approved M5 data is available in this target window yet. Values are never shown as zero.</div>}</Card>; }
function TargetFields({ form, periods, units, orgNodes, onChange }: { form: TargetForm; periods: ReportingPeriod[]; units: Unit[]; orgNodes: OrgNode[]; onChange: (value: TargetForm) => void }) { const update = (key: keyof TargetForm, value: string) => onChange({ ...form, [key]: value }); return <div className="space-y-3"><div className="grid gap-3 sm:grid-cols-2"><Field label="Target scope"><Select value={form.org_node} onValueChange={(value) => update("org_node", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Company-wide</SelectItem>{orgNodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Target type"><Select value={form.target_type} onValueChange={(value) => update("target_type", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ABSOLUTE">Absolute</SelectItem><SelectItem value="INTENSITY">Intensity</SelectItem><SelectItem value="PERCENTAGE">Percentage</SelectItem></SelectContent></Select></Field></div><div className="grid gap-3 sm:grid-cols-2"><Field label="Baseline reporting period"><Select value={form.baseline_period} onValueChange={(value) => update("baseline_period", value)}><SelectTrigger><SelectValue placeholder="Choose baseline period" /></SelectTrigger><SelectContent>{periods.map((period) => <SelectItem key={period.id} value={period.id}>{period.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Baseline value"><Input inputMode="decimal" value={form.baseline_value} onChange={(event) => update("baseline_value", event.target.value)} placeholder="e.g. 120000" /></Field><Field label="Target reporting period"><Select value={form.target_period} onValueChange={(value) => update("target_period", value)}><SelectTrigger><SelectValue placeholder="Choose target period" /></SelectTrigger><SelectContent>{periods.map((period) => <SelectItem key={period.id} value={period.id}>{period.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Target value"><Input inputMode="decimal" value={form.target_value} onChange={(event) => update("target_value", event.target.value)} placeholder="e.g. 90000" /></Field></div><div className="grid gap-3 sm:grid-cols-2"><Field label="Unit"><Select value={form.baseline_unit} onValueChange={(value) => onChange({ ...form, baseline_unit: value, target_unit: value })}><SelectTrigger><SelectValue placeholder="Choose unit" /></SelectTrigger><SelectContent>{units.map((unit) => <SelectItem key={unit.id} value={unit.id}>{unit.name} ({unit.code})</SelectItem>)}</SelectContent></Select></Field><Field label="Target basis"><Select value={form.basis} onValueChange={(value) => update("basis", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{targetBasis.map((basis) => <SelectItem key={basis} value={basis}>{basis.replaceAll("_", " ").toLowerCase()}</SelectItem>)}</SelectContent></Select></Field></div><Field label="Rationale"><Textarea className="min-h-18" value={form.rationale} onChange={(event) => update("rationale", event.target.value)} placeholder="Why is this endpoint appropriate?" /></Field><Field label="Methodology"><Textarea className="min-h-18" value={form.methodology} onChange={(event) => update("methodology", event.target.value)} placeholder="Optional target methodology or assumptions" /></Field></div>; }
function ownerLabel(user: UserData) { return user.full_name || [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username; }
function statusLabel(status: Initiative["status"]) { return status[0] + status.slice(1).toLowerCase(); }
function initiativeVariant(status: Initiative["status"]): "draft" | "active" | "approved" | "inactive" { const variants: Record<Initiative["status"], "draft" | "active" | "approved" | "inactive"> = { PLANNED: "draft", ONGOING: "active", COMPLETE: "approved", PARKED: "inactive" }; return variants[status]; }
function InitiativesDialog({ open, onOpenChange, kpi, initiatives, users, orgNodes, editing, formOpen, form, saving, onEdit, onChange, onSave }: { open: boolean; onOpenChange: (open: boolean) => void; kpi?: KPI; initiatives: Initiative[]; users: UserData[]; orgNodes: OrgNode[]; editing: Initiative | null; formOpen: boolean; form: InitiativeForm; saving: boolean; onEdit: (initiative?: Initiative) => void; onChange: (form: InitiativeForm) => void; onSave: () => void }) {
  const update = (patch: Partial<InitiativeForm>) => onChange({ ...form, ...patch });
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[90vh] gap-3 overflow-y-auto p-5 sm:max-w-3xl"><DialogHeader className="pr-8"><DialogTitle className="text-lg font-semibold">Initiatives</DialogTitle><p className="text-sm text-muted-foreground">{kpi ? `Delivery activity for ${kpi.name}` : "Choose a KPI to manage its delivery activity."}</p></DialogHeader>{kpi && <div className="space-y-4"><div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[#F8F9FC] px-3 py-2"><div><p className="text-sm font-medium">{kpi.name}</p><p className="text-xs text-muted-foreground">Planning records do not change approved KPI actuals.</p></div><Button size="sm" variant="outline" onClick={() => onEdit()}><Plus className="mr-1.5 size-3.5" />Add initiative</Button></div>{initiatives.length ? <div className="overflow-x-auto rounded-lg border border-[#D9DEE8]"><Table><TableHeader><TableRow><TableHead>Initiative</TableHead><TableHead>Status</TableHead><TableHead>Owner</TableHead><TableHead>Scope</TableHead><TableHead>Due</TableHead><TableHead>Impact</TableHead><TableHead className="w-14" /></TableRow></TableHeader><TableBody>{initiatives.map((initiative) => <TableRow key={initiative.id}><TableCell className="min-w-52"><p className="font-medium">{initiative.name}</p>{initiative.description && <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{initiative.description}</p>}</TableCell><TableCell><Badge variant={initiativeVariant(initiative.status)}>{statusLabel(initiative.status)}</Badge></TableCell><TableCell className="whitespace-nowrap text-sm">{initiative.owner_name ?? "—"}</TableCell><TableCell className="whitespace-nowrap text-sm">{initiative.org_node_name ?? "Company-wide"}</TableCell><TableCell className="whitespace-nowrap text-sm">{initiative.due_date ?? "—"}</TableCell><TableCell className="whitespace-nowrap text-sm">{initiative.anticipated_impact ? `${formatMetric(initiative.anticipated_impact)}%` : "—"}</TableCell><TableCell><Button size="icon-sm" variant="ghost" aria-label={`Edit ${initiative.name}`} onClick={() => onEdit(initiative)}><Pencil className="size-4" /></Button></TableCell></TableRow>)}</TableBody></Table></div> : <div className="rounded-lg border border-dashed border-[#D9DEE8] px-4 py-8 text-center"><p className="text-sm font-medium">No initiatives for this KPI</p><p className="mt-1 text-xs text-muted-foreground">Add a focused delivery action to record who owns it, where it applies, and its anticipated impact.</p></div>}{formOpen && <div className="border-t border-[#ECEEF5] pt-4"><div className="mb-3 flex items-center justify-between"><p className="text-sm font-semibold">{editing ? "Edit initiative" : "Add initiative"}</p>{editing && <Button size="sm" variant="ghost" onClick={() => onEdit()}>Add another</Button>}</div><div className="grid gap-3 sm:grid-cols-2"><Field label="Initiative name"><Input value={form.name} onChange={(event) => update({ name: event.target.value })} placeholder="e.g. Install water-efficient fixtures" /></Field><Field label="Status"><Select value={form.status} onValueChange={(value) => update({ status: value as Initiative["status"] })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(["PLANNED", "ONGOING", "COMPLETE", "PARKED"] as Initiative["status"][]).map((status) => <SelectItem key={status} value={status}>{statusLabel(status)}</SelectItem>)}</SelectContent></Select></Field><Field label="Business unit / OrgNode"><Select value={form.org_node} onValueChange={(value) => update({ org_node: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Company-wide</SelectItem>{orgNodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Owner"><Select value={form.owner} onValueChange={(value) => update({ owner: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">No owner assigned</SelectItem>{users.map((user) => <SelectItem key={user.id} value={String(user.id)}>{ownerLabel(user)}</SelectItem>)}</SelectContent></Select></Field><Field label="Due date"><Input type="date" value={form.due_date} onChange={(event) => update({ due_date: event.target.value })} /></Field><Field label="Anticipated impact (%)"><Input inputMode="decimal" value={form.anticipated_impact} onChange={(event) => update({ anticipated_impact: event.target.value })} placeholder="0–100" /></Field></div><div className="mt-3"><Field label="Comments"><Textarea className="min-h-20" value={form.description} onChange={(event) => update({ description: event.target.value })} placeholder="Notes, scope, or context for this initiative" /></Field></div><div className="mt-3 flex justify-end gap-2"><Button size="sm" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button size="sm" disabled={saving || !form.name.trim()} onClick={onSave}>{saving ? "Saving…" : editing ? "Save changes" : "Add initiative"}</Button></div></div>}</div>}<DialogFooter className="-mx-5 -mb-5 px-5 py-3"><Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button></DialogFooter></DialogContent></Dialog>;
}
function DetailSkeleton() { return <div className="space-y-4"><Skeleton className="h-4 w-52" /><Skeleton className="h-32 w-full" /><div className="grid gap-3 md:grid-cols-3">{[1, 2, 3].map((key) => <Skeleton key={key} className="h-28" />)}</div><Skeleton className="h-80 w-full" /></div>; }
