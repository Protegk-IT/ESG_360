import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import api from "../../services/api";

interface AppShellProps {
  title: string;
  description: string;
  children: ReactNode;
  showLogoutButton?: boolean;
}

export default function AppShell({
  title,
  description,
  children,
  showLogoutButton = false,
}: AppShellProps) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post("/accounts/logout/");
    } catch {
      // Keep navigation simple even if the logout call fails.
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
              <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
              <p className="text-sm text-gray-500">{description}</p>
            </div>
          </div>

          {showLogoutButton && (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md bg-orange-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-600"
            >
              Logout
            </button>
          )}
        </header>

        <main className="min-h-[calc(100vh-64px)] bg-gray-100 p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
