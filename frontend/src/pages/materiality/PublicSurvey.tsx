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
  Check,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  Save,
} from "lucide-react";

import {
  toast,
} from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  Button,
} from "@/components/ui/button";

import {
  Badge,
} from "@/components/ui/badge";

import {
  Progress,
} from "@/components/ui/progress";

import {
  Separator,
} from "@/components/ui/separator";

import {
  Textarea,
} from "@/components/ui/textarea";

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
  PublicSurveyData,
  PublicSurveyQuestion,
} from "@/types/materiality/survey";


const DIMENSION_LABELS = {
  IMPACT: "Impact",
  STAKEHOLDER_IMPORTANCE:
    "Stakeholder Importance",
  FINANCIAL: "Financial",
};


interface ResponseState {
  value: number | null;
  comment: string;
}


export default function PublicSurvey() {

  const { token } =
    useParams<{
      token: string;
    }>();

  const navigate =
    useNavigate();


  const [
    data,
    setData,
  ] = useState<PublicSurveyData | null>(
    null
  );


  const [
    responses,
    setResponses,
  ] = useState<
    Record<string, ResponseState>
  >({});


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    loadError,
    setLoadError,
  ] = useState<string | null>(
    null
  );


  const [
    step,
    setStep,
  ] = useState<
    "intro" | "survey" | "review"
  >("intro");


  const [
    categoryIndex,
    setCategoryIndex,
  ] = useState(0);


  const [
    savingQuestion,
    setSavingQuestion,
  ] = useState<string | null>(
    null
  );


  const [
    savedQuestions,
    setSavedQuestions,
  ] = useState<
    Set<string>
  >(new Set());


  const [
    submitOpen,
    setSubmitOpen,
  ] = useState(false);


  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  /* ========================================================
     LOAD SURVEY
  ======================================================== */

  useEffect(() => {

    if (!token) {
      setLoadError(
        "Invalid survey link."
      );

      setLoading(false);

      return;
    }


    const loadSurvey =
      async () => {

        try {

          setLoading(true);
          setLoadError(null);

          const response =
            await PublicSurveyApi.getSurvey(
              token
            );

          const result =
            response.data;

          setData(result);


          const initialResponses:
            Record<string, ResponseState> =
            {};

          result.responses.forEach(
            (item) => {
              initialResponses[
                item.question
              ] = {
                value:
                  item.value,
                comment:
                  item.comment ?? "",
              };
            }
          );

          setResponses(
            initialResponses
          );

        } catch (error) {

          console.error(
            "Failed to load public survey:",
            error
          );

          setLoadError(
            "This survey is unavailable or the link has expired."
          );

        } finally {

          setLoading(false);

        }
      };


    void loadSurvey();

  }, [token]);


  /* ========================================================
     GROUP QUESTIONS
  ======================================================== */

  const categories =
    useMemo(() => {

      if (!data) {
        return [];
      }

      const categoryMap =
        new Map<
          string,
          {
            id: string;
            name: string;
            subtopics: Map<
              string,
              {
                id: string;
                name: string;
                questions:
                  PublicSurveyQuestion[];
              }
            >;
          }
        >();

      data.questions.forEach(
        (question) => {

          if (
            !categoryMap.has(
              question.category_id
            )
          ) {
            categoryMap.set(
              question.category_id,
              {
                id:
                  question.category_id,
                name:
                  question.category_name,
                subtopics:
                  new Map(),
              }
            );
          }


          const category =
            categoryMap.get(
              question.category_id
            )!;


          if (
            !category.subtopics.has(
              question.subtopic_id
            )
          ) {
            category.subtopics.set(
              question.subtopic_id,
              {
                id:
                  question.subtopic_id,
                name:
                  question.subtopic_name,
                questions: [],
              }
            );
          }


          category.subtopics
            .get(
              question.subtopic_id
            )!
            .questions.push(
              question
            );

        }
      );


      return Array.from(
        categoryMap.values()
      ).map(
        (category) => ({
          id:
            category.id,
          name:
            category.name,
          subtopics:
            Array.from(
              category.subtopics.values()
            ),
        })
      );

    }, [data]);


  const allQuestions =
    useMemo(
      () =>
        categories.flatMap(
          (category) =>
            category.subtopics.flatMap(
              (subtopic) =>
                subtopic.questions
            )
        ),
      [categories]
    );


  const answeredCount =
    allQuestions.filter(
      (question) =>
        responses[
          question.id
        ]?.value !== null &&
        responses[
          question.id
        ]?.value !== undefined
    ).length;


  const totalQuestions =
    allQuestions.length;


  const progress =
    totalQuestions > 0
      ? Math.round(
          (answeredCount /
            totalQuestions) *
            100
        )
      : 0;


  const estimatedMinutes =
    Math.ceil(
      (totalQuestions * 15) /
        60
    );


  const currentCategory =
    categories[
      categoryIndex
    ];


  /* ========================================================
     RESPONSE UPDATE
  ======================================================== */

  const updateResponse =
    (
      questionId: string,
      patch: Partial<ResponseState>
    ) => {

      setResponses(
        (previous) => ({
          ...previous,

          [questionId]: {
            value:
              previous[
                questionId
              ]?.value ??
              null,

            comment:
              previous[
                questionId
              ]?.comment ??
              "",

            ...patch,
          },
        })
      );

    };


  /* ========================================================
     LOAD / ERROR STATES
  ======================================================== */

  if (loading) {

    return (
      <div
        className="
          flex
          min-h-screen
          items-center
          justify-center
          bg-slate-50
          px-4
        "
      >
        <div className="flex flex-col items-center gap-3">
          <Loader2
            className="
              h-7
              w-7
              animate-spin
              text-[#4A3FD6]
            "
          />

          <p className="text-sm text-slate-500">
            Loading survey...
          </p>
        </div>
      </div>
    );

  }


  if (loadError || !data) {

    return (
      <div
        className="
          flex
          min-h-screen
          items-center
          justify-center
          bg-slate-50
          px-4
        "
      >

        <Card
          className="
            w-full
            max-w-md
            border-slate-200
            shadow-sm
          "
        >

          <CardContent
            className="
              px-6
              py-10
              text-center
            "
          >

            <AlertCircle
              className="
                mx-auto
                h-8
                w-8
                text-red-500
              "
            />

            <h1
              className="
                mt-4
                text-lg
                font-semibold
                text-[#22243A]
              "
            >
              Survey unavailable
            </h1>

            <p
              className="
                mt-2
                text-sm
                leading-6
                text-slate-500
              "
            >
              {loadError}
            </p>

          </CardContent>

        </Card>

      </div>
    );

  }


  return (
    <div
      className="
        min-h-screen
        bg-slate-50
      "
    >

      {/* HEADER */}

      <header
        className="
          sticky
          top-0
          z-20
          border-b
          border-slate-200
          bg-white/95
          backdrop-blur
        "
      >

        <div
          className="
            mx-auto
            flex
            max-w-3xl
            items-center
            justify-between
            px-4
            py-3
            sm:px-6
          "
        >

          <div className="flex min-w-0 items-center gap-3">

            <div
              className="
                flex
                h-9
                w-9
                shrink-0
                items-center
                justify-center
                rounded-lg
                bg-[#F1EFFF]
                text-[#4A3FD6]
              "
            >
              <FileText
                className="h-4 w-4"
              />
            </div>

            <div className="min-w-0">

              <p
                className="
                  truncate
                  text-sm
                  font-semibold
                  text-[#22243A]
                "
              >
                {data.survey.title}
              </p>

              <p
                className="
                  hidden
                  text-[11px]
                  text-slate-500
                  sm:block
                "
              >
                Stakeholder Survey
              </p>

            </div>

          </div>


          {step === "survey" && (
            <div
              className="
                flex
                items-center
                gap-2
                text-xs
                text-slate-500
              "
            >
              <Clock3 className="h-3.5 w-3.5" />

              ~{estimatedMinutes} min
            </div>
          )}

        </div>

      </header>


      <main
        className="
          mx-auto
          w-full
          max-w-3xl
          px-4
          py-6
          pb-10
          sm:px-6
          sm:py-8
        "
      >

        {/* INTRO */}

        {step === "intro" && (

          <Card
            className="
              overflow-hidden
              border-slate-200
              shadow-sm
            "
          >

            <div
              className="
                h-2
                bg-[#4A3FD6]
              "
            />

            <CardHeader
              className="
                px-5
                py-7
                sm:px-8
                sm:py-9
              "
            >

              <Badge
                variant="outline"
                className="
                  w-fit
                  border-[#DDD8FF]
                  bg-[#F7F5FF]
                  text-[#4A3FD6]
                "
              >
                Stakeholder Survey
              </Badge>

              <CardTitle
                className="
                  mt-4
                  text-2xl
                  leading-tight
                  text-[#22243A]
                  sm:text-3xl
                "
              >
                {data.survey.title}
              </CardTitle>

              <CardDescription
                className="
                  mt-3
                  text-sm
                  leading-6
                  sm:text-base
                "
              >
                {data.survey.intro_text}
              </CardDescription>

            </CardHeader>

            <Separator />

            <CardContent
              className="
                space-y-5
                px-5
                py-6
                sm:px-8
                sm:py-8
              "
            >

              <div
                className="
                  grid
                  gap-3
                  sm:grid-cols-2
                "
              >

                <div
                  className="
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    p-4
                  "
                >
                  <div className="flex items-center gap-3">

                    <Clock3
                      className="
                        h-5
                        w-5
                        text-[#4A3FD6]
                      "
                    />

                    <div>
                      <p className="text-xs text-slate-500">
                        Estimated completion
                      </p>

                      <p className="mt-1 text-sm font-semibold text-[#22243A]">
                        {estimatedMinutes} minutes
                      </p>
                    </div>

                  </div>
                </div>


                <div
                  className="
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    p-4
                  "
                >
                  <div className="flex items-center gap-3">

                    <FileText
                      className="
                        h-5
                        w-5
                        text-[#4A3FD6]
                      "
                    />

                    <div>
                      <p className="text-xs text-slate-500">
                        Questions
                      </p>

                      <p className="mt-1 text-sm font-semibold text-[#22243A]">
                        {totalQuestions}
                      </p>
                    </div>

                  </div>
                </div>

              </div>


              <div
                className="
                  rounded-xl
                  border
                  border-[#DDD8FF]
                  bg-[#FBFAFF]
                  px-4
                  py-4
                "
              >

                <div
                  className="
                    flex
                    items-start
                    gap-3
                  "
                >

                  <Save
                    className="
                      mt-0.5
                      h-4
                      w-4
                      shrink-0
                      text-[#4A3FD6]
                    "
                  />

                  <div>

                    <p
                      className="
                        text-sm
                        font-medium
                        text-[#22243A]
                      "
                    >
                      Your answers are saved automatically
                    </p>

                    <p
                      className="
                        mt-1
                        text-xs
                        leading-5
                        text-slate-500
                      "
                    >
                      You can return later using
                      this same survey link.
                    </p>

                  </div>

                </div>

              </div>


              <Button
                type="button"
                className="
                  h-12
                  w-full
                  bg-[#4A3FD6]
                  text-white
                  hover:bg-[#3F34C2]
                  sm:w-auto
                  sm:px-8
                "
                onClick={() =>
                  setStep("survey")
                }
              >
                Start Survey

                <ArrowRight
                  className="
                    ml-2
                    h-4
                    w-4
                  "
                />
              </Button>

            </CardContent>

          </Card>
        )}
        {step === "survey" &&
          currentCategory && (

          <div className="space-y-5">

            {/* CATEGORY PROGRESS */}

            <Card
              className="
                border-slate-200
                shadow-sm
              "
            >

              <CardContent
                className="
                  px-5
                  py-5
                  sm:px-6
                "
              >

                <div
                  className="
                    flex
                    items-start
                    justify-between
                    gap-4
                  "
                >

                  <div>

                    <p
                      className="
                        text-xs
                        font-medium
                        uppercase
                        tracking-wide
                        text-[#4A3FD6]
                      "
                    >
                      Page{" "}
                      {categoryIndex + 1}{" "}
                      of{" "}
                      {categories.length}
                    </p>

                    <h1
                      className="
                        mt-1
                        text-xl
                        font-semibold
                        text-[#22243A]
                        sm:text-2xl
                      "
                    >
                      {currentCategory.name}
                    </h1>

                  </div>


                  <Badge
                    variant="outline"
                    className="shrink-0"
                  >
                    {answeredCount} of{" "}
                    {totalQuestions}
                  </Badge>

                </div>


                <Progress
                  value={progress}
                  className="
                    mt-5
                    h-2
                  "
                />


                <div
                  className="
                    mt-2
                    flex
                    justify-between
                    text-[11px]
                    text-slate-500
                  "
                >
                  <span>
                    {answeredCount} of{" "}
                    {totalQuestions} questions answered
                  </span>

                  <span>
                    {progress}%
                  </span>
                </div>

              </CardContent>

            </Card>


            {/* SUBTOPICS */}

            {currentCategory.subtopics.map(
              (subtopic) => {

                const impactQuestion =
                  subtopic.questions.find(
                    (question) =>
                      question.dimension ===
                      "IMPACT"
                  ) ??
                  subtopic.questions[0];


                const comment =
                  impactQuestion
                    ? responses[
                        impactQuestion.id
                      ]?.comment ?? ""
                    : "";


                return (
                  <Card
                    key={subtopic.id}
                    className="
                      border-slate-200
                      shadow-sm
                    "
                  >

                    <CardHeader
                      className="
                        border-b
                        border-slate-100
                        px-5
                        py-4
                        sm:px-6
                      "
                    >

                      <CardTitle
                        className="
                          text-base
                          font-semibold
                          text-[#22243A]
                        "
                      >
                        {subtopic.name}
                      </CardTitle>

                    </CardHeader>


                    <CardContent
                      className="
                        space-y-6
                        px-5
                        py-5
                        sm:px-6
                      "
                    >

                      {subtopic.questions.map(
                        (question, index) => {

                          const response =
                            responses[
                              question.id
                            ] ?? {
                              value: null,
                              comment: "",
                            };


                          return (
                            <div
                              key={question.id}
                              className="space-y-4"
                            >

                              <div>

                                <div
                                  className="
                                    mb-2
                                    flex
                                    flex-wrap
                                    gap-2
                                  "
                                >

                                  <Badge
                                    variant="outline"
                                    className="
                                      border-[#DDD8FF]
                                      bg-[#F7F5FF]
                                      text-[#4A3FD6]
                                    "
                                  >
                                    {
                                      DIMENSION_LABELS[
                                        question.dimension
                                      ]
                                    }
                                  </Badge>

                                  {question.is_required && (
                                    <Badge
                                      variant="outline"
                                      className="
                                        border-red-200
                                        bg-red-50
                                        text-red-700
                                      "
                                    >
                                      Required
                                    </Badge>
                                  )}

                                </div>


                                <p
                                  className="
                                    text-sm
                                    font-medium
                                    leading-6
                                    text-[#22243A]
                                  "
                                >
                                  {
                                    question.question_text
                                  }
                                </p>


                                {question.help_text && (
                                  <p
                                    className="
                                      mt-2
                                      text-xs
                                      leading-5
                                      text-slate-500
                                    "
                                  >
                                    {
                                      question.help_text
                                    }
                                  </p>
                                )}

                              </div>


                              <div
                                className="
                                  space-y-2
                                "
                              >

                                {question.scale_options.map(
                                  (option) => {

                                    const selected =
                                      response.value ===
                                      option.value;


                                    return (
                                      <button
                                        key={option.id}
                                        type="button"
                                        className={`
                                          flex
                                          min-h-[58px]
                                          w-full
                                          items-center
                                          gap-3
                                          rounded-xl
                                          border
                                          px-4
                                          py-3
                                          text-left
                                          transition
                                          ${
                                            selected
                                              ? "border-[#4A3FD6] bg-[#F7F5FF] ring-1 ring-[#4A3FD6]"
                                              : "border-slate-200 bg-white hover:bg-slate-50"
                                          }
                                        `}
                                        onClick={async () => {

                                          updateResponse(
                                            question.id,
                                            {
                                              value:
                                                option.value,
                                            }
                                          );


                                          if (!token) {
                                            return;
                                          }


                                          try {

                                            setSavingQuestion(
                                              question.id
                                            );


                                            await PublicSurveyApi.saveResponse(
                                              token,
                                              {
                                                question:
                                                  question.id,
                                                value:
                                                  option.value,
                                                comment:
                                                  response.comment,
                                              }
                                            );


                                            setSavedQuestions(
                                              (previous) => {

                                                const next =
                                                  new Set(
                                                    previous
                                                  );

                                                next.add(
                                                  question.id
                                                );

                                                return next;

                                              }
                                            );

                                          } catch (error) {

                                            console.error(
                                              "Failed to save response:",
                                              error
                                            );

                                            toast.error(
                                              "Unable to save your answer."
                                            );

                                          } finally {

                                            setSavingQuestion(
                                              null
                                            );

                                          }

                                        }}
                                      >

                                        <span
                                          className={`
                                            flex
                                            h-5
                                            w-5
                                            shrink-0
                                            items-center
                                            justify-center
                                            rounded-full
                                            border-2
                                            ${
                                              selected
                                                ? "border-[#4A3FD6]"
                                                : "border-slate-300"
                                            }
                                          `}
                                        >
                                          {selected && (
                                            <span
                                              className="
                                                h-2.5
                                                w-2.5
                                                rounded-full
                                                bg-[#4A3FD6]
                                              "
                                            />
                                          )}
                                        </span>


                                        <div
                                          className="
                                            min-w-0
                                            flex-1
                                          "
                                        >

                                          <p
                                            className="
                                              text-sm
                                              font-medium
                                              text-slate-800
                                            "
                                          >
                                            {option.value}{" "}
                                            —{" "}
                                            {option.label}
                                          </p>


                                          {option.description && (
                                            <p
                                              className="
                                                mt-0.5
                                                text-xs
                                                leading-5
                                                text-slate-500
                                              "
                                            >
                                              {
                                                option.description
                                              }
                                            </p>
                                          )}

                                        </div>


                                        {savingQuestion ===
                                        question.id ? (

                                          <Loader2
                                            className="
                                              h-4
                                              w-4
                                              shrink-0
                                              animate-spin
                                              text-[#4A3FD6]
                                            "
                                          />

                                        ) : savedQuestions.has(
                                            question.id
                                          ) ? (

                                          <Check
                                            className="
                                              h-4
                                              w-4
                                              shrink-0
                                              text-emerald-600
                                            "
                                          />

                                        ) : null}

                                      </button>
                                    );
                                  }
                                )}

                              </div>


                              {index <
                                subtopic.questions.length -
                                  1 && (
                                <Separator />
                              )}

                            </div>
                          );
                        }
                      )}


                      {/* ONE COMMENT PER SUBTOPIC */}

                      <div
                        className="
                          rounded-xl
                          border
                          border-slate-200
                          bg-slate-50
                          p-4
                        "
                      >

                        <label
                          className="
                            text-sm
                            font-medium
                            text-[#22243A]
                          "
                        >
                          Comment about this topic
                        </label>


                        <p
                          className="
                            mt-1
                            text-xs
                            leading-5
                            text-slate-500
                          "
                        >
                          Add any context you would
                          like to share about{" "}
                          {subtopic.name}.
                        </p>


                        <Textarea
                          value={comment}
                          rows={4}
                          placeholder="Optional comment..."
                          className="
                            mt-3
                            resize-none
                            bg-white
                          "
                          onChange={async (event) => {

                            if (!impactQuestion) {
                              return;
                            }


                            const value =
                              event.target.value;


                            updateResponse(
                              impactQuestion.id,
                              {
                                comment:
                                  value,
                              }
                            );


                            if (!token) {
                              return;
                            }


                            try {

                              setSavingQuestion(
                                impactQuestion.id
                              );


                              /*
                               * Response value is preserved
                               * while saving the comment.
                               */

                              await PublicSurveyApi.saveResponse(
                                token,
                                {
                                  question:
                                    impactQuestion.id,
                                  value:
                                    responses[
                                      impactQuestion.id
                                    ]?.value ??
                                    0,
                                  comment:
                                    value,
                                }
                              );


                              setSavedQuestions(
                                (previous) => {

                                  const next =
                                    new Set(
                                      previous
                                    );

                                  next.add(
                                    impactQuestion.id
                                  );

                                  return next;
                                }
                              );

                            } catch (error) {

                              console.error(
                                "Failed to save comment:",
                                error
                              );

                              toast.error(
                                "Unable to save your comment."
                              );

                            } finally {

                              setSavingQuestion(
                                null
                              );

                            }

                          }}
                        />

                      </div>

                    </CardContent>

                  </Card>
                );
              }
            )}


            {/* NAVIGATION */}

            <div
              className="
                sticky
                bottom-0
                z-10
                -mx-4
                border-t
                border-slate-200
                bg-slate-50/95
                px-4
                py-3
                backdrop-blur
                sm:static
                sm:border-0
                sm:bg-transparent
                sm:px-0
                sm:py-0
              "
            >

              <div
                className="
                  flex
                  items-center
                  justify-between
                  gap-3
                "
              >

                <Button
                  type="button"
                  variant="outline"
                  disabled={
                    categoryIndex === 0
                  }
                  onClick={() =>
                    setCategoryIndex(
                      (previous) =>
                        Math.max(
                          previous - 1,
                          0
                        )
                    )
                  }
                  className="
                    min-h-[46px]
                    gap-2
                  "
                >

                  <ArrowLeft
                    className="h-4 w-4"
                  />

                  Back

                </Button>


                {categoryIndex <
                categories.length - 1 ? (

                  <Button
                    type="button"
                    className="
                      min-h-[46px]
                      gap-2
                      bg-[#4A3FD6]
                      text-white
                      hover:bg-[#3F34C2]
                    "
                    onClick={() =>
                      setCategoryIndex(
                        (previous) =>
                          previous + 1
                      )
                    }
                  >

                    Next

                    <ArrowRight
                      className="h-4 w-4"
                    />

                  </Button>

                ) : (

                  <Button
                    type="button"
                    className="
                      min-h-[46px]
                      gap-2
                      bg-[#4A3FD6]
                      text-white
                      hover:bg-[#3F34C2]
                    "
                    onClick={() =>
                      setStep(
                        "review"
                      )
                    }
                  >

                    Review Responses

                    <ArrowRight
                      className="h-4 w-4"
                    />

                  </Button>

                )}

              </div>

            </div>

          </div>
        )}
                {/* ==================================================
            REVIEW
        ================================================== */}

        {step === "review" && (

          <div className="space-y-5">

            <Card
              className="
                border-slate-200
                shadow-sm
              "
            >

              <CardHeader
                className="
                  px-5
                  py-6
                  sm:px-6
                "
              >

                <Badge
                  variant="outline"
                  className="
                    w-fit
                    border-[#DDD8FF]
                    bg-[#F7F5FF]
                    text-[#4A3FD6]
                  "
                >
                  Final Review
                </Badge>

                <CardTitle
                  className="
                    mt-3
                    text-xl
                    font-semibold
                    text-[#22243A]
                  "
                >
                  Review your responses
                </CardTitle>

                <CardDescription>
                  Check your responses before submitting.
                </CardDescription>

              </CardHeader>


              <Separator />


              <CardContent
                className="
                  space-y-3
                  px-5
                  py-5
                  sm:px-6
                "
              >

                {categories.map(
                  (
                    category,
                    index
                  ) => {

                    const categoryQuestions =
                      category.subtopics.flatMap(
                        (subtopic) =>
                          subtopic.questions
                      );


                    const categoryAnswered =
                      categoryQuestions.filter(
                        (question) =>
                          responses[
                            question.id
                          ]?.value !== null &&
                          responses[
                            question.id
                          ]?.value !==
                            undefined
                      ).length;


                    const complete =
                      categoryAnswered ===
                      categoryQuestions.length;


                    return (
                      <button
                        key={category.id}
                        type="button"
                        onClick={() => {

                          setCategoryIndex(
                            index
                          );

                          setStep(
                            "survey"
                          );

                        }}
                        className="
                          flex
                          w-full
                          items-center
                          justify-between
                          gap-4
                          rounded-xl
                          border
                          border-slate-200
                          px-4
                          py-4
                          text-left
                          hover:bg-slate-50
                        "
                      >

                        <div>
                          <p
                            className="
                              text-sm
                              font-semibold
                              text-[#22243A]
                            "
                          >
                            {category.name}
                          </p>

                          <p
                            className="
                              mt-1
                              text-xs
                              text-slate-500
                            "
                          >
                            {categoryAnswered} of{" "}
                            {
                              categoryQuestions.length
                            }{" "}
                            questions answered
                          </p>
                        </div>


                        {complete ? (

                          <div
                            className="
                              flex
                              h-8
                              w-8
                              items-center
                              justify-center
                              rounded-full
                              bg-emerald-50
                              text-emerald-600
                            "
                          >
                            <Check className="h-4 w-4" />
                          </div>

                        ) : (

                          <Badge
                            variant="outline"
                            className="
                              border-amber-200
                              bg-amber-50
                              text-amber-700
                            "
                          >
                            Incomplete
                          </Badge>

                        )}

                      </button>
                    );

                  }
                )}

              </CardContent>

            </Card>


            <Card
              className="
                border-[#DDD8FF]
                bg-[#FBFAFF]
                shadow-sm
              "
            >

              <CardContent
                className="
                  flex
                  flex-col
                  gap-4
                  px-5
                  py-6
                  sm:flex-row
                  sm:items-center
                  sm:justify-between
                  sm:px-6
                "
              >

                <div>

                  <p
                    className="
                      text-sm
                      font-semibold
                      text-[#22243A]
                    "
                  >
                    {answeredCount} of{" "}
                    {totalQuestions} questions answered
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      leading-5
                      text-slate-500
                    "
                  >
                    You won't be able to change your
                    answers after submission.
                  </p>

                </div>


                <Button
                  type="button"
                  disabled={
                    answeredCount <
                    totalQuestions
                  }
                  onClick={() =>
                    setSubmitOpen(true)
                  }
                  className="
                    min-h-[46px]
                    gap-2
                    bg-[#4A3FD6]
                    text-white
                    hover:bg-[#3F34C2]
                  "
                >

                  <CheckCircle2
                    className="h-4 w-4"
                  />

                  Submit Survey

                </Button>

              </CardContent>

            </Card>


            <Button
              type="button"
              variant="ghost"
              className="gap-2"
              onClick={() =>
                setStep("survey")
              }
            >

              <ArrowLeft
                className="h-4 w-4"
              />

              Back to Survey

            </Button>

          </div>
        )}


        {/* ==================================================
            SUBMIT CONFIRMATION
        ================================================== */}

        <Dialog
          open={submitOpen}
          onOpenChange={(
            open
          ) => {

            if (
              !open &&
              !submitting
            ) {
              setSubmitOpen(false);
            }

          }}
        >

          <DialogContent
            className="
              w-[95vw]
              max-w-md
              border-slate-200
              bg-white
            "
          >

            <DialogHeader>

              <div
                className="
                  mx-auto
                  flex
                  h-12
                  w-12
                  items-center
                  justify-center
                  rounded-full
                  bg-[#F1EFFF]
                  text-[#4A3FD6]
                "
              >

                <CheckCircle2
                  className="
                    h-6
                    w-6
                  "
                />

              </div>

              <DialogTitle
                className="
                  pt-2
                  text-center
                  text-lg
                  text-[#22243A]
                "
              >
                Submit your survey?
              </DialogTitle>

              <DialogDescription
                className="text-center"
              >
                Your responses will be submitted
                and cannot be changed afterwards.
              </DialogDescription>

            </DialogHeader>


            <div
              className="
                rounded-lg
                border
                border-slate-200
                bg-slate-50
                px-4
                py-3
                text-center
                text-xs
                text-slate-600
              "
            >

              {answeredCount} of{" "}
              {totalQuestions} questions answered

            </div>


            <DialogFooter
              className="
                grid
                grid-cols-2
                gap-2
              "
            >

              <Button
                type="button"
                variant="outline"
                disabled={
                  submitting
                }
                onClick={() =>
                  setSubmitOpen(false)
                }
              >
                Cancel
              </Button>


              <Button
                type="button"
                disabled={
                  submitting ||
                  !token
                }
                onClick={async () => {

                  if (!token) {
                    return;
                  }

                  try {

                    setSubmitting(
                      true
                    );

                    await PublicSurveyApi.submitSurvey(
                      token
                    );

                    toast.success(
                      "Survey submitted successfully."
                    );

                    navigate(
                      `/survey/${token}/thank-you`
                    );

                  } catch (error) {

                    console.error(
                      "Failed to submit survey:",
                      error
                    );

                    toast.error(
                      "Unable to submit survey."
                    );

                  } finally {

                    setSubmitting(
                      false
                    );

                  }

                }}
                className="
                  bg-[#4A3FD6]
                  text-white
                  hover:bg-[#3F34C2]
                "
              >

                {submitting && (
                  <Loader2
                    className="
                      mr-2
                      h-4
                      w-4
                      animate-spin
                    "
                  />
                )}

                {submitting
                  ? "Submitting..."
                  : "Submit Survey"}

              </Button>

            </DialogFooter>

          </DialogContent>

        </Dialog>

      </main>

    </div>
  );
}