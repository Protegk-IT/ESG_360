import {
  Database,
  FileBarChart2,
  FileText,
  FolderTree,
  LayoutDashboard,
  ShieldCheck,
  Target,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
export interface SidebarSubItem {
  title: string;
  url: string;
  permission?: string;
  companyAdminOnly?: boolean;
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
    title: "Goals",
    url: "/goals",
    icon: Target,
    permission: "target.set",
  },
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
    title: "Data Management",
    icon: Database,
    items: [
      {
        title: "Datapoint Catalog",
        url: "/datapoints",
      },
      {
        title: "Units Manager",
        url: "/units/families",
        permission: "datapoint.manage",
      },
      {
        title: "Category Manager",
        url: "/datapoints/categories",
        permission: "datapoint.manage",
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
  {
    title: "Materiality Assessment",
    icon: FileText,
    items: [
      {
        title: "Topic Library",
        url: "/materiality/topics",
        permission: "materiality.view",
        companyAdminOnly: true,
      },
      {
        title: "Assessments",
        url: "/materiality/assessments",
        permission: "materiality.view",
      },
    ],
  },
];
