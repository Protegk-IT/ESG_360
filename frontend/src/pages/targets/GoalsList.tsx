import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, Pencil, Plus, Search, Target as TargetIcon, UserRound } from "lucide-react";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { TargetsApi } from "@/api/targets/TargetsApi";
import TopicLibraryApi from "@/api/materiality/TopicLibraryApi";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { Goal, GoalStatus } from "@/types/targets/targets";
import type { MaterialSubTopic, MaterialTopic } from "@/types/materiality/materiality";

type GoalForm = Pick<Goal, "name" | "description" | "material_topic" | "material_subtopic" | "status">;

const emptyGoal: GoalForm = { name: "", description: "", material_topic: null, material_subtopic: null, status: "DRAFT" };
const statusVariant: Record<GoalStatus, "draft" | "active" | "approved" | "inactive"> = { DRAFT: "draft", ACTIVE: "active", COMPLETED: "approved", ARCHIVED: "inactive" };

export default function GoalsList() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [topics, setTopics] = useState<MaterialTopic[]>([]);
  const [subtopics, setSubtopics] = useState<MaterialSubTopic[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [form, setForm] = useState<GoalForm>(emptyGoal);
  const [saving, setSaving] = useState(false);

  const loadGoals = useCallback(async (term = search) => {
    try { setLoading(true); setError(""); setGoals(await TargetsApi.goals(term.trim() ? { search: term.trim() } : undefined)); }
    catch { setError("Goals could not be loaded. Check your access and try again."); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => { const timer = window.setTimeout(() => void loadGoals(), 250); return () => window.clearTimeout(timer); }, [loadGoals]);
  useEffect(() => { void TopicLibraryApi.getTopics().then((response) => setTopics(response.data)).catch(() => setTopics([])); }, []);
  useEffect(() => {
    if (!form.material_topic) return;
    void TopicLibraryApi.getSubTopics({ topic: form.material_topic }).then((response) => setSubtopics(response.data)).catch(() => setSubtopics([]));
  }, [form.material_topic]);
  const summary = useMemo(() => `${goals.length} strategic ${goals.length === 1 ? "goal" : "goals"}`, [goals.length]);
  const openCreate = () => { setEditing(null); setForm(emptyGoal); setEditorOpen(true); };
  const openEdit = (goal: Goal) => { setEditing(goal); setForm({ name: goal.name, description: goal.description, material_topic: goal.material_topic ?? null, material_subtopic: goal.material_subtopic ?? null, status: goal.status }); setEditorOpen(true); };
  async function saveGoal() {
    if (!form.name.trim()) return;
    try {
      setSaving(true);
      const payload = { ...form, name: form.name.trim(), description: form.description?.trim() ?? "", material_topic: form.material_topic || null, material_subtopic: form.material_subtopic || null };
      if (editing) { await TargetsApi.updateGoal(editing.id, payload); toast.success("Goal updated"); } else { await TargetsApi.createGoal(payload); toast.success("Goal created"); }
      setEditorOpen(false); await loadGoals("");
    } catch { toast.error("Unable to save this goal. Review the details and try again."); }
    finally { setSaving(false); }
  }

  return <AppShell title="Goals" description="Set strategic sustainability outcomes and track approved ESG data against targets.">
    <main className="mx-auto w-full max-w-7xl space-y-7 px-4 pb-10 sm:px-6 lg:px-8">
      <section className="flex flex-col justify-between gap-5 rounded-2xl border bg-card p-5 shadow-sm sm:flex-row sm:items-end sm:p-7"><div className="max-w-2xl space-y-2"><Badge variant="info">Sustainability planning</Badge><h1 className="text-3xl font-semibold tracking-tight">Goals</h1><p className="text-sm leading-6 text-muted-foreground">Create independent goals or add Materiality context when useful. Each goal brings together KPIs, targets, approved actuals, and delivery initiatives.</p></div><Button onClick={openCreate}><Plus className="mr-2 size-4" />Add goal</Button></section>
      <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div className="relative w-full sm:max-w-md"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" placeholder="Search goals, topics, or owners" /></div><p className="text-sm text-muted-foreground">{loading ? "Loading goals…" : summary}</p></section>
      {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>}
      {loading ? <GoalSkeletons /> : goals.length ? <section className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{goals.map((goal) => <GoalCard key={goal.id} goal={goal} onEdit={openEdit} />)}</section> : <Card className="border-dashed"><CardContent className="flex min-h-72 flex-col items-center justify-center p-8 text-center"><span className="mb-4 grid size-12 place-items-center rounded-full bg-primary/10"><TargetIcon className="size-6 text-primary" /></span><h2 className="text-lg font-semibold">No goals yet</h2><p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">Start with an independent sustainability goal, then connect it to a Material Topic or assessment later if relevant.</p><Button className="mt-5" onClick={openCreate}><Plus className="mr-2 size-4" />Create your first goal</Button></CardContent></Card>}
    </main>
    <Dialog open={editorOpen} onOpenChange={setEditorOpen}><DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl"><DialogHeader><DialogTitle>{editing ? "Edit goal" : "Add goal"}</DialogTitle></DialogHeader><GoalFields form={form} topics={topics} subtopics={form.material_topic ? subtopics : []} onChange={setForm} /><DialogFooter><Button variant="outline" onClick={() => setEditorOpen(false)}>Cancel</Button><Button disabled={!form.name.trim() || saving} onClick={() => void saveGoal()}>{saving ? "Saving…" : editing ? "Save changes" : "Create goal"}</Button></DialogFooter></DialogContent></Dialog>
  </AppShell>;
}

function GoalCard({ goal, onEdit }: { goal: Goal; onEdit: (goal: Goal) => void }) { return <Card className="group flex min-h-64 flex-col overflow-hidden transition-shadow hover:shadow-md"><CardHeader className="space-y-4"><div className="flex items-start justify-between gap-3"><span className="grid size-10 place-items-center rounded-lg bg-primary/10"><TargetIcon className="size-5 text-primary" /></span><div className="flex items-center gap-2"><Badge variant={statusVariant[goal.status]}>{goal.status.toLowerCase()}</Badge><Button variant="ghost" size="icon-sm" aria-label={`Edit ${goal.name}`} onClick={(event) => { event.preventDefault(); onEdit(goal); }}><Pencil className="size-4" /></Button></div></div><div><CardTitle className="line-clamp-2 text-xl"><Link to={`/goals/${goal.id}`} className="outline-none hover:text-primary focus-visible:ring-2 focus-visible:ring-ring">{goal.name}</Link></CardTitle><CardDescription className="mt-2 line-clamp-2 min-h-10">{goal.description || "No description yet."}</CardDescription></div></CardHeader><CardContent className="mt-auto space-y-3"><div className="flex items-center gap-2 text-sm"><Badge variant={goal.material_topic_name ? "secondary" : "default"}>{goal.material_topic_name ?? "Independent goal"}</Badge>{goal.material_subtopic_name && <span className="truncate text-muted-foreground">{goal.material_subtopic_name}</span>}</div><div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted-foreground"><span className="inline-flex items-center gap-1.5"><TargetIcon className="size-4" />{goal.kpi_count} KPI{goal.kpi_count === 1 ? "" : "s"}</span>{goal.owner_name && <span className="inline-flex items-center gap-1.5"><UserRound className="size-4" />{goal.owner_name}</span>}</div></CardContent><CardFooter className="border-t bg-muted/20 px-6 py-3"><Link className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline" to={`/goals/${goal.id}`}>Open goal <CalendarDays className="size-4" /></Link></CardFooter></Card>; }

function GoalFields({ form, topics, subtopics, onChange }: { form: GoalForm; topics: MaterialTopic[]; subtopics: MaterialSubTopic[]; onChange: (value: GoalForm) => void }) { return <div className="space-y-4"><div className="space-y-2"><Label htmlFor="goal-name">Goal name</Label><Input id="goal-name" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} placeholder="e.g. Water stewardship" /></div><div className="space-y-2"><Label htmlFor="goal-description">Description</Label><Textarea id="goal-description" className="min-h-24" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} placeholder="What outcome is this goal intended to achieve?" /></div><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label>Material Topic <span className="font-normal text-muted-foreground">(optional)</span></Label><Select value={form.material_topic ?? "none"} onValueChange={(value) => onChange({ ...form, material_topic: value === "none" ? null : value, material_subtopic: null })}><SelectTrigger><SelectValue placeholder="No Materiality context" /></SelectTrigger><SelectContent><SelectItem value="none">No Materiality context</SelectItem>{topics.map((topic) => <SelectItem key={topic.id} value={topic.id}>{topic.name}</SelectItem>)}</SelectContent></Select></div><div className="space-y-2"><Label>Material subtopic <span className="font-normal text-muted-foreground">(optional)</span></Label><Select disabled={!form.material_topic} value={form.material_subtopic ?? "none"} onValueChange={(value) => onChange({ ...form, material_subtopic: value === "none" ? null : value })}><SelectTrigger><SelectValue placeholder="None" /></SelectTrigger><SelectContent><SelectItem value="none">None</SelectItem>{subtopics.map((subtopic) => <SelectItem key={subtopic.id} value={subtopic.id}>{subtopic.name}</SelectItem>)}</SelectContent></Select></div></div><div className="space-y-2"><Label>Status</Label><Select value={form.status} onValueChange={(value) => onChange({ ...form, status: value as GoalStatus })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(["DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"] as GoalStatus[]).map((status) => <SelectItem key={status} value={status}>{status[0] + status.slice(1).toLowerCase()}</SelectItem>)}</SelectContent></Select></div><p className="text-xs leading-5 text-muted-foreground">Materiality context is optional and can be associated or changed later without recreating the Goal, KPI, or Target.</p></div>; }
function GoalSkeletons() { return <section className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((key) => <Card key={key}><CardHeader><Skeleton className="size-10" /><Skeleton className="h-6 w-3/4" /><Skeleton className="h-10 w-full" /></CardHeader><CardContent><Skeleton className="h-4 w-1/2" /></CardContent></Card>)}</section>; }
