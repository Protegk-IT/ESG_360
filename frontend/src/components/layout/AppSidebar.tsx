import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
} from "@/components/ui/sidebar";

import { navMain } from "./sidebar-data";
import { NavMain } from "./NavMain";
import { NavUser } from "./NavUser";

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">

      <SidebarHeader className="border-b group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-2">

        <div className="px-4 py-5 group-data-[collapsible=icon]:px-0">

          <h1 className="text-xl font-bold text-orange-500">
            <span className="group-data-[collapsible=icon]:hidden">ESG360</span>
            <span className="hidden group-data-[collapsible=icon]:inline">E</span>
          </h1>

          <p className="text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
            Platform Admin
          </p>

        </div>

      </SidebarHeader>

      <SidebarContent>
        <NavMain items={navMain} />
      </SidebarContent>

      <NavUser />

    </Sidebar>
  );
}
