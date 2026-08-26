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
import { useAuth } from "@/context/AuthContext";
import type { SidebarItem, SidebarSubItem } from "./sidebar-data";

interface NavMainProps {
  items: SidebarItem[];
  isAssessmentMode?: boolean;
  assessmentId?: string | null;
}

const isPathActive = (pathname: string, url?: string, exact = false) => {
  if (!url) return false;
  if (exact || url === "/materiality/assessments") return pathname === url;
  return pathname === url || pathname.startsWith(`${url}/`);
};

const baseItem =
  "h-11 w-full rounded-xl px-4 text-sm font-medium transition-colors duration-150";
const restState = "text-gray-600 hover:bg-blue-50 hover:text-blue-700";
const activeState = "bg-blue-50 text-blue-700 font-semibold";

const baseSubItem =
  "h-9 w-full rounded-lg px-3 text-sm transition-colors duration-150";
const restSubState = "text-gray-500 hover:bg-blue-50 hover:text-blue-700";
const activeSubState = "bg-blue-50 text-blue-700 font-medium";

/* ==========================================================
   FLATTENED-GROUP TYPE
   ----------------------------------------------------------
   A group that collapsed to one visible child renders exactly
   like a normal top-level SidebarItem (icon + label + link),
   so it can flow through the same render branch as items that
   were never a group in the first place.
========================================================== */

type RenderableItem = SidebarItem & { items?: SidebarSubItem[] };

export function NavMain({ items }: NavMainProps) {
  const location = useLocation();
  const { user, permissions: userPermissions } = useAuth();

  /* ========================================================
     PERMISSION CHECK
     ----------------------------------------------------------
     Mirrors ProtectedRoute's own logic (superuser bypass, then
     single-permission, then OR-list, then "no permission means
     public"), so the sidebar and the route guard never disagree
     about who can see/reach a screen.
  ======================================================== */

  const hasAccess = (
    permission?: string,
    permissionList?: string[],
  ): boolean => {
    if (user?.is_superuser) return true;
    if (!permission && !permissionList) return true;
    if (permission && userPermissions.includes(permission)) return true;
    if (permissionList?.some((code) => userPermissions.includes(code))) {
      return true;
    }
    return false;
  };

  /* ========================================================
     BUILD THE VISIBLE, ROLE-SHAPED NAV
     ----------------------------------------------------------
     1. Drop groups/links the user has no access to at all.
     2. Within a surviving group, drop sub-items the user can't
        reach.
     3. If exactly one sub-item survives, collapse the group
        into a single flat link — a dropdown with one option
        is friction, not navigation. Two or more sub-items (or
        superuser, who always sees everything) keeps the
        dropdown, since there's an actual choice to present.
  ======================================================== */

  const visibleItems: RenderableItem[] = items
    .filter((item) => hasAccess(item.permission, item.permissions))
    .map((item): RenderableItem => {
      if (!item.items) return item;

      const visibleSubItems = item.items.filter((sub) =>
        hasAccess(sub.permission, sub.permissions),
      );

      if (visibleSubItems.length === 1) {
        const only = visibleSubItems[0];
        return {
          title: item.title,
          icon: item.icon,
          url: only.url,
          permission: item.permission,
          permissions: item.permissions,
          // items intentionally omitted — this now renders as a flat link
        };
      }

      return { ...item, items: visibleSubItems };
    })
    .filter((item) => !item.items || item.items.length > 0);

  const [openTitle, setOpenTitle] = useState<string | null>(() => {
    const match = visibleItems.find((item) =>
      item.items?.some((sub) => sub.url === location.pathname),
    );
    return match?.title ?? null;
  });

  return (
    <SidebarGroup className="px-2 py-2">
      <SidebarGroupContent>
        <SidebarMenu className="space-y-2">
          {visibleItems.map((item) => {
            if (!item.items) {
              const isActive = isPathActive(
                location.pathname,
                item.url,
                item.title === "Overview",
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
                isPathActive(location.pathname, sub.url),
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
                        isParentActive || isOpen ? activeState : restState,
                      )}
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0" />
                      <span className="flex-1 truncate text-left">
                        {item.title}
                      </span>
                      <ChevronRight
                        className={cn(
                          "h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200",
                          isOpen && "rotate-90",
                        )}
                      />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>

                  <CollapsibleContent
                    forceMount
                    className={isOpen ? "block" : "hidden"}
                  >
                    <SidebarMenuSub className="relative ml-5 mt-1 space-y-1 border-l border-gray-200 pl-4">
                      {item.items!.map((sub) => {
                        const isSubActive = isPathActive(
                          location.pathname,
                          sub.url,
                          sub.title === "Overview" ||
                            sub.title === "All assessments" ||
                            sub.title === "3. Survey & Responses",
                        );

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
                                isSubActive ? activeSubState : restSubState,
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