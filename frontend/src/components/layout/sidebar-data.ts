import {
  FileBarChart2,
  FolderTree,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react";

import type { LucideIcon } from "lucide-react";

export interface SidebarSubItem {
  title: string;
  url: string;
  permission: string;
}

export interface SidebarItem {
  title: string;
  icon: LucideIcon;
  url?: string;
  permission?: string;
  items?: SidebarSubItem[];
}

export const navMain: SidebarItem[] = [
  {
    title: "Dashboard",
    url: "/accounts/dashboard/",
    icon: LayoutDashboard,
    permission: "dashboard.view",
  },

  {
    title: "Administration",
    icon: ShieldCheck,
    items: [
      {
        title: "Company Management",
        url: "/companies",
        permission: "company.view",
      },
      {
        title: "User Management",
        url: "/accounts/users",
        permission: "user.view",
      },
      {
        title: "Role Management",
        url: "/accounts/roles",
        permission: "role.view",
      },
       {
        title: "Departments",
        url: "/company/departments",
        permission: "department.view",
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
        permission: "organization.view",
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
        permission: "reporting_period.view",
      },
    ],
  },
];
