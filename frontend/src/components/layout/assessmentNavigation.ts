import {
  ArrowLeft,
  BarChart3,
  FileText,
  Network,
  Send,
  Users,
} from "lucide-react";

export const getAssessmentNav = (
  assessmentId?: string | null
) => {
  if (!assessmentId) {
    return [];
  }

  const base = `/materiality/assessments/${assessmentId}`;

  return [
    {
      title: "← All Assessments",
      url: "/materiality/assessments",
      icon: ArrowLeft,
    },
    {
      title: "Manage Topics",
      url: `${base}/select-topics/`,
      icon: Network,
    },

    {
      title: "Manage Stakeholder Groups",
      url: `${base}/stakeholders/`,
      icon: Users,
    },

    {
      title: "Manage Survey",
      url: `${base}/survey`,
      icon: FileText,
    },

    {
      title: "Survey Distribution",
      url: `${base}/survey/distribution`,
      icon: Send,
    },

    {
      title: "Materiality Scoring",
      url: `${base}/scoring`,
      icon: BarChart3,
    },

    {
      title: "Materiality Matrix",
      url: `${base}/matrix`,
      icon: BarChart3,
    },
  ];
};