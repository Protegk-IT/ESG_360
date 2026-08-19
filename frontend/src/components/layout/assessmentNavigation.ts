import {
  ArrowLeft,
  BarChart3,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Network,
  Users,
} from "lucide-react";

export const getAssessmentNav = (assessmentId?: string | null) => {
  if (!assessmentId) {
    return [];
  }

  const base = `/materiality/assessments/${assessmentId}`;

  return [
    {
      title: "All assessments",
      url: "/materiality/assessments",
      icon: ArrowLeft,
    },
    {
      title: "Overview",
      url: base,
      icon: LayoutDashboard,
    },
    {
      title: "1. Scope & Topics",
      url: `${base}/select-topics`,
      icon: Network,
    },

    {
      title: "2. Stakeholder Setup",
      url: `${base}/stakeholders`,
      icon: Users,
    },

    {
      title: "3. Survey & Responses",
      url: `${base}/survey`,
      icon: Users,
    },

    {
      title: "Distribution",
      url: `${base}/survey/distribution`,
      icon: FileText,
    },

    {
      title: "4. Scoring & Review",
      url: `${base}/scoring`,
      icon: ClipboardList,
    },

    {
      title: "5. Results & Matrix",
      url: `${base}/matrix`,
      icon: BarChart3,
    },
  ];
};
