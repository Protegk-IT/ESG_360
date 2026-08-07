import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

import {
  SidebarProvider,
  SidebarInset,
} from "@/components/ui/sidebar";

import { AppSidebar } from "@/components/layout/AppSidebar";

export default function AccessDenied() {
  const navigate = useNavigate();

  return (
    <SidebarProvider>
      <AppSidebar />

      <SidebarInset>
        <div className="flex min-h-screen items-center justify-center bg-gray-50">
          <div className="max-w-md rounded-xl border bg-white p-8 text-center shadow-sm">

            <ShieldX className="mx-auto h-16 w-16 text-red-500" />

            <h1 className="mt-5 text-3xl font-bold">
              Access Denied
            </h1>

            <p className="mt-3 text-muted-foreground">
              You don't have permission to access this page.
            </p>

            <Button
              className="mt-6"
              onClick={() => navigate("/dashboard")}
            >
              Go to Dashboard
            </Button>

          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}