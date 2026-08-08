import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
} from "@/components/ui/sidebar";
import { useAuth } from "@/context/AuthContext";

import { navMain } from "./sidebar-data";
import { NavMain } from "./NavMain";
import { NavUser } from "./NavUser";




export function AppSidebar() {
  const { user } = useAuth();
  return (
    <Sidebar
      collapsible="icon"
      className="border-r border-gray-200 bg-white text-slate-900"
    >
      <SidebarHeader className="border-b border-gray-100">
        <div className="flex items-center gap-3 px-4 py-4 transition-all group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-2">
          <div className="relative shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
              E
            </div>
            <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-green-500" />
          </div>

          <div className="min-w-0 group-data-[collapsible=icon]:hidden">
            <h1 className="truncate text-sm font-semibold text-slate-900">
              ESG<span className="text-blue-600">360</span>
            </h1>
           <p className="truncate text-xs text-gray-500">
              {user?.role_name ?? "User"}
            </p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="py-2">
        <NavMain items={navMain} />
      </SidebarContent>

      <NavUser />
    </Sidebar>
  );
}
