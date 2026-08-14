import {
  Building,
  FolderTree,
  Factory,
  Users,
  ShieldCheck,
  Activity,
  UserPlus,
  Leaf,
  Droplets,
  Scale,
} from "lucide-react";

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "@/services/api";

import AppShell from "@/components/layout/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/* ==========================================================
    TYPES
========================================================== */

interface DashboardStats {
  organizations: number;
  departments: number;
  facility: number;
  users: number;
  active_users: number;
  inactive_users: number;
  roles: number;
  permissions: number;
  system_status: string;
}

const emptyStats: DashboardStats = {
  organizations: 0,
  departments: 0,
  facility: 0,
  users: 0,
  active_users: 0,
  inactive_users: 0,
  roles: 0,
  permissions: 0,
  system_status: "Unknown",
};

export default function Dashboard() {
  const navigate = useNavigate();

  const [stats, setStats] = useState<DashboardStats>(emptyStats);
  const [loading, setLoading] = useState(true);

  /* ==========================================================
      LOAD DASHBOARD
  ========================================================== */

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const { data } = await api.get("/accounts/dashboard/");

        if (cancelled) return;

        setStats({
          organizations: data.organizations ?? 0,
          departments: data.departments ?? 0,
          facility: data.facility ?? 0,
          users: data.users ?? 0,
          active_users: data.active_users ?? 0,
          inactive_users: data.inactive_users ?? 0,
          roles: data.roles ?? 0,
          permissions: data.permissions ?? 0,
          system_status: data.system_status ?? "Unknown",
        });
      } catch (error) {
        console.error("Dashboard error:", error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  const isHealthy = stats.system_status.toLowerCase() === "healthy";

  return (
    <AppShell
      title="ESG360 Platform Dashboard"
      description="A single view of how your organization is structured, staffed, and governed."
    >
      {/* ==========================================================
          SYSTEM PULSE — signature banner
      ========================================================== */}

      <div
        className="
          relative mb-8 overflow-hidden rounded-2xl
          bg-gradient-to-r from-[#0F5C46] via-[#0E7C86] to-[#0F5C46]
          px-8 py-7 text-white shadow-sm
        "
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, white 1px, transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        />

        <div className="relative flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div
              className={`
                flex h-3 w-3 items-center justify-center rounded-full
                ${isHealthy ? "bg-emerald-300" : "bg-amber-300"}
              `}
            >
              <span
                className={`
                  h-3 w-3 animate-ping rounded-full
                  ${isHealthy ? "bg-emerald-300" : "bg-amber-300"}
                `}
              />
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                System Pulse
              </p>
              <h2 className="mt-1 text-2xl font-semibold">
                {loading ? "Checking status..." : stats.system_status}
              </h2>
            </div>
          </div>

          <div className="flex gap-8 text-sm text-white/80">
            <div>
              <p className="text-white/60">Active Users</p>
              <p className="text-lg font-semibold text-white">
                {stats.active_users}
              </p>
            </div>
            <div>
              <p className="text-white/60">Roles Configured</p>
              <p className="text-lg font-semibold text-white">
                {stats.roles}
              </p>
            </div>
            <div>
              <p className="text-white/60">Permissions Defined</p>
              <p className="text-lg font-semibold text-white">
                {stats.permissions}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ==========================================================
          KPI CARDS
      ========================================================== */}

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <FolderTree className="mb-5 h-8 w-8 text-[#0F7A5C]" />
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Organizations
            </p>
            <h2 className="mt-2 text-4xl font-bold">{stats.organizations}</h2>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <Building className="mb-5 h-8 w-8 text-[#0F7A5C]" />
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Departments
            </p>
            <h2 className="mt-2 text-4xl font-bold">{stats.departments}</h2>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <Factory className="mb-5 h-8 w-8 text-[#0F7A5C]" />
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Facilities
            </p>
            <h2 className="mt-2 text-4xl font-bold">{stats.facility}</h2>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <Users className="mb-5 h-8 w-8 text-[#0F7A5C]" />
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Active Users
            </p>
            <h2 className="mt-2 text-4xl font-bold">{stats.active_users}</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {stats.inactive_users} inactive
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ==========================================================
          ESG FOCUS AREAS — static, thematic
      ========================================================== */}

      <Card className="mt-8">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-2xl font-bold">ESG Focus Areas</h2>
            <p className="text-sm text-muted-foreground">
              The three pillars this platform is built to help you govern.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border bg-[#ECFDF5] p-5">
              <Leaf className="mb-3 h-6 w-6 text-[#0F7A5C]" />
              <h3 className="font-semibold text-[#0F5C46]">Environmental</h3>
              <p className="mt-1 text-sm text-[#0F5C46]/70">
                Track resource use, emissions, and facility-level impact.
              </p>
            </div>

            <div className="rounded-xl border bg-[#ECFEFF] p-5">
              <Droplets className="mb-3 h-6 w-6 text-[#0E7C86]" />
              <h3 className="font-semibold text-[#0E5A63]">Social</h3>
              <p className="mt-1 text-sm text-[#0E5A63]/70">
                Manage people, departments, and workforce accountability.
              </p>
            </div>

            <div className="rounded-xl border bg-[#F0FDF4] p-5">
              <Scale className="mb-3 h-6 w-6 text-[#166534]" />
              <h3 className="font-semibold text-[#166534]">Governance</h3>
              <p className="mt-1 text-sm text-[#166534]/70">
                Enforce roles, permissions, and org-level access control.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ==========================================================
          QUICK ACTIONS
      ========================================================== */}

      <Card className="mt-8">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-2xl font-bold">Quick Actions</h2>
            <p className="text-sm text-muted-foreground">
              Frequently used platform administration tasks.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Button
              variant="outline"
              className="h-auto justify-start p-6"
              onClick={() => navigate("/accounts/users/create")}
            >
              <div className="flex flex-col items-start">
                <UserPlus className="mb-4 h-7 w-7 text-[#0F7A5C]" />
                <h3 className="font-semibold">Add User</h3>
                <p className="mt-1 text-left text-sm text-muted-foreground">
                  Onboard a new platform user.
                </p>
              </div>
            </Button>

            <Button
              variant="outline"
              className="h-auto justify-start p-6"
              onClick={() => navigate("/organizations")}
            >
              <div className="flex flex-col items-start">
                <FolderTree className="mb-4 h-7 w-7 text-[#0F7A5C]" />
                <h3 className="font-semibold">Organizations</h3>
                <p className="mt-1 text-left text-sm text-muted-foreground">
                  Manage organizational hierarchy.
                </p>
              </div>
            </Button>

            <Button
              variant="outline"
              className="h-auto justify-start p-6"
              onClick={() => navigate("/company/departments")}
            >
              <div className="flex flex-col items-start">
                <Building className="mb-4 h-7 w-7 text-[#0F7A5C]" />
                <h3 className="font-semibold">Departments</h3>
                <p className="mt-1 text-left text-sm text-muted-foreground">
                  Configure company departments.
                </p>
              </div>
            </Button>

            <Button
              variant="outline"
              className="h-auto justify-start p-6"
              onClick={() => navigate("/accounts/roles")}
            >
              <div className="flex flex-col items-start">
                <ShieldCheck className="mb-4 h-7 w-7 text-[#0F7A5C]" />
                <h3 className="font-semibold">Roles & Access</h3>
                <p className="mt-1 text-left text-sm text-muted-foreground">
                  Define roles and permission.
                </p>
              </div>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ==========================================================
          RECENT ACTIVITY
      ========================================================== */}

      <Card className="mt-8">
        <CardContent className="p-6">
          <div className="mb-6 flex items-center gap-3">
            <Activity className="h-6 w-6 text-[#0F7A5C]" />
            <div>
              <h2 className="text-2xl font-bold">Recent Activity</h2>
              <p className="text-sm text-muted-foreground">
                Latest platform events
              </p>
            </div>
          </div>

          <div className="space-y-5">
            <div className="flex items-start gap-4">
              <div className="mt-2 h-2.5 w-2.5 rounded-full bg-[#0F7A5C]" />
              <div>
                <p className="font-medium">Platform initialized successfully</p>
                <p className="text-sm text-muted-foreground">
                  System is ready for organization and role management.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="mt-2 h-2.5 w-2.5 rounded-full bg-[#0E7C86]" />
              <div>
                <p className="font-medium">Administrator logged in</p>
                <p className="text-sm text-muted-foreground">
                  Welcome to ESG360 Platform Administration.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="mt-2 h-2.5 w-2.5 rounded-full bg-amber-500" />
              <div>
                <p className="font-medium">
                  {stats.roles === 0
                    ? "No roles configured yet"
                    : `${stats.roles} role${stats.roles === 1 ? "" : "s"} configured`}
                </p>
                <p className="text-sm text-muted-foreground">
                  {stats.roles === 0
                    ? "Set up roles and permissions to begin assigning access."
                    : "Assign roles to users under Accounts → Users."}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <p className="mt-4 text-center text-xs text-muted-foreground">
          Refreshing live stats…
        </p>
      )}
    </AppShell>
  );
}