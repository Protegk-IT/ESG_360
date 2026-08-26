import { useEffect, useMemo, useState } from "react";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import TopicLibraryApi from "@/api/materiality/TopicLibraryApi";
import UserApi from "@/api/users/UserApi";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { AssessmentTopic, MaterialityAssessment } from "@/types/materiality/assessment";
import type { MaterialSubTopic, MaterialTopic } from "@/types/materiality/materiality";
import type { Goal, GoalStatus } from "@/types/targets/targets";
import type { UserData } from "@/types/user";

export type GoalForm = Pick<Goal, "name" | "description" | "material_topic" | "material_subtopic" | "source_assessment_topic" | "owner" | "status"> & { assessment_id?: string | null };

const emptyGoal: GoalForm = { name: "", description: "", material_topic: null, material_subtopic: null, source_assessment_topic: null, owner: null, status: "DRAFT", assessment_id: null };

export function goalFormFor(goal?: Goal | null): GoalForm {
  if (!goal) return { ...emptyGoal };
  return {
    name: goal.name,
    description: goal.description,
    material_topic: goal.material_topic ?? null,
    material_subtopic: goal.material_subtopic ?? null,
    source_assessment_topic: goal.source_assessment_topic ?? null,
    owner: goal.owner ?? null,
    status: goal.status,
    assessment_id: goal.source_assessment_id ?? null,
  };
}

type Props = {
  open: boolean;
  goal?: Goal | null;
  saving: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (form: GoalForm) => void;
};

