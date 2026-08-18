import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";

import { cn } from "@/lib/utils";
import type { SidebarItem } from "./sidebar-data";

interface NavMainProps {
  items: SidebarItem[];
  isAssessmentMode?: boolean;
  assessmentId?: string | null;
}

// Explicit JS-driven color states (no dependency on data-* variant support).
const isPathActive = (
  pathname: string,
  url?: string
) => {
  if (!url) {
    return false;
  }

  if (url === "/materiality/assessments") {
    return pathname === url;
  }

  return (
    pathname === url ||
    pathname.startsWith(`${url}/`)
  );
};
const baseItem =
  "h-11 w-full rounded-xl px-4 text-sm font-medium transition-colors duration-150";
const restState = "text-gray-600 hover:bg-blue-50 hover:text-blue-700";
const activeState = "bg-blue-50 text-blue-700 font-semibold";

const baseSubItem =
  "h-9 w-full rounded-lg px-3 text-sm transition-colors duration-150";
const restSubState = "text-gray-500 hover:bg-blue-50 hover:text-blue-700";
const activeSubState = "bg-blue-50 text-blue-700 font-medium";

export function NavMain({
  items,
}: NavMainProps) {
  const location = useLocation();

  // Accordion-style: only one section open at a time.
  // Swap to a Set<string> if you want multiple sections open together.
  const [openTitle, setOpenTitle] = useState<string | null>(() => {
    const match = items.find((item) =>
      item.items?.some((sub) => sub.url === location.pathname)
    );
    return match?.title ?? null;
  });

  return (
    <SidebarGroup className="px-2 py-2">
      <SidebarGroupContent>
        <SidebarMenu className="space-y-2">
          {items.map((item) => {
            if (!item.items) {
              const isActive = isPathActive(
  location.pathname,
  item.url
);
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    className={cn(baseItem, isActive ? activeState : restState)}
                  >
                    <Link to={item.url!} className="flex items-center gap-3">
                      <item.icon className="h-[18px] w-[18px] shrink-0" />

                      <span className="flex-1 truncate text-left">
                        {item.title}
                      </span>

                      {isActive && (
                        <ChevronRight className="h-4 w-4 shrink-0 text-blue-600" />
                      )}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            }

           const isParentActive =
  item.items?.some((sub) =>
    isPathActive(
      location.pathname,
      sub.url
    )
  ) ?? false;
            const isOpen = openTitle === item.title;

            return (
              <Collapsible
                key={item.title}
                open={isOpen}
                onOpenChange={(open) => setOpenTitle(open ? item.title : null)}
                className="group/collapsible"
              >
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton
                      type="button"
                      isActive={isParentActive}
                      className={cn(
                        baseItem,
                        isParentActive || isOpen ? activeState : restState
                      )}
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0" />

                      <span className="flex-1 truncate text-left">
                        {item.title}
                      </span>

                      <ChevronRight
                        className={cn(
                          "h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200",
                          isOpen && "rotate-90"
                        )}
                      />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>

                  {/* forceMount + explicit hidden/block guarantees this renders
                      even if tailwindcss-animate isn't set up in the project */}
                  <CollapsibleContent
                    forceMount
                    className={isOpen ? "block" : "hidden"}
                  >
                    {/* Tree structure: one vertical guide line down the group,
                        each child gets a short horizontal branch to the line */}
                    <SidebarMenuSub className="relative ml-5 mt-1 space-y-1 border-l border-gray-200 pl-4">
                      {item.items.map((sub) => {
                        const isSubActive = location.pathname === sub.url;

                        return (
                          <SidebarMenuSubItem key={sub.title} className="relative">
                            <span
                              aria-hidden="true"
                              className="pointer-events-none absolute -left-4 top-1/2 h-px w-3 -translate-y-1/2 bg-gray-200"
                            />
                        <SidebarMenuSubButton
  asChild
  isActive={isSubActive}
  className={cn(
    baseSubItem,
    isSubActive
      ? activeSubState
      : restSubState
  )}
>
  <Link to={sub.url}>
    <span>{sub.title}</span>
  </Link>
</SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        );
                      })}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </Collapsible>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
