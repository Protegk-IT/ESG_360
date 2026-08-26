import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Pencil, Plus, Search, Target as TargetIcon, UserRound } from "lucide-react";
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
    <main className="mx-auto w-full max-w-7xl space-y-5 px-0 pb-6">
      <section className="flex flex-col justify-between gap-4 rounded-xl border border-[#D9DEE8] bg-white px-5 py-4 shadow-sm sm:flex-row sm:items-center"><div className="max-w-2xl space-y-1.5"><Badge variant="info">Sustainability planning</Badge><h1 className="text-2xl font-semibold tracking-tight text-[#22243A]">Goals</h1><p className="text-sm leading-5 text-muted-foreground">Plan measurable outcomes with approved ESG actuals, targets, and delivery activity in one place.</p></div><Button className="shrink-0" onClick={openCreate}><Plus className="mr-2 size-4" />Add goal</Button></section>
      <section className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div className="relative w-full sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-9 pl-9" placeholder="Search goals, topics, or owners" /></div><p className="text-xs text-muted-foreground">{loading ? "Loading goals…" : summary}</p></section>
      {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>}
      {loading ? <GoalSkeletons /> : goals.length ? <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{goals.map((goal) => <GoalCard key={goal.id} goal={goal} onEdit={openEdit} />)}</section> : <Card className="border-dashed shadow-none"><CardContent className="flex min-h-60 flex-col items-center justify-center p-6 text-center"><span className="mb-3 grid size-10 place-items-center rounded-full bg-primary/10"><TargetIcon className="size-5 text-primary" /></span><h2 className="text-base font-semibold">No goals yet</h2><p className="mt-1.5 max-w-md text-sm leading-5 text-muted-foreground">Start with an independent sustainability goal, then connect it to a Material Topic or assessment later if relevant.</p><Button className="mt-4" onClick={openCreate}><Plus className="mr-2 size-4" />Create your first goal</Button></CardContent></Card>}
    </main>
    <Dialog open={editorOpen} onOpenChange={setEditorOpen}><DialogContent className="max-h-[90vh] gap-3 overflow-y-auto p-5 sm:max-w-lg"><DialogHeader className="pr-8"><DialogTitle className="text-lg font-semibold">{editing ? "Edit goal" : "Add goal"}</DialogTitle></DialogHeader><GoalFields form={form} topics={topics} subtopics={form.material_topic ? subtopics : []} onChange={setForm} /><DialogFooter className="-mx-5 -mb-5 px-5 py-3"><Button variant="outline" onClick={() => setEditorOpen(false)}>Cancel</Button><Button disabled={!form.name.trim() || saving} onClick={() => void saveGoal()}>{saving ? "Saving…" : editing ? "Save changes" : "Create goal"}</Button></DialogFooter></DialogContent></Dialog>
  </AppShell>;
}

function GoalCard({ goal, onEdit }: { goal: Goal; onEdit: (goal: Goal) => void }) { return <Card size="sm" className="group min-h-52 border-[#D9DEE8] shadow-none hover:shadow-sm"><CardHeader className="space-y-3 border-b-0 px-4 py-4"><div className="flex items-start justify-between gap-3"><span className="grid size-9 place-items-center rounded-lg bg-primary/10"><TargetIcon className="size-4 text-primary" /></span><div className="flex items-center gap-1"><Badge variant={statusVariant[goal.status]}>{goal.status.toLowerCase()}</Badge><Button variant="ghost" size="icon-sm" aria-label={`Edit ${goal.name}`} onClick={(event) => { event.preventDefault(); onEdit(goal); }}><Pencil className="size-4" /></Button></div></div><div><CardTitle className="line-clamp-2 text-base"><Link to={`/goals/${goal.id}`} className="outline-none hover:text-primary focus-visible:ring-2 focus-visible:ring-ring">{goal.name}</Link></CardTitle><CardDescription className="mt-1 line-clamp-2 min-h-10 text-xs leading-5">{goal.description || "No description yet."}</CardDescription></div></CardHeader><CardContent className="mt-auto space-y-2 px-4 py-0"><div className="flex items-center gap-2 text-xs"><Badge variant={goal.material_topic_name ? "secondary" : "default"}>{goal.material_topic_name ?? "Independent goal"}</Badge>{goal.material_subtopic_name && <span className="truncate text-muted-foreground">{goal.material_subtopic_name}</span>}</div><div className="flex flex-wrap gap-x-3 gap-y-1.5 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><TargetIcon className="size-3.5" />{goal.kpi_count} KPI{goal.kpi_count === 1 ? "" : "s"}</span>{goal.owner_name && <span className="inline-flex items-center gap-1"><UserRound className="size-3.5" />{goal.owner_name}</span>}</div></CardContent><CardFooter className="mt-4 border-t border-[#ECEEF5] bg-transparent px-4 py-2.5"><Link className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline" to={`/goals/${goal.id}`}>Open goal <ArrowRight className="size-3.5" /></Link></CardFooter></Card>; }

function GoalFields({ form, topics, subtopics, onChange }: { form: GoalForm; topics: MaterialTopic[]; subtopics: MaterialSubTopic[]; onChange: (value: GoalForm) => void }) { return <div className="space-y-3"><div className="space-y-1.5"><Label htmlFor="goal-name">Goal name</Label><Input id="goal-name" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} placeholder="e.g. Water stewardship" /></div><div className="space-y-1.5"><Label htmlFor="goal-description">Description</Label><Textarea id="goal-description" className="min-h-20" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} placeholder="What outcome is this goal intended to achieve?" /></div><div className="grid gap-3 sm:grid-cols-2"><div className="space-y-1.5"><Label>Material Topic <span className="font-normal text-muted-foreground">(optional)</span></Label><Select value={form.material_topic ?? "none"} onValueChange={(value) => onChange({ ...form, material_topic: value === "none" ? null : value, material_subtopic: null })}><SelectTrigger><SelectValue placeholder="No Materiality context" /></SelectTrigger><SelectContent><SelectItem value="none">No Materiality context</SelectItem>{topics.map((topic) => <SelectItem key={topic.id} value={topic.id}>{topic.name}</SelectItem>)}</SelectContent></Select></div><div className="space-y-1.5"><Label>Material subtopic <span className="font-normal text-muted-foreground">(optional)</span></Label><Select disabled={!form.material_topic} value={form.material_subtopic ?? "none"} onValueChange={(value) => onChange({ ...form, material_subtopic: value === "none" ? null : value })}><SelectTrigger><SelectValue placeholder="None" /></SelectTrigger><SelectContent><SelectItem value="none">None</SelectItem>{subtopics.map((subtopic) => <SelectItem key={subtopic.id} value={subtopic.id}>{subtopic.name}</SelectItem>)}</SelectContent></Select></div></div><div className="space-y-1.5"><Label>Status</Label><Select value={form.status} onValueChange={(value) => onChange({ ...form, status: value as GoalStatus })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(["DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"] as GoalStatus[]).map((status) => <SelectItem key={status} value={status}>{status[0] + status.slice(1).toLowerCase()}</SelectItem>)}</SelectContent></Select></div><p className="text-xs leading-5 text-muted-foreground">Materiality context is optional and can be associated or changed later without recreating the Goal, KPI, or Target.</p></div>; }
function GoalSkeletons() { return <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((key) => <Card key={key} size="sm" className="shadow-none"><CardHeader className="border-b-0"><Skeleton className="size-9" /><Skeleton className="h-5 w-3/4" /><Skeleton className="h-8 w-full" /></CardHeader><CardContent className="py-0"><Skeleton className="h-3.5 w-1/2" /></CardContent></Card>)}</section>; }
