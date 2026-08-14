import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Loader2,
} from "lucide-react";

import { toast } from "sonner";

import {
  Card,
  CardContent,
} from "@/components/ui/card";

import {
  Button,
} from "@/components/ui/button";

import {
  Progress,
} from "@/components/ui/progress";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import PublicSurveyApi from "@/api/materiality/PublicSurveyApi";

import type {
  PublicSurveyAlreadySubmitted,
  PublicSurveyData,
  PublicSurveyGetResponse,
  PublicSurveyQuestion,
} from "@/types/materiality/survey";


/* ==========================================================
   LOCAL RESPONSE STATE
========================================================== */

interface ResponseState {
  value: number | null;
  comment: string;
}


/* ==========================================================
   GROUPED UI TYPES
========================================================== */

interface GroupedSubtopic {
  name: string;
  questions: PublicSurveyQuestion[];
}

interface GroupedCategory {
  name: string;
  subtopics: GroupedSubtopic[];
}


/* ==========================================================
   TYPE GUARD
========================================================== */

function isAlreadySubmittedResponse(
  result: PublicSurveyGetResponse
): result is PublicSurveyAlreadySubmitted {
  return (
    "submitted" in result &&
    result.submitted === true
  );
}


/* ==========================================================
   COMPONENT
========================================================== */

