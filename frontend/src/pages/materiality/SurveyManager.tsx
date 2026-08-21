import { useCallback, useEffect, useState } from "react";

import { useParams } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import SurveyApi from "@/api/materiality/surveyApi";

import type {
  Survey,
  SurveyFormData,
  SurveyQuestion,
  SurveyDimension,
} from "@/types/materiality/survey";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";

import { Badge } from "@/components/ui/badge";

import { Input } from "@/components/ui/input";

import { Label } from "@/components/ui/label";

import { Textarea } from "@/components/ui/textarea";

import { Checkbox } from "@/components/ui/checkbox";

import { Separator } from "@/components/ui/separator";

import { Tabs, TabsContent } from "@/components/ui/tabs";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  Pencil,
  Sparkles,
} from "lucide-react";

import { toast } from "sonner";

/* ==========================================================
   LABELS
========================================================== */

const DIMENSION_LABELS: Record<SurveyDimension, string> = {
  IMPACT: "Impact",

  STAKEHOLDER_IMPORTANCE: "Stakeholder Importance",

  FINANCIAL: "Financial",
};

/* ==========================================================
   COMPONENT
========================================================== */

export default function SurveyManager() {
  const { id } = useParams<{
    id: string;
  }>();

  /* ========================================================
     SURVEY
  ======================================================== */

  const [survey, setSurvey] = useState<Survey | null>(null);
  const [surveyLoading, setSurveyLoading] = useState(true);
  const [savingSurvey, setSavingSurvey] = useState(false);

  /* ========================================================
     QUESTIONS
  ======================================================== */

  const [questions, setQuestions] = useState<SurveyQuestion[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);

  /* ========================================================
     GENERATION
  ======================================================== */

  const [generating, setGenerating] = useState(false);

  /* ========================================================
     QUESTION EDIT DIALOG
  ======================================================== */

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<SurveyQuestion | null>(
    null,
  );
  const [editingQuestionSaving, setEditingQuestionSaving] = useState(false);

  /* ========================================================
     QUESTION EDIT FORM
  ======================================================== */

  const [questionForm, setQuestionForm] = useState({
    question_text: "",
    help_text: "",
    display_order: "0",
    is_required: true,
  });

  /* ========================================================
     SURVEY SETTINGS FORM
  ======================================================== */

  const [surveyForm, setSurveyForm] = useState<SurveyFormData>({
    title: "",
    intro_text: "",
    closing_text: "",
    opens_at: null,
    closes_at: null,
  });

  /* ========================================================
     ACTIVE TAB
  ======================================================== */

  const [activeTab, setActiveTab] = useState("overview");

  /* ========================================================
     ERROR
  ======================================================== */

  const [error, setError] = useState<string | null>(null);

  /* ========================================================
     LOAD SURVEY
  ======================================================== */

  const loadSurvey = useCallback(async () => {
    if (!id) return;

    try {
      setSurveyLoading(true);
      setError(null);

      const response = await SurveyApi.getSurvey(id);
      const data = response.data;

      setSurvey(data);

      setSurveyForm({
        title: data.title,
        intro_text: data.intro_text ?? "",
        closing_text: data.closing_text ?? "",
        opens_at: data.opens_at,
        closes_at: data.closes_at,
      });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;

      if (status === 404) {
        setSurvey(null);
        setSurveyForm({
          title: "",
          intro_text: "",
          closing_text: "",
          opens_at: null,
          closes_at: null,
        });
        return;
      }

      console.error("Failed to load survey:", err);
      setError("Unable to load survey configuration.");
    } finally {
      setSurveyLoading(false);
    }
  }, [id]);

  /* ========================================================
     LOAD QUESTIONS
  ======================================================== */

  const loadQuestions = useCallback(async () => {
    if (!id || !survey) {
      setQuestions([]);
      return;
    }

    try {
      setQuestionsLoading(true);

      const response = await SurveyApi.getQuestions(id);
      setQuestions(response.data);
    } catch (err: unknown) {
      console.error("Failed to load survey questions:", err);
      setQuestions([]);
      toast.error("Unable to load survey questions.");
    } finally {
      setQuestionsLoading(false);
    }
  }, [id, survey]);

 useEffect(() => {
  const load = async () => {
    await loadSurvey();
  };

  void load();
}, [loadSurvey]);

useEffect(() => {
  const load = async () => {
    if (!survey) {
      setQuestions([]);
      return;
    }

    await loadQuestions();
  };

  void load();
}, [survey, loadQuestions]);

  /* ========================================================
     SURVEY FIELD UPDATE
  ======================================================== */

  const updateSurveyField = <K extends keyof SurveyFormData>(
    field: K,
    value: SurveyFormData[K],
  ) => {
    setSurveyForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  /* ========================================================
     QUESTION EDIT OPEN
  ======================================================== */

  const handleOpenQuestionEdit = (question: SurveyQuestion) => {
    setEditingQuestion(question);

    setQuestionForm({
      question_text: question.question_text,
      help_text: question.help_text ?? "",
      display_order: String(question.display_order),
      is_required: question.is_required,
    });

    setEditDialogOpen(true);
  };

  /* ========================================================
     DERIVED VALUES
  ======================================================== */

  const questionCount = questions.length;
  const estimatedMinutes = Math.ceil((questionCount * 15) / 60);
  const isLargeSurvey = questionCount > 40;

  /* ========================================================
     MISSING ASSESSMENT ID
  ======================================================== */

  if (!id) {
    return (
      <AppShell
        title="Survey & Responses"
        description="Configure the stakeholder materiality survey."
      >
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          Assessment ID is missing.
        </div>
      </AppShell>
    );
  }

  /* ========================================================
     GENERATE QUESTIONS
  ======================================================== */

  const handleGenerateQuestions = async () => {
    if (!id) return;

    try {
      setGenerating(true);
      setError(null);

      await SurveyApi.generateSurvey(id);

      toast.success("Survey questions generated successfully.", {
        description:
          "Questions were generated from the included assessment topics.",
      });

      await loadSurvey();

      setActiveTab("questions");
    } catch (err: unknown) {
      console.error("Failed to generate survey questions:", err);

      toast.error("Unable to generate survey questions.", {
        description: "Make sure the assessment has included topics.",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleSurveyLifecycle = async (next: "open" | "close") => {
    if (!id || !survey) return;
    try {
      setSavingSurvey(true);
      const response =
        next === "open"
          ? await SurveyApi.openSurvey(id)
          : await SurveyApi.closeSurvey(id);
      setSurvey(response.data);
      toast.success(
        next === "open"
          ? "Survey is now open for responses."
          : "Survey has been closed.",
      );
    } catch (err) {
      console.error("Failed to update survey lifecycle:", err);
      toast.error("Unable to update survey status.");
    } finally {
      setSavingSurvey(false);
    }
  };

  /* ========================================================
     SAVE SURVEY SETTINGS
  ======================================================== */

  const handleSaveSurvey = async () => {
    if (!id || !survey) return;

    if (!surveyForm.title.trim()) {
      toast.error("Survey title is required.");
      return;
    }

    if (
      surveyForm.opens_at &&
      surveyForm.closes_at &&
      surveyForm.opens_at >= surveyForm.closes_at
    ) {
      toast.error("Closing time must be greater than opening time.");
      return;
    }

    try {
      setSavingSurvey(true);

      const response = await SurveyApi.updateSurvey(id, {
        title: surveyForm.title.trim(),
        intro_text: surveyForm.intro_text.trim(),
        closing_text: surveyForm.closing_text.trim(),
        opens_at: surveyForm.opens_at,
        closes_at: surveyForm.closes_at,
      });

      setSurvey(response.data);

      toast.success("Survey settings saved successfully.");
    } catch (err: unknown) {
      console.error("Failed to update survey settings:", err);
      toast.error("Unable to save survey settings.");
    } finally {
      setSavingSurvey(false);
    }
  };

  /* ========================================================
     SAVE QUESTION EDIT
  ======================================================== */

  const handleSaveQuestion = async () => {
    if (!id || !editingQuestion) return;

    if (!questionForm.question_text.trim()) {
      toast.error("Question text is required.");
      return;
    }

    const displayOrder = Number(questionForm.display_order);

    if (!Number.isInteger(displayOrder) || displayOrder < 0) {
      toast.error("Display order must be a valid non-negative number.");
      return;
    }

    try {
      setEditingQuestionSaving(true);

      await SurveyApi.updateQuestion(id, editingQuestion.id, {
        question_text: questionForm.question_text.trim(),
        help_text: questionForm.help_text.trim(),
        display_order: displayOrder,
        is_required: questionForm.is_required,
      });

      toast.success("Question updated successfully.");

      setEditDialogOpen(false);
      setEditingQuestion(null);

      await loadQuestions();
    } catch (err: unknown) {
      console.error("Failed to update question:", err);
      toast.error("Unable to update question.");
    } finally {
      setEditingQuestionSaving(false);
    }
  };

  /* ========================================================
     LOADING
  ======================================================== */

  if (surveyLoading) {
    return (
      <AppShell
        title="Survey & Responses"
        description="Configure the stakeholder materiality survey."
      >
        <div className="flex min-h-[420px] items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-[#4A3FD6]" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Survey & Responses"
      description="Configure, generate and review the stakeholder materiality survey."
    >
      <div className="space-y-5">
        {/* ==================================================
            HEADER — title, status, and the one primary action
            all live in a single compact row so nothing below
            has to repeat them.
        ================================================== */}

        <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#22243A]">
              Survey design
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Prepare the survey from the included materiality assessment
              topics.
            </p>
          </div>

          {survey && (
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className={`
                  px-3 py-1
                  ${
                    survey.status === "OPEN"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                      : survey.status === "READY"
                        ? "border-blue-200 bg-blue-50 text-blue-700"
                        : survey.status === "CLOSED"
                          ? "border-slate-200 bg-slate-100 text-slate-600"
                          : "border-amber-200 bg-amber-50 text-amber-700"
                  }
                `}
              >
                {survey.status}
              </Badge>

              <Badge variant="outline" className="px-3 py-1">
                {questionCount} question{questionCount === 1 ? "" : "s"} · ~
                {estimatedMinutes} min
              </Badge>

              {survey.status !== "OPEN" && survey.status !== "CLOSED" && (
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void handleSurveyLifecycle("open")}
                  disabled={savingSurvey}
                >
                  Open survey
                </Button>
              )}
              {survey.status === "OPEN" && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void handleSurveyLifecycle("close")}
                  disabled={savingSurvey}
                >
                  Close survey
                </Button>
              )}
            </div>
          )}
        </div>

        {/* ==================================================
            ERROR
        ================================================== */}

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* ==================================================
            BEFORE GENERATION
        ================================================== */}

        {!survey ? (
          <Card className="border-[#DDD8FF] bg-[#FBFAFF] shadow-sm">
            <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-[#F1EFFF] text-[#4A3FD6]">
                <Sparkles className="h-7 w-7" />
              </div>

              <h2 className="text-lg font-semibold text-[#22243A]">
                Generate your survey
              </h2>

              <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                Generate survey questions automatically from the topics included
                in this materiality assessment. The generated questions can be
                reviewed and edited afterwards.
              </p>

              <Button
                type="button"
                onClick={handleGenerateQuestions}
                disabled={generating}
                className="mt-6 bg-[#4A3FD6] px-6 text-white hover:bg-[#3F34C2]"
              >
                {generating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="mr-2 h-4 w-4" />
                )}
                {generating ? "Generating Questions..." : "Generate Questions"}
              </Button>

              <p className="mt-4 text-[11px] text-slate-400">
                The survey and its generated questions will be created by the
                backend.
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* =================================================
                LARGE SURVEY WARNING
            ================================================= */}

            {isLargeSurvey && (
              <Card className="border-amber-200 bg-amber-50 shadow-none">
                <CardContent className="flex items-start gap-3 px-5 py-3">
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                  <div>
                    <p className="text-sm font-semibold text-amber-800">
                      Survey may be too long
                    </p>
                    <p className="mt-1 text-xs leading-5 text-amber-700">
                      {questionCount} questions are currently configured, with
                      an estimated completion time of {estimatedMinutes}{" "}
                      minutes. Consider reducing the topic shortlist if the
                      survey is too long.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* =================================================
                TABS
            ================================================= */}

            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="flex w-full flex-col items-stretch space-y-4"
            >
              <div
                className="
    flex
    w-fit
    items-center
    gap-1
    rounded-lg
    border
    border-slate-200
    bg-white
    p-1
  "
              >
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setActiveTab("overview")}
                  className={`
      rounded-md
      px-5
      py-2
      text-sm
      font-medium
      ${
        activeTab === "overview"
          ? "bg-[#F1EFFF] text-[#4A3FD6] hover:bg-[#F1EFFF] hover:text-[#4A3FD6]"
          : "text-slate-600 hover:bg-slate-50"
      }
    `}
                >
                  Survey Settings
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setActiveTab("questions")}
                  className={`
      rounded-md
      px-5
      py-2
      text-sm
      font-medium
      ${
        activeTab === "questions"
          ? "bg-[#F1EFFF] text-[#4A3FD6] hover:bg-[#F1EFFF] hover:text-[#4A3FD6]"
          : "text-slate-600 hover:bg-slate-50"
      }
    `}
                >
                  Generated Questions
                </Button>
              </div>

              {/* ==============================================
                  SETTINGS — one card, fields arranged in a
                  two-column grid so the whole form fits without
                  the long single-column scroll.
              ============================================== */}

              <TabsContent value="overview" className="space-y-4">
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="px-6 py-4">
                    <CardTitle className="text-base font-semibold text-[#22243A]">
                      Survey Settings
                    </CardTitle>
                    <CardDescription>
                      Customize the content and availability of the generated
                      survey.
                    </CardDescription>
                  </CardHeader>

                  <Separator />

                  <CardContent className="space-y-4 px-6 py-5">
                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="space-y-2">
                        <Label>
                          Survey Title
                          <span className="ml-1 text-red-500">*</span>
                        </Label>
                        <Input
                          value={surveyForm.title}
                          disabled={savingSurvey}
                          onChange={(event) =>
                            updateSurveyField("title", event.target.value)
                          }
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Opens At</Label>
                          <Input
                            type="datetime-local"
                            value={
                              surveyForm.opens_at
                                ? surveyForm.opens_at.slice(0, 16)
                                : ""
                            }
                            disabled={savingSurvey}
                            onChange={(event) =>
                              updateSurveyField(
                                "opens_at",
                                event.target.value ? event.target.value : null,
                              )
                            }
                          />
                        </div>

                        <div className="space-y-2">
                          <Label>Closes At</Label>
                          <Input
                            type="datetime-local"
                            value={
                              surveyForm.closes_at
                                ? surveyForm.closes_at.slice(0, 16)
                                : ""
                            }
                            disabled={savingSurvey}
                            onChange={(event) =>
                              updateSurveyField(
                                "closes_at",
                                event.target.value ? event.target.value : null,
                              )
                            }
                          />
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Introduction</Label>
                        <Textarea
                          value={surveyForm.intro_text}
                          disabled={savingSurvey}
                          rows={4}
                          placeholder="Explain the purpose of this survey..."
                          onChange={(event) =>
                            updateSurveyField("intro_text", event.target.value)
                          }
                          className="resize-none"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Closing Message</Label>
                        <Textarea
                          value={surveyForm.closing_text}
                          disabled={savingSurvey}
                          rows={4}
                          placeholder="Thank stakeholders after completing the survey..."
                          onChange={(event) =>
                            updateSurveyField(
                              "closing_text",
                              event.target.value,
                            )
                          }
                          className="resize-none"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <Button
                        type="button"
                        onClick={handleSaveSurvey}
                        disabled={savingSurvey}
                        className="bg-[#4A3FD6] text-white hover:bg-[#3F34C2]"
                      >
                        {savingSurvey ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                        )}
                        Save Settings
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* ==============================================
                  GENERATED QUESTIONS
              ============================================== */}

              <TabsContent value="questions" className="space-y-4">
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="px-6 py-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <CardTitle className="text-base font-semibold text-[#22243A]">
                          Generated Questions
                        </CardTitle>
                        <CardDescription>
                          Review and edit the generated question wording before
                          the survey is distributed.
                        </CardDescription>
                      </div>

                      <Badge variant="outline" className="w-fit">
                        {questionCount} questions
                      </Badge>
                    </div>
                  </CardHeader>

                  <Separator />

                  <CardContent className="p-0">
                    {questionsLoading ? (
                      <div className="flex min-h-[320px] items-center justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-[#4A3FD6]" />
                      </div>
                    ) : questions.length === 0 ? (
                      <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
                        <FileText className="mb-4 h-7 w-7 text-[#4A3FD6]" />
                        <p className="text-sm font-semibold text-[#22243A]">
                          No generated questions
                        </p>
                        <p className="mt-1 max-w-md text-xs leading-5 text-slate-500">
                          Generate questions from the included assessment topics
                          to begin building the survey.
                        </p>
                        <Button
                          type="button"
                          onClick={handleGenerateQuestions}
                          disabled={generating}
                          className="mt-5 bg-[#4A3FD6] hover:bg-[#3F34C2]"
                        >
                          Generate Questions
                        </Button>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-4 p-6 xl:grid-cols-2">
                        {questions.map((question) => (
                          <Card
                            key={question.id}
                            className="group relative border-slate-200 shadow-none transition-colors hover:border-[#DDD8FF] hover:bg-[#FBFAFF]"
                          >
                            <CardContent className="space-y-3 p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex flex-wrap items-center gap-1.5">
                                  <Badge
                                    variant="outline"
                                    className="border-[#DDD8FF] bg-[#F7F5FF] text-[#4A3FD6]"
                                  >
                                    {DIMENSION_LABELS[question.dimension]}
                                  </Badge>

                                  {question.is_required && (
                                    <Badge
                                      variant="outline"
                                      className="border-emerald-200 bg-emerald-50 text-emerald-700"
                                    >
                                      Required
                                    </Badge>
                                  )}

                                  <Badge variant="outline">
                                    Order {question.display_order}
                                  </Badge>
                                </div>

                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 shrink-0 text-slate-400 hover:bg-[#F1EFFF] hover:text-[#4A3FD6]"
                                        onClick={() =>
                                          handleOpenQuestionEdit(question)
                                        }
                                      >
                                        <Pencil className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent
                                      side="top"
                                      className="text-xs"
                                    >
                                      Edit question
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </div>

                              <p className="text-sm font-medium leading-6 text-[#22243A]">
                                {question.question_text}
                              </p>

                              {question.help_text && (
                                <p className="text-xs leading-5 text-slate-500">
                                  {question.help_text}
                                </p>
                              )}

                              <Separator />

                              <div className="flex flex-col gap-1 text-[11px] text-slate-400">
                                <span
                                  className="truncate"
                                  title={question.assessment_topic_name}
                                >
                                  Topic: {question.assessment_topic_name}
                                </span>

                                <span
                                  className="truncate"
                                  title={question.scale_name}
                                >
                                  Scale: {question.scale_name}
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </>
        )}

        {/* ==================================================
            EDIT QUESTION DIALOG
        ================================================== */}
        <Dialog
          open={editDialogOpen}
          onOpenChange={(open) => {
            if (!open && !editingQuestionSaving) {
              setEditDialogOpen(false);
              setEditingQuestion(null);
            }
          }}
        >
          <DialogContent
            className="
      w-[95vw]
      max-w-3xl
      p-0
      overflow-hidden
      border-slate-200
      bg-white
    "
          >
            {/* Header */}
            <DialogHeader
              className="
        border-b
        border-slate-200
        px-6
        py-5
      "
            >
              <DialogTitle className="text-lg font-semibold text-[#22243A]">
                Edit Survey Question
              </DialogTitle>

              <DialogDescription>
                Refine the automatically generated wording before the survey is
                distributed.
              </DialogDescription>
            </DialogHeader>

            {/* SCROLLABLE CONTENT */}
            <div
              className="
        h-[60vh]
        overflow-y-scroll
        px-6
        py-5
        scrollbar-thin
        scrollbar-thumb-slate-300
        scrollbar-track-slate-100
      "
            >
              {editingQuestion && (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className="
                border-[#DDD8FF]
                bg-[#F7F5FF]
                text-[#4A3FD6]
              "
                    >
                      {DIMENSION_LABELS[editingQuestion.dimension]}
                    </Badge>

                    {editingQuestion.is_required && (
                      <Badge
                        variant="outline"
                        className="
                  border-emerald-200
                  bg-emerald-50
                  text-emerald-700
                "
                      >
                        Required
                      </Badge>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>
                      Question Text
                      <span className="ml-1 text-red-500">*</span>
                    </Label>

                    <Textarea
                      value={questionForm.question_text}
                      disabled={editingQuestionSaving}
                      rows={6}
                      onChange={(event) =>
                        setQuestionForm((previous) => ({
                          ...previous,
                          question_text: event.target.value,
                        }))
                      }
                      className="resize-none"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Help Text</Label>

                    <Textarea
                      value={questionForm.help_text}
                      disabled={editingQuestionSaving}
                      rows={5}
                      placeholder="Optional guidance for the stakeholder..."
                      onChange={(event) =>
                        setQuestionForm((previous) => ({
                          ...previous,
                          help_text: event.target.value,
                        }))
                      }
                      className="resize-none"
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Display Order</Label>

                      <Input
                        type="number"
                        min={0}
                        value={questionForm.display_order}
                        disabled={editingQuestionSaving}
                        onChange={(event) =>
                          setQuestionForm((previous) => ({
                            ...previous,
                            display_order: event.target.value,
                          }))
                        }
                      />
                    </div>

                    <div
                      className="
                flex
                items-center
                gap-3
                rounded-lg
                border
                border-slate-200
                bg-slate-50
                px-4
                py-3
              "
                    >
                      <Checkbox
                        checked={questionForm.is_required}
                        disabled={editingQuestionSaving}
                        onCheckedChange={(checked) =>
                          setQuestionForm((previous) => ({
                            ...previous,
                            is_required: checked === true,
                          }))
                        }
                      />

                      <div>
                        <p className="text-sm font-medium text-slate-800">
                          Required Question
                        </p>

                        <p className="mt-0.5 text-xs text-slate-500">
                          Stakeholders must answer this question.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div
                    className="
              grid
              gap-4
              rounded-lg
              border
              border-slate-200
              bg-slate-50
              p-4
              md:grid-cols-3
            "
                  >
                    <div>
                      <p className="text-xs font-medium text-slate-600">
                        Dimension
                      </p>

                      <p className="mt-1 text-sm font-semibold text-slate-800">
                        {DIMENSION_LABELS[editingQuestion.dimension]}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-600">
                        Assessment Topic
                      </p>

                      <p
                        className="
                  mt-1
                  truncate
                  text-xs
                  text-slate-500
                "
                      >
                        {editingQuestion.assessment_topic_name ??
                          editingQuestion.assessment_topic}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-600">
                        Scale
                      </p>

                      <p
                        className="
                  mt-1
                  truncate
                  text-xs
                  text-slate-500
                "
                      >
                        {editingQuestion.scale_name ?? editingQuestion.scale}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <DialogFooter
              className="
        border-t
        border-slate-100
        bg-white
        px-6
        py-4
      "
            >
              <Button
                type="button"
                variant="outline"
                disabled={editingQuestionSaving}
                onClick={() => {
                  setEditDialogOpen(false);
                  setEditingQuestion(null);
                }}
              >
                Cancel
              </Button>

              <Button
                type="button"
                disabled={editingQuestionSaving || !editingQuestion}
                onClick={handleSaveQuestion}
                className="
          bg-[#4A3FD6]
          text-white
          hover:bg-[#3F34C2]
        "
              >
                {editingQuestionSaving ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                )}
                Save Changes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
