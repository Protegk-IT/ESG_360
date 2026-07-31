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
        url: "/companies",
      },
    ],
  },

  {
    title: "Organization",
    icon: FolderTree,

    items: [
      {
        title: "Organizations",
        url: "/organizations",
      },
      {
        title: "Departments",
        url: "/departments",
      },
      {
        title: "Facilities",
        url: "/facilities",
      },
    ],
  },

  {
    title: "Frameworks",
    icon: FileText,

    items: [
      {
        title: "BRSR",
        url: "",
      },
      {
        title: "GRI",
        url: "",
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