export default function PublicSurvey() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  /* DATA */
  const [data, setData] = useState<PublicSurveyData | null>(null);
  const [responses, setResponses] = useState<Record<string, ResponseState>>({});

  /* PAGE STATE */
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState<"intro" | "survey">("intro");
  const [categoryIndex, setCategoryIndex] = useState(0);

  /* SAVE STATE */
  const [savingQuestion, setSavingQuestion] = useState<string | null>(null);

  /* SUBMIT STATE */
  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  /* ========================================================
     LOAD PUBLIC SURVEY
  ======================================================== */

  useEffect(() => {
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoadError("Invalid survey link.");
      setLoading(false);
      return;
    }

    const surveyToken = token;

    const loadSurvey = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        const response = await PublicSurveyApi.getSurvey(surveyToken);
        const result = response.data;

        if (isAlreadySubmittedResponse(result)) {
          navigate(`/survey/${surveyToken}/thank-you`, { replace: true });
          return;
        }

        setData(result);

        const initialResponses: Record<string, ResponseState> = {};

        result.questions.forEach((question) => {
          initialResponses[question.id] = {
            value: question.response?.value ?? null,
            comment: question.response?.comment ?? "",
          };
        });

        setResponses(initialResponses);
      } catch (error) {
        console.error("Failed to load public survey:", error);
        setLoadError("This survey is unavailable or the link has expired.");
      } finally {
        setLoading(false);
      }
    };

    void loadSurvey();
  }, [token, navigate]);

  /* ========================================================
     GROUP QUESTIONS: Category -> Subtopic -> Questions
  ======================================================== */

  const categories = useMemo<GroupedCategory[]>(() => {
    if (!data) {
      return [];
    }

    const categoryMap = new Map<
      string,
      { name: string; subtopics: Map<string, GroupedSubtopic> }
    >();

    data.questions.forEach((question) => {
      const categoryKey = question.category_name;

      if (!categoryMap.has(categoryKey)) {
        categoryMap.set(categoryKey, { name: categoryKey, subtopics: new Map() });
      }

      const category = categoryMap.get(categoryKey)!;
      const subtopicKey = question.subtopic_name;

      if (!category.subtopics.has(subtopicKey)) {
        category.subtopics.set(subtopicKey, { name: subtopicKey, questions: [] });
      }

      category.subtopics.get(subtopicKey)!.questions.push(question);
    });

    return Array.from(categoryMap.values()).map((category) => ({
      name: category.name,
      subtopics: Array.from(category.subtopics.values()),
    }));
  }, [data]);

  const allQuestions = useMemo(
    () => categories.flatMap((category) => category.subtopics.flatMap((subtopic) => subtopic.questions)),
    [categories]
  );

  const totalQuestions = allQuestions.length;

  const answeredCount = useMemo(
    () =>
      allQuestions.filter(
        (question) => responses[question.id]?.value !== null && responses[question.id]?.value !== undefined
      ).length,
    [allQuestions, responses]
  );

  const requiredQuestions = useMemo(
    () => allQuestions.filter((question) => question.is_required),
    [allQuestions]
  );

  const answeredRequiredCount = requiredQuestions.filter(
    (question) => responses[question.id]?.value !== null && responses[question.id]?.value !== undefined
  ).length;

  const allRequiredAnswered = answeredRequiredCount === requiredQuestions.length;

  const progress = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const currentCategory = categories[categoryIndex] ?? null;
  const isLastPage = categoryIndex === categories.length - 1;

  /* ========================================================
     UPDATE LOCAL RESPONSE
  ======================================================== */

  const updateResponse = (questionId: string, patch: Partial<ResponseState>) => {
    setResponses((previous) => ({
      ...previous,
      [questionId]: {
        value: previous[questionId]?.value ?? null,
        comment: previous[questionId]?.comment ?? "",
        ...patch,
      },
    }));
  };

  /* ========================================================
     SAVE ANSWER
  ======================================================== */

  const handleAnswer = async (question: PublicSurveyQuestion, value: number) => {
    if (!token) {
      return;
    }

    const surveyToken = token;
    const previousResponse = responses[question.id] ?? { value: null, comment: "" };

    updateResponse(question.id, { value });

    try {
      setSavingQuestion(question.id);

      await PublicSurveyApi.saveResponse(surveyToken, {
        question: question.id,
        value,
        comment: previousResponse.comment,
      });
    } catch (error) {
      console.error("Failed to save survey answer:", error);
      updateResponse(question.id, { value: previousResponse.value });
      toast.error("Unable to save your answer.", {
        description: "Please try selecting the answer again.",
      });
    } finally {
      setSavingQuestion(null);
    }
  };

  /* ========================================================
     SUBMIT
  ======================================================== */

  const handleSubmit = async () => {
    if (!token) {
      return;
    }

    const surveyToken = token;

    try {
      setSubmitting(true);

      await PublicSurveyApi.submitSurvey(surveyToken);

      setSubmitOpen(false);
      toast.success("Survey submitted successfully.");
      navigate(`/survey/${surveyToken}/thank-you`, { replace: true });
    } catch (error: unknown) {
      console.error("Failed to submit survey:", error);

      const responseData = (
        error as {
          response?: { data?: { message?: string; missing_question_ids?: string[] } };
        }
      )?.response?.data;

      if (responseData?.missing_question_ids?.length) {
        toast.error("Some questions are unanswered.", {
          description: "Please review the highlighted sections before submitting.",
        });
      } else {
        toast.error(responseData?.message ?? "Unable to submit your survey.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  /* ========================================================
     INVALID TOKEN / LOADING / ERROR
  ======================================================== */

  if (!token) {
    return <PublicError title="Invalid Survey Link" message="The survey link is missing or invalid." />;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white px-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-[#4A3FD6]" />
          <p className="text-sm text-slate-500">Loading survey...</p>
        </div>
      </div>
    );
  }

  if (loadError || !data) {
    return <PublicError title="Survey unavailable" message={loadError ?? "This survey is unavailable."} />;
  }

  return (
    <div className="min-h-screen bg-white">
      {/* HEADER */}
      <header className="sticky top-0 z-20 border-b border-slate-100 bg-white">
        <div className="mx-auto max-w-xl px-4 py-3 sm:px-6">
          <p className="truncate text-sm font-semibold text-[#22243A]">{data.survey.title}</p>

          {step === "survey" && (
            <Progress value={progress} className="mt-2 h-1.5" />
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-xl px-4 py-8 sm:px-6">
        {/* INTRO */}
        {step === "intro" && (
          <div className="flex min-h-[70vh] flex-col justify-center space-y-6">
            <div>
              <h1 className="text-2xl font-semibold leading-tight text-[#22243A] sm:text-3xl">
                {data.survey.title}
              </h1>

              {data.survey.intro_text && (
                <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">{data.survey.intro_text}</p>
              )}
            </div>

            <p className="text-sm text-slate-500">
              {totalQuestions} question{totalQuestions === 1 ? "" : "s"} &middot; answers save automatically, so
              you can pick up where you left off.
            </p>

            <Button
              type="button"
              className="h-12 w-full bg-[#4A3FD6] text-white hover:bg-[#3F34C2] sm:w-auto sm:px-8"
              onClick={() => setStep("survey")}
            >
              Start Survey
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        )}

        {/* SURVEY QUESTIONS */}
        {step === "survey" && currentCategory && (
          <div className="space-y-8">
            <h1 className="text-xl font-semibold text-[#22243A] sm:text-2xl">{currentCategory.name}</h1>

            {currentCategory.subtopics.map((subtopic) => (
              <div key={subtopic.name} className="space-y-6">
                <h2 className="text-sm font-semibold text-slate-500">{subtopic.name}</h2>

                {subtopic.questions.map((question) => {
                  const response = responses[question.id] ?? { value: null, comment: "" };
                  const options = question.scale.options;
                  const firstOption = options[0];
                  const lastOption = options[options.length - 1];

                  return (
                    <div key={question.id} className="space-y-3">
                      <p className="text-sm font-medium leading-6 text-[#22243A]">{question.question_text}</p>

                      {question.help_text && (
                        <p className="text-xs leading-5 text-slate-400">{question.help_text}</p>
                      )}

                      {/* SCALE LEGEND */}
                      {firstOption && lastOption && firstOption.id !== lastOption.id && (
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span>{firstOption.label}</span>
                          <span>{lastOption.label}</span>
                        </div>
                      )}

                      {/* NUMBER SCALE */}
                      <div className="flex flex-wrap gap-2">
                        {options.map((option) => {
                          const selected = response.value === option.value;
                          const isSaving = savingQuestion === question.id;

                          return (
                            <button
                              key={option.id}
                              type="button"
                              disabled={isSaving}
                              title={option.label}
                              className={`
                                flex h-11 min-w-[44px] flex-1 basis-[44px] items-center justify-center
                                rounded-lg border text-sm font-medium transition
                                ${
                                  selected
                                    ? "border-[#4A3FD6] bg-[#4A3FD6] text-white"
                                    : "border-slate-200 bg-white text-slate-700 hover:border-[#4A3FD6]"
                                }
                                disabled:cursor-not-allowed disabled:opacity-70
                              `}
                              onClick={() => void handleAnswer(question, option.value)}
                            >
                              {isSaving && selected ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                option.value
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}

            {/* NAVIGATION */}
            <div className="sticky bottom-0 z-10 -mx-4 border-t border-slate-100 bg-white px-4 py-3 sm:static sm:border-0 sm:px-0 sm:py-0">
              <div className="flex items-center justify-between gap-3">
                <Button
                  type="button"
                  variant="outline"
                  disabled={categoryIndex === 0}
                  onClick={() => setCategoryIndex((previous) => Math.max(previous - 1, 0))}
                  className="min-h-[46px] gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>

                {!isLastPage ? (
                  <Button
                    type="button"
                    className="min-h-[46px] gap-2 bg-[#4A3FD6] text-white hover:bg-[#3F34C2]"
                    onClick={() =>
                      setCategoryIndex((previous) => Math.min(previous + 1, categories.length - 1))
                    }
                  >
                    Next
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    type="button"
                    disabled={!allRequiredAnswered}
                    className="min-h-[46px] gap-2 bg-[#4A3FD6] text-white hover:bg-[#3F34C2]"
                    onClick={() => setSubmitOpen(true)}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Submit Survey
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* SUBMIT DIALOG */}
        <Dialog
          open={submitOpen}
          onOpenChange={(open) => {
            if (!open && !submitting) {
              setSubmitOpen(false);
            }
          }}
        >
          <DialogContent className="w-[95vw] max-w-md border-slate-200 bg-white">
            <DialogHeader>
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#F1EFFF] text-[#4A3FD6]">
                <CheckCircle2 className="h-6 w-6" />
              </div>

              <DialogTitle className="pt-2 text-center text-lg text-[#22243A]">Submit your survey?</DialogTitle>

              <DialogDescription className="text-center leading-6">
                Your responses will be submitted and cannot be changed afterwards.
              </DialogDescription>
            </DialogHeader>

            <DialogFooter className="grid grid-cols-2 gap-2">
              <Button type="button" variant="outline" disabled={submitting} onClick={() => setSubmitOpen(false)}>
                Cancel
              </Button>

              <Button
                type="button"
                disabled={submitting || !allRequiredAnswered}
                onClick={() => void handleSubmit()}
                className="bg-[#4A3FD6] text-white hover:bg-[#3F34C2]"
              >
                {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {submitting ? "Submitting..." : "Submit Survey"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}

/* ==========================================================
   ERROR COMPONENT
========================================================== */

function PublicError({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <Card className="w-full max-w-md border-slate-200 shadow-sm">
        <CardContent className="px-6 py-10 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-red-500" />
          <h1 className="mt-4 text-lg font-semibold text-[#22243A]">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
        </CardContent>
      </Card>
    </div>
  );
}