import api from "@/services/api";
import type { Goal, Initiative, KPI, Target, TargetProgress } from "@/types/targets/targets";

type Envelope<T> = { success: boolean; data: T };
const unwrap = <T>(promise: Promise<{ data: Envelope<T> }>) => promise.then((response) => response.data.data);
export const TargetsApi = {
  goals: (params?: Record<string, string>) => unwrap<Goal[]>(api.get("/targets/goals/", { params })),
  goal: (id: string) => unwrap<Goal>(api.get(`/targets/goals/${id}/`)),
  createGoal: (body: Partial<Goal>) => unwrap<Goal>(api.post("/targets/goals/", body)),
  updateGoal: (id: string, body: Partial<Goal>) => unwrap<Goal>(api.patch(`/targets/goals/${id}/`, body)),
  kpis: (goal: string) => unwrap<KPI[]>(api.get(`/targets/goals/${goal}/kpis/`)),
  createKpi: (goal: string, body: Partial<KPI>) => unwrap<KPI>(api.post(`/targets/goals/${goal}/kpis/`, body)),
  updateKpi: (id: string, body: Partial<KPI>) => unwrap<KPI>(api.patch(`/targets/kpis/${id}/`, body)),
  targets: (kpi: string) => unwrap<Target[]>(api.get(`/targets/kpis/${kpi}/targets/`)),
  createTarget: (kpi: string, body: Partial<Target>) => unwrap<Target>(api.post(`/targets/kpis/${kpi}/targets/`, body)),
  updateTarget: (id: string, body: Partial<Target>) => unwrap<Target>(api.patch(`/targets/targets/${id}/`, body)),
  progress: (id: string) => unwrap<TargetProgress>(api.get(`/targets/targets/${id}/progress/`)),
  initiatives: (kpi: string) => unwrap<Initiative[]>(api.get(`/targets/kpis/${kpi}/initiatives/`)),
  createInitiative: (kpi: string, body: Partial<Initiative>) => unwrap<Initiative>(api.post(`/targets/kpis/${kpi}/initiatives/`, body)),
  updateInitiative: (id: string, body: Partial<Initiative>) => unwrap<Initiative>(api.patch(`/targets/initiatives/${id}/`, body)),
};
