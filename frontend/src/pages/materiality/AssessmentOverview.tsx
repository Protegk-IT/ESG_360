import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Layers3,
  Loader2,
  Lock,
  Send,
  Sparkles,
  Users,
} from "lucide-react";

import AssessmentApi from "@/api/materiality/AssessmentApi";
import StakeholderApi from "@/api/materiality/StakeholderApi";
import SurveyApi from "@/api/materiality/surveyApi";
import AppShell from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { MaterialityAssessment } from "@/types/materiality/assessment";

type Counts = {
  topics: number;
  groups: number;
  stakeholders: number;
  surveyReady: boolean;
};

const statusLabel = (status: string) =>
  status
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function AssessmentOverview() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState<MaterialityAssessment | null>(
    null,
  );
  const [counts, setCounts] = useState<Counts>({
    topics: 0,
    groups: 0,
    stakeholders: 0,
    surveyReady: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!assessmentId) return;
    setLoading(true);
    setError(null);
    try {
      const [
        assessmentResult,
        topicsResult,
        groupsResult,
        stakeholdersResult,
        surveyResult,
      ] = await Promise.allSettled([
        AssessmentApi.getById(assessmentId),
        AssessmentApi.getTopicsByAssessment(assessmentId),
        StakeholderApi.getGroups(assessmentId),
        StakeholderApi.getStakeholders(assessmentId),
        SurveyApi.getSurvey(assessmentId),
      ]);
      if (assessmentResult.status !== "fulfilled")
        throw assessmentResult.reason;
      setAssessment(assessmentResult.value.data);
      setCounts({
        topics:
          topicsResult.status === "fulfilled"
            ? topicsResult.value.data.filter((topic) => topic.is_included)
                .length
            : 0,
        groups:
          groupsResult.status === "fulfilled"
            ? groupsResult.value.data.length
            : 0,
        stakeholders:
          stakeholdersResult.status === "fulfilled"
            ? stakeholdersResult.value.data.length
            : 0,
        surveyReady:
          surveyResult.status === "fulfilled" &&
          Boolean(surveyResult.value.data?.id),
      });
    } catch {
      setError("Unable to load this assessment overview.");
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

  const workflow = useMemo(() => {
    if (!assessmentId) return [];
    const base = `/materiality/assessments/${assessmentId}`;
    const scored = ["SCORED", "COMPLETED", "APPROVED"].includes(
      assessment?.status ?? "",
    );
    return [
      {
        title: "Scope",
        description: `${counts.topics} selected topic${counts.topics === 1 ? "" : "s"}`,
        icon: Layers3,
        url: `${base}/select-topics`,
        complete: counts.topics > 0,
      },
      {
        title: "Stakeholder setup",
        description: `${counts.groups} group${counts.groups === 1 ? "" : "s"} · ${counts.stakeholders} known stakeholder${counts.stakeholders === 1 ? "" : "s"}`,
        icon: Users,
        url: `${base}/stakeholders`,
        complete: counts.groups > 0,
      },
      {
        title: "Survey & responses",
        description: counts.surveyReady
          ? "Survey configured and ready to distribute"
          : "Generate the survey once scope is confirmed",
        icon: Send,
        url: `${base}/survey`,
        complete: counts.surveyReady,
      },
      {
        title: "Scoring & review",
        description:
          assessment?.mode === "DOUBLE"
            ? "Complete internal scoring, then run the calculation"
            : "Run the stakeholder scoring calculation",
        icon: ClipboardList,
        url: `${base}/scoring`,
        complete: scored,
      },
      {
        title: "Results & matrix",
        description: scored
          ? "Review the latest materiality outcome and history"
          : "Available after the first score run",
        icon: Sparkles,
        url: `${base}/matrix`,
        complete: scored,
      },
    ];
  }, [assessment?.mode, assessment?.status, assessmentId, counts]);

  if (loading)
    return (
      <AppShell
        title="Assessment overview"
        description="Loading your materiality workflow."
      >
        <div className="flex min-h-[420px] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      </AppShell>
    );
  if (!assessment)
    return (
      <AppShell title="Assessment overview" description="Materiality workflow">
        <Card className="max-w-lg">
          <CardHeader>
            <CardTitle>Assessment unavailable</CardTitle>
            <CardDescription>
              {error ?? "This assessment could not be found."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/materiality/assessments")}>
              Back to assessments
            </Button>
          </CardContent>
        </Card>
      </AppShell>
    );

  const progress = Math.max(
    0,
    Math.min(100, assessment.progress_percentage ?? 0),
  );
  const locked =
    assessment.is_locked ||
    ["COMPLETED", "APPROVED"].includes(assessment.status);

  return (
    <AppShell
      title="Assessment overview"
      description="Your guided materiality assessment workflow."
    >
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <Card className="overflow-hidden border-indigo-100 bg-gradient-to-br from-white via-indigo-50/50 to-emerald-50/50 shadow-sm">
          <CardContent className="p-6 sm:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <div className="mb-3 flex flex-wrap gap-2">
                  <Badge className="bg-indigo-600 hover:bg-indigo-600">
                    {assessment.mode === "DOUBLE"
                      ? "Double materiality"
                      : "Single materiality"}
                  </Badge>
                  <Badge variant="outline">
                    {statusLabel(assessment.status)}
                  </Badge>
                  {locked && (
                    <Badge
                      variant="outline"
                      className="border-amber-200 bg-amber-50 text-amber-700"
                    >
                      <Lock className="mr-1 h-3 w-3" />
                      Historical view
                    </Badge>
                  )}
                </div>
                <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
                  {assessment.name}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {locked
                    ? "This completed assessment remains available for review. Its workflow data and score history are read-only."
                    : "Work through the stages below. Each stage keeps the context needed for the next decision."}
                </p>
              </div>
              <div className="w-full max-w-sm rounded-xl border border-white/80 bg-white/80 p-4 shadow-sm">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-800">
                    Assessment progress
                  </span>
                  <span className="font-semibold text-indigo-700">
                    {progress}%
                  </span>
                </div>
                <Progress value={progress} className="mt-3 h-2" />
                <p className="mt-2 text-xs text-slate-500">
                  Next: {assessment.current_step ?? "Review results"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Assessment workflow
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            Start with scope, then collect evidence and move into scoring and
            decision-making.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {workflow.map((step, index) => {
            const Icon = step.icon;
            const isCurrent = assessment.current_step
              ?.toLowerCase()
              .includes(step.title.split(" ")[0].toLowerCase());
            return (
              <Card
                key={step.title}
                className={`group flex min-h-[232px] flex-col overflow-hidden border ${isCurrent ? "border-indigo-300 ring-1 ring-indigo-200" : "border-slate-200"}`}
              >
                <CardHeader className="p-5 pb-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Stage {index + 1}
                    </span>
                    {step.complete && (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    )}
                  </div>
                  <div className="mt-3 w-fit rounded-xl bg-slate-100 p-2.5">
                    <Icon className="h-5 w-5 text-slate-700" />
                  </div>
                  <CardTitle className="pt-3 text-base">{step.title}</CardTitle>
                  <CardDescription className="min-h-[40px] text-xs leading-5">
                    {step.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="mt-auto p-5 pt-3">
                  <Button
                    variant={isCurrent ? "default" : "outline"}
                    className={
                      isCurrent
                        ? "w-full bg-indigo-600 hover:bg-indigo-700"
                        : "w-full"
                    }
                    onClick={() => navigate(step.url)}
                  >
                    {locked ? "View" : step.complete ? "Review" : "Continue"}
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
