import {
  Activity,
  Building2,
  FileText,
  Plus,
  Settings,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AppSidebar } from "@/components/layout/AppSidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <SidebarProvider>
      <AppSidebar />

      <SidebarInset>
        {/* Header */}
        <header className="flex h-16 items-center justify-between border-b bg-white px-6">
          <div className="flex items-center gap-4">
            <SidebarTrigger />

            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                ESG360 Platform Admin
              </h1>

              <p className="text-sm text-gray-500">
                Welcome, Platform Administrator
              </p>
            </div>
          </div>

          <div className="rounded-xl border bg-white px-5 py-2 shadow-sm">
            <p className="font-medium">Admin</p>
          </div>
        </header>

        {/* Content */}
        <main className="bg-gray-100 p-8 min-h-[calc(100vh-64px)]">
          {/* Create Company */}
          <div className="mb-10 flex justify-center">
            <button
              onClick={() => navigate("/companies/create")}
              className="rounded-2xl bg-orange-500 px-12 py-10 text-white shadow-xl transition hover:bg-orange-600"
            >
              <Building2 size={60} className="mx-auto mb-4" />

              <h2 className="text-2xl font-bold">
                Create Company
              </h2>

              <p className="mt-2 text-orange-100">
                Register a new organization
              </p>
            </button>
          </div>

          {/* Statistics */}
          <div className="mb-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white p-6 shadow">
              <Building2 className="mb-3 text-orange-500" />

              <h3 className="text-gray-500">
                Companies
              </h3>

              <p className="text-3xl font-bold">
                0
              </p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow">
              <Users className="mb-3 text-blue-500" />

              <h3 className="text-gray-500">
                Users
              </h3>

              <p className="text-3xl font-bold">
                1
              </p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow">
              <ShieldCheck className="mb-3 text-green-500" />

              <h3 className="text-gray-500">
                Platform Admins
              </h3>

              <p className="text-3xl font-bold">
                1
              </p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow">
              <Activity className="mb-3 text-purple-500" />

              <h3 className="text-gray-500">
                System Status
              </h3>

              <p className="text-xl font-bold text-green-600">
                Healthy
              </p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mb-10 rounded-xl bg-white p-6 shadow">
            <h2 className="mb-5 text-2xl font-bold">
              Quick Actions
            </h2>

            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              <button
                onClick={() => navigate("/companies/create")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <Plus className="mx-auto mb-3 text-orange-500" />

                Create Company
              </button>

              <button
                onClick={() => navigate("/companies")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <Building2 className="mx-auto mb-3 text-orange-500" />

                Company Directory
              </button>

              <button
                onClick={() => navigate("/settings")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <Settings className="mx-auto mb-3 text-orange-500" />

                Platform Settings
              </button>

              <button
                onClick={() => navigate("/audit-logs")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <FileText className="mx-auto mb-3 text-orange-500" />

                Audit Logs
              </button>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="rounded-xl bg-white p-6 shadow">
            <h2 className="mb-5 text-2xl font-bold">
              Recent Activity
            </h2>

            <ul className="space-y-4 text-gray-600">
              <li>✅ Platform initialized</li>
              <li>✅ Administrator logged in</li>
              <li>ℹ️ No companies registered yet</li>
            </ul>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}