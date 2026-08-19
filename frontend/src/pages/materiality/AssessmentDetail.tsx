import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import {
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  FileText,
  FolderTree,
  Loader2,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  Tag,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import api from "@/services/api";
import SurveyApi from "@/api/materiality/surveyApi";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import type {
  TopicCategory,
  MaterialTopic,
  MaterialSubTopic,
} from "@/types/materiality/materiality";
import type { ReportingPeriod } from "@/types/reporting-period";

/* ============================================================
   TYPES
============================================================ */

interface Assessment {
  reporting_period_details: ReportingPeriod;
  id: string;
  company: string;
  name: string;
  financial_year: string;
  period_start: string;
  period_end: string;

  mode: "SINGLE" | "DOUBLE";
  status: string;

  primary_threshold: string | number;
  secondary_threshold: string | number;

  scale_min: number;
  scale_max: number;

  internal_blend_weight: string | number;
  is_locked: boolean;

  created_by: string | number;
  approved_by: string | number | null;
  approved_at: string | null;
  created_at: string;
}

interface AssessmentTopic {
  id: string;
  assessment: string;
  subtopic: string;

  is_included: boolean;
  display_order: number;

  primary_score: string | number | null;
  secondary_score: string | number | null;

  classification: string;

  is_override: boolean;
  override_reason: string;
  override_by: string | number | null;

  created_at: string;
  updated_at: string;
}

type StatusFilter = "All" | "Active" | "Inactive";

interface VisibleTopic {
  topic: MaterialTopic;
  subTopics: MaterialSubTopic[];
}

interface VisibleCategory {
  category: TopicCategory;
  topics: VisibleTopic[];
}

/* ============================================================
   STATIC CONFIG
============================================================ */

const STATUS_BADGE_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  DRAFT: {
    label: "Draft",
    className: "border-slate-200 bg-slate-50 text-slate-700",
  },
  TOPICS_SELECTED: {
    label: "Topics Selected",
    className: "border-blue-200 bg-blue-50 text-blue-700",
  },
  IN_PROGRESS: {
    label: "In Progress",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  SURVEY_READY: {
    label: "Survey Ready",
    className: "border-indigo-200 bg-indigo-50 text-indigo-700",
  },
  COMPLETED: {
    label: "Completed",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  APPROVED: {
    label: "Approved",
    className: "border-purple-200 bg-purple-50 text-purple-700",
  },
};

const CATEGORY_LABELS: Record<string, string> = {
  E: "Environmental",
  S: "Social",
  G: "Governance",
};

/* Every selected sub-topic produces exactly 2 questions,
   for both SINGLE and DOUBLE materiality. */
const QUESTIONS_PER_SUBTOPIC = 2;

/* question_count × 15 seconds, rounded up to the nearest minute. */
const SECONDS_PER_QUESTION = 15;

/* ============================================================
   COMPONENT
============================================================ */

export default function AssessmentDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  /* ---------------------------- data state ---------------------------- */

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [categories, setCategories] = useState<TopicCategory[]>([]);
  const [topics, setTopics] = useState<MaterialTopic[]>([]);
  const [subTopics, setSubTopics] = useState<MaterialSubTopic[]>([]);

  /* IDs of sub-topics already selected for this assessment. */
  const [selectedSubTopicIds, setSelectedSubTopicIds] = useState<Set<string>>(
    new Set(),
  );

  /* ---------------------------- ui state ---------------------------- */

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");

  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(),
  );
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());

  /* ---------------------------- post-save "generate survey" dialog ---------------------------- */

  /*
   * Shown right after the topic selection is saved successfully, so the
   * user can jump straight into generating the survey without having to
   * find their way to the Survey Manager separately.
   */
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [generatingSurvey, setGeneratingSurvey] = useState(false);

  /* ---------------------------- load data ---------------------------- */

  const loadData = useCallback(async () => {
    if (!id) {
      setError("Assessment ID is missing.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [
        assessmentResponse,
        categoriesResponse,
        topicsResponse,
        subTopicsResponse,
        assessmentTopicsResponse,
      ] = await Promise.all([
        api.get<Assessment>(`/materiality/assessments/${id}/`),
        api.get<TopicCategory[]>("/materiality/topics/categories/"),
        api.get<MaterialTopic[]>("/materiality/topics/"),
        api.get<MaterialSubTopic[]>("/materiality/topics/subtopics/"),
        // Filter AssessmentTopic records by assessment.
        api.get<AssessmentTopic[]>(`/materiality/assessments/${id}/topics/`),
      ]);

      setAssessment(assessmentResponse.data);
      setCategories(categoriesResponse.data);
      setTopics(topicsResponse.data);
      setSubTopics(subTopicsResponse.data);

      const selectedIds = new Set<string>();
      assessmentTopicsResponse.data.forEach((assessmentTopic) => {
        if (assessmentTopic.is_included) {
          selectedIds.add(assessmentTopic.subtopic);
        }
      });
      setSelectedSubTopicIds(selectedIds);
    } catch (err: unknown) {
      console.error("Failed to load assessment:", err);
      setError("Unable to load the assessment.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  /* ---------------------------- lookup maps ---------------------------- */

  const topicsByCategory = useMemo(() => {
    const map = new Map<string, MaterialTopic[]>();
    topics.forEach((topic) => {
      const existing = map.get(topic.category) ?? [];
      existing.push(topic);
      map.set(topic.category, existing);
    });
    return map;
  }, [topics]);

  const subTopicsByTopic = useMemo(() => {
    const map = new Map<string, MaterialSubTopic[]>();
    subTopics.forEach((subTopic) => {
      const existing = map.get(subTopic.topic) ?? [];
      existing.push(subTopic);
      map.set(subTopic.topic, existing);
    });
    return map;
  }, [subTopics]);

  /* ---------------------------- sorting ---------------------------- */

  const sortTopics = (topicList: MaterialTopic[]) =>
    [...topicList].sort(
      (a, b) =>
        a.display_order - b.display_order ||
        String(a.code).localeCompare(String(b.code)) ||
        a.name.localeCompare(b.name),
    );

  const sortSubTopics = (subTopicList: MaterialSubTopic[]) =>
    [...subTopicList].sort(
      (a, b) =>
        a.display_order - b.display_order ||
        a.code.localeCompare(b.code) ||
        a.name.localeCompare(b.name),
    );

  /* ---------------------------- search matching ---------------------------- */

  const subTopicMatchesKeyword = (
    subTopic: MaterialSubTopic,
    keyword: string,
  ) =>
    subTopic.name.toLowerCase().includes(keyword) ||
    subTopic.code.toLowerCase().includes(keyword) ||
    (subTopic.description?.toLowerCase().includes(keyword) ?? false);

  const topicMatchesKeyword = (topic: MaterialTopic, keyword: string) =>
    topic.name.toLowerCase().includes(keyword) ||
    String(topic.code).toLowerCase().includes(keyword) ||
    (topic.description?.toLowerCase().includes(keyword) ?? false);

  const categoryMatchesKeyword = (category: TopicCategory, keyword: string) =>
    category.name.toLowerCase().includes(keyword) ||
    category.code.toLowerCase().includes(keyword);

  /* ---------------------------- visible tree ----------------------------
     Built once here, and reused as-is by the renderers below, so the
     "what matches the search / status filter" logic lives in a single
     place instead of being recomputed (and risking drift) per row.

     Rule: if a topic's own name/code/description matches the keyword,
     all of its sub-topics are shown. Otherwise only the sub-topics that
     individually match are shown. Same idea one level up for categories.
  ------------------------------------------------------------------- */

  const visibleTree = useMemo<VisibleCategory[]>(() => {
    const keyword = search.trim().toLowerCase();

    const matchesStatus = (topic: MaterialTopic) =>
      statusFilter === "All" ||
      (statusFilter === "Active" && topic.is_active) ||
      (statusFilter === "Inactive" && !topic.is_active);

    return categories.reduce<VisibleCategory[]>(
      (visibleCategories, category) => {
        const categorySelfMatches =
          !keyword || categoryMatchesKeyword(category, keyword);

        const visibleTopics = sortTopics(
          topicsByCategory.get(category.id) ?? [],
        )
          .filter(matchesStatus)
          .reduce<VisibleTopic[]>((acc, topic) => {
            const topicSubTopics = sortSubTopics(
              subTopicsByTopic.get(topic.id) ?? [],
            );

            const topicSelfMatches =
              !keyword || topicMatchesKeyword(topic, keyword);

            const matchingSubTopics = keyword
              ? topicSubTopics.filter((subTopic) =>
                  subTopicMatchesKeyword(subTopic, keyword),
                )
              : topicSubTopics;

            const topicVisible =
              categorySelfMatches ||
              topicSelfMatches ||
              matchingSubTopics.length > 0;

            if (!topicVisible) {
              return acc;
            }

            acc.push({
              topic,
              subTopics:
                topicSelfMatches || categorySelfMatches
                  ? topicSubTopics
                  : matchingSubTopics,
            });

            return acc;
          }, []);

        if (categorySelfMatches || visibleTopics.length > 0) {
          visibleCategories.push({ category, topics: visibleTopics });
        }

        return visibleCategories;
      },
      [],
    );
  }, [categories, topicsByCategory, subTopicsByTopic, search, statusFilter]);

  /* ---------------------------- derived counts ---------------------------- */

  const selectedCount = selectedSubTopicIds.size;
  const estimatedQuestions = selectedCount * QUESTIONS_PER_SUBTOPIC;
  const estimatedMinutes = Math.ceil(
    (estimatedQuestions * SECONDS_PER_QUESTION) / 60,
  );

  /* ---------------------------- tree toggles ---------------------------- */

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((previous) => {
      const next = new Set(previous);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const toggleTopic = (topicId: string) => {
    setExpandedTopics((previous) => {
      const next = new Set(previous);
      if (next.has(topicId)) {
        next.delete(topicId);
      } else {
        next.add(topicId);
      }
      return next;
    });
  };

  const toggleSubTopic = (subTopicId: string) => {
    // Approved / locked assessments cannot be modified.
    if (assessment?.is_locked) {
      return;
    }

    setSelectedSubTopicIds((previous) => {
      const next = new Set(previous);
      if (next.has(subTopicId)) {
        next.delete(subTopicId);
      } else {
        next.add(subTopicId);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedCategories(
      new Set(visibleTree.map(({ category }) => category.id)),
    );
    setExpandedTopics(
      new Set(
        visibleTree.flatMap(({ topics: topicList }) =>
          topicList.map(({ topic }) => topic.id),
        ),
      ),
    );
  };

  const collapseAll = () => {
    setExpandedCategories(new Set());
    setExpandedTopics(new Set());
  };

  /* Auto-expand everything that's currently visible while searching. */
  useEffect(() => {
    if (!search.trim()) {
      return;
    }

    setExpandedCategories(
      new Set(visibleTree.map(({ category }) => category.id)),
    );
    setExpandedTopics(
      new Set(
        visibleTree.flatMap(({ topics: topicList }) =>
          topicList.map(({ topic }) => topic.id),
        ),
      ),
    );
  }, [search, visibleTree]);

  /* ---------------------------- save ---------------------------- */

  const handleSaveTopics = async () => {
    if (!id || !assessment || assessment.is_locked) {
      return;
    }

    try {
      setSaving(true);
      setError(null);

      await api.post(`/materiality/assessments/${id}/select-topics/`, {
        subtopic_ids: Array.from(selectedSubTopicIds),
      });

      toast.success("Topics selected successfully.", {
        description: "The selected topics have been saved to this assessment.",
      });

      // Refresh data so the page reflects what was just saved.
      await loadData();

      /*
       * Instead of navigating straight away, offer to generate the
       * survey from the topics that were just saved. The user can
       * still back out and go to the assessment list from the dialog.
       */
      setGenerateDialogOpen(true);
    } catch (err: unknown) {
      console.error("Failed to save topic selection:", err);

      setError("Unable to save topic selection. Please try again.");

      toast.error("Failed to save topics.", {
        description: "Unable to save the topic selection. Please try again.",
      });
    } finally {
      setSaving(false);
    }
  };

  /* ---------------------------- generate survey ---------------------------- */

  const handleGenerateSurvey = async () => {
    if (!id) {
      return;
    }

    try {
      setGeneratingSurvey(true);

      await SurveyApi.generateSurvey(id);

      toast.success("Survey questions generated successfully.", {
        description:
          "Questions were generated from the included assessment topics.",
      });

      setGenerateDialogOpen(false);

      navigate(`/materiality/assessments/${id}/survey`);
    } catch (err: unknown) {
      console.error("Failed to generate survey questions:", err);

      toast.error("Unable to generate survey questions.", {
        description: "Make sure the assessment has included topics.",
      });
    } finally {
      setGeneratingSurvey(false);
    }
  };

  const handleSkipGenerate = () => {
    if (generatingSurvey) {
      return;
    }

    setGenerateDialogOpen(false);
    navigate("/materiality/assessments");
  };

  /* ---------------------------- badges ---------------------------- */

  const renderStatusBadge = (status: string) => {
    const config = STATUS_BADGE_CONFIG[status] ?? {
      label: status,
      className: "border-slate-200 bg-slate-50 text-slate-700",
    };

    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const renderModeBadge = (mode: Assessment["mode"]) => (
    <Badge
      className={
        mode === "DOUBLE"
          ? "border-indigo-200 bg-indigo-50 text-indigo-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700"
      }
    >
      {mode === "DOUBLE" ? "Double Materiality" : "Single Materiality"}
    </Badge>
  );

  const getCategoryLabel = (code: TopicCategory["code"]) =>
    CATEGORY_LABELS[code] ?? "Governance";

  const renderCategoryBadge = (code: TopicCategory["code"]) => (
    <Badge className="border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-50">
      {getCategoryLabel(code)}
    </Badge>
  );

  /* ---------------------------- tree rows ---------------------------- */

  const renderSubTopic = (subTopic: MaterialSubTopic, isLast: boolean) => {
    const selected = selectedSubTopicIds.has(subTopic.id);

    return (
      <div key={subTopic.id} className="relative pb-3 last:pb-0">
        {!isLast && (
          <span className="pointer-events-none absolute -left-5 top-6 bottom-0 w-px bg-slate-200" />
        )}
        <span className="pointer-events-none absolute -left-5 top-6 h-px w-5 bg-slate-200" />

        <div
          className={`flex items-center justify-between gap-4 rounded-lg border px-4 py-3 transition-all ${
            selected
              ? "border-indigo-200 bg-indigo-50/50"
              : "border-slate-100 bg-slate-50/70"
          }`}
        >
          <div className="flex min-w-0 items-center gap-3">
            <Checkbox
              checked={selected}
              disabled={assessment?.is_locked === true}
              onCheckedChange={() => toggleSubTopic(subTopic.id)}
            />

            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-slate-500 shadow-sm">
              <Tag className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-[#4A3FD6]">
                  {subTopic.code}
                </span>
                <span className="truncate text-sm font-medium text-slate-800">
                  {subTopic.name}
                </span>
              </div>

              {subTopic.description && (
                <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                  {subTopic.description}
                </p>
              )}
            </div>
          </div>

          <Badge
            className={
              subTopic.is_active
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-slate-200 bg-slate-100 text-slate-500"
            }
          >
            {subTopic.is_active ? "Active" : "Inactive"}
          </Badge>
        </div>
      </div>
    );
  };

  const renderTopic = (
    { topic, subTopics: children }: VisibleTopic,
    isLast: boolean,
  ) => {
    const expanded = expandedTopics.has(topic.id);

    return (
      <div key={topic.id} className="relative pb-3 last:pb-0">
        {!isLast && (
          <span className="pointer-events-none absolute -left-5 top-6 bottom-0 w-px bg-slate-200" />
        )}
        <span className="pointer-events-none absolute -left-5 top-6 h-px w-5 bg-slate-200" />

        <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-100 bg-white px-4 py-3 transition-colors hover:border-slate-200 hover:bg-slate-50">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => toggleTopic(topic.id)}
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>

            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
              <FolderTree className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-[#4A3FD6]">
                  {topic.code}
                </span>
                <span className="truncate text-sm font-semibold text-slate-800">
                  {topic.name}
                </span>

                {!topic.is_active && (
                  <Badge className="border-slate-200 bg-slate-100 text-slate-500">
                    Inactive
                  </Badge>
                )}
              </div>

              {topic.description && (
                <p className="mt-1 line-clamp-1 text-xs text-slate-500">
                  {topic.description}
                </p>
              )}
            </div>
          </div>

          <div className="shrink-0 text-xs text-slate-500">
            {children.length}{" "}
            {children.length === 1 ? "sub-topic" : "sub-topics"}
          </div>
        </div>

        {expanded && (
          <div className="relative ml-8 mt-3 space-y-0 border-l border-slate-200 pl-6">
            {children.length > 0 ? (
              children.map((subTopic, index) =>
                renderSubTopic(subTopic, index === children.length - 1),
              )
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center">
                <p className="text-sm text-slate-500">
                  No matching sub-topics.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderCategory = (
    { category, topics: categoryTopics }: VisibleCategory,
    isLast: boolean,
  ) => {
    const expanded = expandedCategories.has(category.id);

    return (
      <div key={category.id} className="relative pb-4 last:pb-0">
        {!isLast && (
          <span className="pointer-events-none absolute left-5 top-12 bottom-0 w-px bg-slate-200" />
        )}

        <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="shrink-0"
              onClick={() => toggleCategory(category.id)}
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>

            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <FolderTree className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-900">
                  {category.name}
                </span>
                {renderCategoryBadge(category.code)}
              </div>

              <p className="mt-0.5 text-xs text-slate-500">
                {categoryTopics.length}{" "}
                {categoryTopics.length === 1 ? "topic" : "topics"}
              </p>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="relative ml-8 mt-3 space-y-0 border-l border-slate-200 pl-6">
            {categoryTopics.length > 0 ? (
              categoryTopics.map((visibleTopic, index) =>
                renderTopic(visibleTopic, index === categoryTopics.length - 1),
              )
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-5 py-7 text-center">
                <p className="text-sm font-medium text-slate-600">
                  No topics found
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Try changing your search or status filter.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  /* ---------------------------- loading / error states ---------------------------- */

  if (loading) {
    return (
      <AppShell
        title="Materiality Assessment"
        description="Select the ESG topics and sub-topics for this assessment."
      >
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading assessment...
          </div>
        </div>
      </AppShell>
    );
  }

  if (!assessment) {
    return (
      <AppShell
        title="Materiality Assessment"
        description="Unable to load the requested assessment."
      >
        <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
          <p className="text-sm text-red-600">
            {error ?? "Assessment not found."}
          </p>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void loadData()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>

            <Button
              variant="outline"
              onClick={() => navigate("/materiality/assessments")}
            >
              Back
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  /* ---------------------------- main render ---------------------------- */

  return (
    <AppShell
      title="Materiality Assessment"
      description="Select the ESG sub-topics that will be included in this assessment."
    >
      <div className="space-y-6">
        {/* ASSESSMENT SUMMARY */}
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-semibold text-[#22243A]">
                    {assessment.name}
                  </h1>
                  {renderStatusBadge(assessment.status)}
                  {renderModeBadge(assessment.mode)}
                  {assessment.is_locked && (
                    <Badge className="border-red-200 bg-red-50 text-red-700">
                      Locked
                    </Badge>
                  )}
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-500">
                  <span>
                    Reporting Period:{" "}
                    <strong className="font-medium text-slate-700">
                      {assessment.reporting_period_details?.name ??
                        "Not specified"}
                    </strong>
                  </span>
                </div>
              </div>

              <div className="flex shrink-0 gap-2">
                <Button
                  variant="outline"
                  onClick={() => void loadData()}
                  disabled={saving}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>

                <Button
                  onClick={() => void handleSaveTopics()}
                  disabled={saving || assessment.is_locked}
                >
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Selection
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* LIVE SELECTION SUMMARY */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <Check className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Selected Sub-topics
                  </p>
                  <p className="mt-1 text-2xl font-semibold text-[#22243A]">
                    {selectedCount}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Estimated Questions
                  </p>
                  <p className="mt-1 text-2xl font-semibold text-[#22243A]">
                    {estimatedQuestions}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                  <CircleHelp className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Estimated Survey Time
                  </p>
                  <p className="mt-1 text-2xl font-semibold text-[#22243A]">
                    {estimatedMinutes} {estimatedMinutes === 1 ? "min" : "mins"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {selectedCount > 20 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm font-medium text-amber-800">
              Large topic shortlist
            </p>
            <p className="mt-1 text-sm text-amber-700">
              {selectedCount} sub-topics will produce approximately{" "}
              {estimatedQuestions} questions and an estimated {estimatedMinutes}
              -minute survey. Consider reducing the shortlist.
            </p>
          </div>
        )}

        {/* TOPIC LIBRARY */}
        <Card className="border-slate-200 shadow-sm px-4">
          <CardHeader className="border-b border-slate-100">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FolderTree className="h-5 w-5 text-[#4A3FD6]" />
                  Topic Selection
                </CardTitle>
                <p className="mt-1 text-sm text-slate-500">
                  Select the sub-topics that should be included in this
                  assessment.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button variant="ghost" size="sm" onClick={expandAll}>
                  Expand All
                </Button>
                <Button variant="ghost" size="sm" onClick={collapseAll}>
                  Collapse All
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            {/* TOOLBAR */}
            <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="relative w-full md:max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search topics or sub-topics..."
                  className="pl-9"
                />
              </div>

              <Select
                value={statusFilter}
                onValueChange={(value) =>
                  setStatusFilter(value as StatusFilter)
                }
              >
                <SelectTrigger className="w-full md:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All Status</SelectItem>
                  <SelectItem value="Active">Active</SelectItem>
                  <SelectItem value="Inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* TREE */}
            {visibleTree.length === 0 ? (
              <div className="flex min-h-[280px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 text-center">
                <FolderTree className="h-10 w-10 text-slate-300" />
                <p className="mt-3 text-sm font-medium text-slate-600">
                  No topics found
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Try changing your search or status filter.
                </p>
              </div>
            ) : (
              <div className="space-y-0">
                {visibleTree.map((visibleCategory, index) =>
                  renderCategory(
                    visibleCategory,
                    index === visibleTree.length - 1,
                  ),
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* BOTTOM ACTION */}
        <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
          <Button
            variant="outline"
            onClick={() => navigate("/materiality/assessments")}
            disabled={saving}
          >
            Cancel
          </Button>

          <Button
            onClick={() => void handleSaveTopics()}
            disabled={saving || assessment.is_locked}
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Topic Selection
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ==================================================
          POST-SAVE: GENERATE SURVEY PROMPT

          Fires automatically once the topic selection saves
          successfully — offers to generate the survey right
          away instead of making the user find their own way
          to the Survey Manager afterwards.
      ================================================== */}

      <Dialog
        open={generateDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            handleSkipGenerate();
          }
        }}
      >
        <DialogContent className="max-w-md border-slate-200 bg-white p-0">
          <div className="flex flex-col items-center px-6 pb-2 pt-8 text-center">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-[#F1EFFF] text-[#4A3FD6]">
              <Sparkles className="h-7 w-7" />
            </div>

            <DialogHeader className="items-center">
              <DialogTitle className="text-lg font-semibold text-[#22243A]">
                Generate your survey
              </DialogTitle>

              <DialogDescription className="max-w-sm text-center text-sm leading-6 text-slate-500">
                Generate survey questions automatically from the topics included
                in this materiality assessment. The generated questions can be
                reviewed and edited afterwards.
              </DialogDescription>
            </DialogHeader>

            <p className="mt-4 text-[11px] text-slate-400">
              The survey and its generated questions will be created by the
              backend.
            </p>
          </div>

          <DialogFooter className="flex-col gap-2 border-t border-slate-100 px-6 py-4 sm:flex-col">
            <Button
              type="button"
              onClick={() => void handleGenerateSurvey()}
              disabled={generatingSurvey}
              className="w-full bg-[#4A3FD6] text-white hover:bg-[#3F34C2]"
            >
              {generatingSurvey ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              {generatingSurvey
                ? "Generating Questions..."
                : "Generate Questions"}
            </Button>

            <Button
              type="button"
              variant="ghost"
              disabled={generatingSurvey}
              onClick={handleSkipGenerate}
              className="w-full text-slate-500"
            >
              Not Now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
