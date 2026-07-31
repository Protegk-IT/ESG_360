import {
  Building,
  Building2,
  FolderTree,
  Plus,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";

import { AppSidebar } from "@/components/layout/AppSidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post("/accounts/logout/");
    } catch {
      // Keep logout resilient even if the backend call fails.
    } finally {
      navigate("/");
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar />

      <SidebarInset>
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

          <button
            type="button"
            onClick={handleLogout}
            className="rounded-xl bg-orange-500 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-orange-600"
          >
            Logout
          </button>
        </header>

        <main className="min-h-[calc(100vh-64px)] bg-gray-100 p-8">

          <div className="mb-10 grid gap-6 md:grid-cols-3">
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
              <FolderTree className="mb-3 text-blue-500" />

              <h3 className="text-gray-500">
                OrgNodes
              </h3>

              <p className="text-3xl font-bold">
                0
              </p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow">
              <Building className="mb-3 text-green-500" />

              <h3 className="text-gray-500">
                Departments
              </h3>

              <p className="text-3xl font-bold">
                0
              </p>
            </div>

          </div>

          <div className="mb-10 rounded-xl bg-white p-6 shadow">
            <h2 className="mb-5 text-2xl font-bold">
              Quick Actions
            </h2>

            <div className="grid gap-5 md:grid-cols-3">
              <button
                onClick={() => navigate("/companies")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <Plus className="mx-auto mb-3 text-orange-500" />

                Create Company
              </button>

              <button
                onClick={() => navigate("/organizations")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <FolderTree className="mx-auto mb-3 text-orange-500" />

                OrgNodes
              </button>

              <button
                onClick={() => navigate("/departments")}
                className="rounded-xl border p-6 transition hover:bg-orange-50"
              >
                <Building className="mx-auto mb-3 text-orange-500" />

                Departments
              </button>

            </div>
          </div>

          <div className="rounded-xl bg-white p-6 shadow">
            <h2 className="mb-5 text-2xl font-bold">
              Recent Activity
            </h2>

            <ul className="space-y-4 text-gray-600">
              <li>Platform initialized</li>
              <li>Administrator logged in</li>
              <li>Use the sidebar to open companies, OrgNodes, or departments.</li>
            </ul>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