function userLabel(user: UserData) {
  return user.full_name || [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;
}

export default function GoalEditorDialog({ open, goal, saving, onOpenChange, onSave }: Props) {
  const [form, setForm] = useState<GoalForm>(() => goalFormFor(goal));
  const [topics, setTopics] = useState<MaterialTopic[]>([]);
  const [subtopics, setSubtopics] = useState<MaterialSubTopic[]>([]);
  const [users, setUsers] = useState<UserData[]>([]);
  const [assessments, setAssessments] = useState<MaterialityAssessment[]>([]);
  const [assessmentTopics, setAssessmentTopics] = useState<AssessmentTopic[]>([]);

  // Reset only when the dialog opens for a different persisted Goal.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (open) setForm(goalFormFor(goal)); }, [open, goal]);
  useEffect(() => {
    if (!open) return;
    void Promise.allSettled([TopicLibraryApi.getTopics(), TopicLibraryApi.getSubTopics(), UserApi.getAll(), AssessmentApi.getAll()]).then((results) => {
      if (results[0].status === "fulfilled") setTopics(results[0].value.data);
      if (results[1].status === "fulfilled") setSubtopics(results[1].value.data);
      if (results[2].status === "fulfilled") setUsers(results[2].value.data.filter((user) => user.is_active));
      if (results[3].status === "fulfilled") setAssessments(results[3].value.data);
    });
  }, [open]);
  useEffect(() => {
    if (!form.assessment_id) return;
    void AssessmentApi.getTopicsByAssessment(form.assessment_id).then((response) => setAssessmentTopics(response.data.filter((topic) => topic.is_included))).catch(() => setAssessmentTopics([]));
  }, [form.assessment_id]);

  const visibleSubtopics = useMemo(() => subtopics.filter((subtopic) => subtopic.topic === form.material_topic), [form.material_topic, subtopics]);
  const isSaveable = Boolean(form.name.trim());
  const update = (patch: Partial<GoalForm>) => setForm((current) => ({ ...current, ...patch }));

  function chooseMaterialTopic(value: string) {
    update({ material_topic: value === "none" ? null : value, material_subtopic: null, source_assessment_topic: null, assessment_id: null });
  }
  function chooseSubtopic(value: string) {
    update({ material_subtopic: value === "none" ? null : value, source_assessment_topic: null, assessment_id: null });
  }
  function chooseAssessmentTopic(value: string) {
    if (value === "none") { update({ source_assessment_topic: null }); return; }
    const assessmentTopic = assessmentTopics.find((topic) => topic.id === value);
    const subtopic = subtopics.find((item) => item.id === assessmentTopic?.subtopic);
    update({
      source_assessment_topic: value,
      material_topic: subtopic?.topic ?? form.material_topic,
      material_subtopic: subtopic?.id ?? form.material_subtopic,
    });
  }

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[90vh] gap-3 overflow-y-auto p-5 sm:max-w-xl">
      <DialogHeader className="pr-8"><DialogTitle className="text-lg font-semibold">{goal ? "Edit goal" : "Add goal"}</DialogTitle></DialogHeader>
      <div className="space-y-3">
        <Field label="Goal name"><Input value={form.name} onChange={(event) => update({ name: event.target.value })} placeholder="e.g. Water stewardship" /></Field>
        <Field label="Description"><Textarea className="min-h-20" value={form.description} onChange={(event) => update({ description: event.target.value })} placeholder="What outcome is this goal intended to achieve?" /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Owner"><Select value={form.owner ?? "none"} onValueChange={(value) => update({ owner: value === "none" ? null : value })}><SelectTrigger><SelectValue placeholder="No owner assigned" /></SelectTrigger><SelectContent><SelectItem value="none">No owner assigned</SelectItem>{users.map((user) => <SelectItem key={user.id} value={String(user.id)}>{userLabel(user)}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Status"><Select value={form.status} onValueChange={(value) => update({ status: value as GoalStatus })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(["DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"] as GoalStatus[]).map((status) => <SelectItem key={status} value={status}>{status[0] + status.slice(1).toLowerCase()}</SelectItem>)}</SelectContent></Select></Field>
        </div>
        <div className="border-t border-[#ECEEF5] pt-3"><p className="mb-2 text-sm font-medium">Optional Materiality context</p><div className="grid gap-3 sm:grid-cols-2">
          <Field label="Material Topic"><Select value={form.material_topic ?? "none"} onValueChange={chooseMaterialTopic}><SelectTrigger><SelectValue placeholder="No Materiality context" /></SelectTrigger><SelectContent><SelectItem value="none">No Materiality context</SelectItem>{topics.map((topic) => <SelectItem key={topic.id} value={topic.id}>{topic.name}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Material subtopic"><Select disabled={!form.material_topic} value={form.material_subtopic ?? "none"} onValueChange={chooseSubtopic}><SelectTrigger><SelectValue placeholder="None" /></SelectTrigger><SelectContent><SelectItem value="none">None</SelectItem>{visibleSubtopics.map((subtopic) => <SelectItem key={subtopic.id} value={subtopic.id}>{subtopic.name}</SelectItem>)}</SelectContent></Select></Field>
        </div><div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Assessment provenance"><Select value={form.assessment_id ?? "none"} onValueChange={(value) => update({ assessment_id: value === "none" ? null : value, source_assessment_topic: null })}><SelectTrigger><SelectValue placeholder="No assessment provenance" /></SelectTrigger><SelectContent><SelectItem value="none">No assessment provenance</SelectItem>{assessments.map((assessment) => <SelectItem key={assessment.id} value={assessment.id}>{assessment.name}</SelectItem>)}</SelectContent></Select></Field>
          <Field label="Assessment topic"><Select disabled={!form.assessment_id} value={form.source_assessment_topic ?? "none"} onValueChange={chooseAssessmentTopic}><SelectTrigger><SelectValue placeholder="Select provenance topic" /></SelectTrigger><SelectContent><SelectItem value="none">None</SelectItem>{assessmentTopics.map((topic) => <SelectItem key={topic.id} value={topic.id}>{topic.topic_name} · {topic.subtopic_name}</SelectItem>)}</SelectContent></Select></Field>
        </div><p className="mt-2 text-xs leading-5 text-muted-foreground">Materiality is optional. Selecting an assessment topic safely aligns the reusable Topic Library links; removing this context never recreates existing KPIs or targets.</p></div>
      </div>
      <DialogFooter className="-mx-5 -mb-5 px-5 py-3"><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button disabled={saving || !isSaveable} onClick={() => onSave(form)}>{saving ? "Saving…" : goal ? "Save changes" : "Create goal"}</Button></DialogFooter>
    </DialogContent>
  </Dialog>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>; }
