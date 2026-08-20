import type { NavigateFunction } from "react-router-dom";
import { toast } from "sonner";

export type AssessmentStep =
  | "topics"
  | "stakeholder_groups"
  | "stakeholders"
  | "survey"
  | "distribution"
  | "scoring"
  | "matrix"
  | "results"
  | "export";

interface AssessmentProgress {
  id: string;
  current_step?: string | null;
  current_step_url?: string | null;
  progress_percentage?: number | null;
  is_assessment_completed?: boolean | null;
}

const STEP_ORDER: AssessmentStep[] = [
  "topics",
  "stakeholder_groups",
  "stakeholders",
  "survey",
  "distribution",
  "scoring",
  "matrix",
  "results",
  "export",
];

const STEP_LABELS: Record<AssessmentStep, string> = {
  topics: "Manage Topics",
  stakeholder_groups: "Manage Stakeholder Groups",
  stakeholders: "Manage Stakeholders",
  survey: "Manage Survey",
  distribution: "Survey Distribution",
  scoring: "Materiality Scoring",
  matrix: "Materiality Matrix",
  results: "Results",
  export: "Export",
};

export function guardAssessmentStep(
  assessment: AssessmentProgress,
  requestedStep: AssessmentStep,
  navigate: NavigateFunction
): boolean {
  const currentStep = assessment.current_step;

  // No progress information yet.
  // Allow the first step.
  if (!currentStep) {
    return requestedStep === "topics";
  }

  // Assessment is completely finished.
  if (currentStep === "Completed") {
    return true;
  }

  const currentIndex = STEP_ORDER.findIndex(
    (step) => STEP_LABELS[step] === currentStep
  );

  const requestedIndex =
    STEP_ORDER.indexOf(requestedStep);

  // Unknown step.
  if (
    currentIndex === -1 ||
    requestedIndex === -1
  ) {
    return true;
  }

  // Current step and previously completed steps
  // are accessible.
  if (requestedIndex <= currentIndex) {
    return true;
  }

  // Requested step is locked.
  toast.warning(
    `Please complete ${currentStep} first.`
  );

  // Backend already provides the correct URL.
  if (assessment.current_step_url) {
    navigate(assessment.current_step_url);
  }

  return false;
}