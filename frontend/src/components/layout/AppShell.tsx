import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { LogOut } from "lucide-react";

import { toast } from "sonner";

import { useAuth } from "@/context/AuthContext";
import { logoutUser } from "@/services/authService";

import { AppSidebar } from "./AppSidebar";

import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface AppShellProps {
  title: string;
  description: string;
  children: ReactNode;
}

export default function AppShell({
  title,
  description,
  children,
}: AppShellProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const user = JSON.parse(localStorage.getItem("user") ?? "{}");

  const handleLogout = async () => {
    try {
      await logoutUser();
      toast.success("Logout successful.");
    } catch (error) {
      console.error(error);
      toast.error("Unable to contact server. Logging out locally.");
    } finally {
      logout();
      navigate("/login", { replace: true });
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar />

      <SidebarInset className="min-w-0 bg-[#F5F5FB]">
        {/* ================= Header ================= */}
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-[#8891A3] bg-white px-3 shadow-sm sm:h-16 sm:px-6">
          {/* Left */}
          <div className="flex min-w-0 items-center gap-2 sm:gap-4">
            <SidebarTrigger className="shrink-0 rounded-lg hover:bg-[#ECE9FB]" />

            <div className="min-w-0">
              <h1 className="truncate text-base font-extrabold tracking-tight text-[#22243A] sm:text-2xl">
                {title}
              </h1>

              <p className="mt-0.5 hidden truncate text-sm text-[#6B7280] sm:block">
                {description}
              </p>
            </div>
          </div>

          {/* Right */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-10 shrink-0 gap-2 rounded-lg px-2 hover:bg-[#EEF2FF] sm:gap-3 sm:px-3"
              >
                {/* Avatar */}
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#4A3FD6] text-xs font-semibold text-white">
                  {(user?.full_name || user?.username || "Loading...")
                    .charAt(0)
                    .toUpperCase()}
                </div>

                {/* Name — hidden on narrow screens to save header space */}
                <div className="hidden flex-col items-start leading-tight sm:flex">
                  <span className="max-w-[140px] truncate text-sm font-semibold text-[#22243A]">
                    {user?.full_name || user?.username || "Loading..."}
                  </span>
                </div>
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-60 rounded-xl">
              <div className="border-b px-4 py-3">
                <p className="truncate font-semibold text-[#22243A]">
                  {user?.full_name || user?.username || "Loading..."}
                </p>
              </div>

              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-red-600 focus:text-red-600"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* ================= Page ================= */}
       <main className="min-h-[calc(100vh-56px)] min-w-0 bg-[#F5F5FB] p-3 sm:min-h-[calc(100vh-64px)] sm:p-6">
  {children}
</main>
      </SidebarInset>
    </SidebarProvider>
  );
}