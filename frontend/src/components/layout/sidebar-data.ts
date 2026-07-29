import {
  Building2,
  FileText,
  FolderTree,
  LayoutDashboard,
  Leaf,
  Settings,
} from "lucide-react";

export const navMain = [
  {
    title: "Dashboard",
    url: "/accounts/dashboard/",
    icon: LayoutDashboard,
  },

  {
    title: "Company",
    icon: Building2,

    items: [
      {
        title: "Company Management",
        url: "/accounts/companies/",
      },
    ],
  },

  {
    title: "Organization",
    icon: FolderTree,

    items: [
      {
        title: "Users",
        url: "/accounts/users/",
      },
      {
        title: "Roles",
        url: "/accounts/roles/",
      },
      {
        title: "Departments",
        url: "/accounts/departments/",
      },
    ],
  },

  {
    title: "Frameworks",
    icon: FileText,

    items: [
      {
        title: "BRSR",
        url: "/frameworks/brsr/",
      },
      {
        title: "GRI",
        url: "/frameworks/gri/",
      },
    ],
  },

  {
    title: "Emissions",
    url: "/emissions/",
    icon: Leaf,
  },

  {
    title: "Reports",
    url: "/reports/",
    icon: FileText,
  },

  {
    title: "Settings",
    url: "/settings/",
    icon: Settings,
  },
];