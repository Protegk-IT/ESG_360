import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Pencil, Plus, Search, Target as TargetIcon, UserRound } from "lucide-react";
import { toast } from "sonner";

import AppShell from "@/components/layout/AppShell";
import { TargetsApi } from "@/api/targets/TargetsApi";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Goal, GoalStatus } from "@/types/targets/targets";
import GoalEditorDialog, { goalFormFor, type GoalForm } from "./GoalEditorDialog";

const statusVariant: Record<GoalStatus, "draft" | "active" | "approved" | "inactive"> = { DRAFT: "draft", ACTIVE: "active", COMPLETED: "approved", ARCHIVED: "inactive" };

export default function GoalsList() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [saving, setSaving] = useState(false);

  const loadGoals = useCallback(async (term = search) => {
    try { setLoading(true); setError(""); setGoals(await TargetsApi.goals(term.trim() ? { search: term.trim() } : undefined)); }
    catch { setError("Goals could not be loaded. Check your access and try again."); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => { const timer = window.setTimeout(() => void loadGoals(), 250); return () => window.clearTimeout(timer); }, [loadGoals]);
  const summary = useMemo(() => `${goals.length} strategic ${goals.length === 1 ? "goal" : "goals"}`, [goals.length]);
  const openCreate = () => { setEditing(null); setEditorOpen(true); };
  const openEdit = (goal: Goal) => { setEditing(goal); setEditorOpen(true); };
  async function saveGoal(form: GoalForm) {
    if (!form.name.trim()) return;
    try {
      setSaving(true);
      const payload = { ...goalFormFor(), ...form, name: form.name.trim(), description: form.description?.trim() ?? "", material_topic: form.material_topic || null, material_subtopic: form.material_subtopic || null, source_assessment_topic: form.source_assessment_topic || null, owner: form.owner || null };
      delete payload.assessment_id;
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
    <GoalEditorDialog open={editorOpen} goal={editing} saving={saving} onOpenChange={setEditorOpen} onSave={(form) => void saveGoal(form)} />
  </AppShell>;
}

function GoalCard({ goal, onEdit }: { goal: Goal; onEdit: (goal: Goal) => void }) { return <Card size="sm" className="group min-h-52 border-[#D9DEE8] shadow-none hover:shadow-sm"><CardHeader className="space-y-3 border-b-0 px-4 py-4"><div className="flex items-start justify-between gap-3"><span className="grid size-9 place-items-center rounded-lg bg-primary/10"><TargetIcon className="size-4 text-primary" /></span><div className="flex items-center gap-1"><Badge variant={statusVariant[goal.status]}>{goal.status.toLowerCase()}</Badge><Button variant="ghost" size="icon-sm" aria-label={`Edit ${goal.name}`} onClick={(event) => { event.preventDefault(); onEdit(goal); }}><Pencil className="size-4" /></Button></div></div><div><CardTitle className="line-clamp-2 text-base"><Link to={`/goals/${goal.id}`} className="outline-none hover:text-primary focus-visible:ring-2 focus-visible:ring-ring">{goal.name}</Link></CardTitle><CardDescription className="mt-1 line-clamp-2 min-h-10 text-xs leading-5">{goal.description || "No description yet."}</CardDescription></div></CardHeader><CardContent className="mt-auto space-y-2 px-4 py-0"><div className="flex items-center gap-2 text-xs"><Badge variant={goal.material_topic_name ? "secondary" : "default"}>{goal.material_topic_name ?? "Independent goal"}</Badge>{goal.material_subtopic_name && <span className="truncate text-muted-foreground">{goal.material_subtopic_name}</span>}</div><div className="flex flex-wrap gap-x-3 gap-y-1.5 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><TargetIcon className="size-3.5" />{goal.kpi_count} KPI{goal.kpi_count === 1 ? "" : "s"}</span>{goal.owner_name && <span className="inline-flex items-center gap-1"><UserRound className="size-3.5" />{goal.owner_name}</span>}</div></CardContent><CardFooter className="mt-4 border-t border-[#ECEEF5] bg-transparent px-4 py-2.5"><Link className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline" to={`/goals/${goal.id}`}>Open goal <ArrowRight className="size-3.5" /></Link></CardFooter></Card>; }

function GoalSkeletons() { return <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((key) => <Card key={key} size="sm" className="shadow-none"><CardHeader className="border-b-0"><Skeleton className="size-9" /><Skeleton className="h-5 w-3/4" /><Skeleton className="h-8 w-full" /></CardHeader><CardContent className="py-0"><Skeleton className="h-3.5 w-1/2" /></CardContent></Card>)}</section>; }
