import {
  FileBarChart2,
  FileText,
  FolderTree,
  LayoutDashboard,
  Leaf,
  Settings,
  ShieldCheck,
} from "lucide-react";

export const navMain = [
  {
    title: "Dashboard",
    url: "/accounts/dashboard/",
    icon: LayoutDashboard,
  },

  {
    title: "Administration",
    icon: ShieldCheck,
    items: [
      {
        title: "Company Management",
        url: "/companies",
      },
      {
        title: "User Management",
        url: "/accounts/users",
      },
      {
        title: "Role Management",
        url: "/accounts/roles",
      },
       {
        title: "Departments",
        url: "/company/departments",
      },
    ],
  },

  {
    title: "Organization",
    icon: FolderTree,
    items: [
      {
        title: "Organization",
        url: "/organizations",
      },
    ],
  },

  {
    title: "Materiality Assessment",
    icon: FileText,
    items: [
      {
        title: "Topic Library",
        url: "/materiality/topics",
      },
       {
        title: "Assessment",
        url: "/materiality/assessments",
      },
    

    ],
  },

  {
    title: "Emissions",
    icon: Leaf,
    items: [
      {
        title: "Scope 1",
        url: "/emissions/scope-1",
      },
      {
        title: "Scope 2",
        url: "/emissions/scope-2",
      },
      {
        title: "Scope 3",
        url: "/emissions/scope-3",
      },
    ],
  },

  {
    title: "Reports",
    icon: FileBarChart2,
    items: [
      {
        title: "Reporting Periods",
        url: "/periods",
      },
      {
        title: "Reporting Forms",
        url: "/periods/create",
      },
    ],
  },

  {
    title: "Settings",
    url: "/settings/",
    icon: Settings,
  },
];