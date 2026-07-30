/* eslint-disable @typescript-eslint/no-explicit-any */
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

import type { LucideIcon } from "lucide-react";

export interface SidebarSubItem {
  title: string;
  url: string;
}

export interface SidebarItem {
  title: string;
  icon: LucideIcon;
  url?: string;
  items?: SidebarSubItem[];
}
export function NavMain({
  items,
}: {
  items: any[];
}) {
  const location = useLocation();

  return (
    <SidebarGroup>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            if (!item.items) {
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === item.url}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            }

            return (
              <Collapsible
                key={item.title}
                defaultOpen
                className="group/collapsible"
              >
                <SidebarMenuItem>

                  <CollapsibleTrigger asChild>

                    <SidebarMenuButton>

                      <item.icon />

                      <span>{item.title}</span>

                      <ChevronRight className="ml-auto transition-transform group-data-[collapsible=icon]:hidden group-data-[state=open]/collapsible:rotate-90" />

                    </SidebarMenuButton>

                  </CollapsibleTrigger>

                  <CollapsibleContent className="group-data-[collapsible=icon]:hidden">

                    <SidebarMenuSub>

                      {item.items.map((sub: any) => (
                        <SidebarMenuSubItem key={sub.title}>

                          <SidebarMenuSubButton
                            asChild
                            isActive={
                              location.pathname === sub.url
                            }
                          >
                            <Link to={sub.url}>
                              <span>{sub.title}</span>
                            </Link>
                          </SidebarMenuSubButton>

                        </SidebarMenuSubItem>
                      ))}

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
