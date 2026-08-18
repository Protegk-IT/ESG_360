import { Sidebar, SidebarContent, SidebarHeader } from "@/components/ui/sidebar";
import { useAuth } from "@/context/AuthContext";
import { navMain, type SidebarItem } from "./sidebar-data";
import { NavMain } from "./NavMain";
import { NavUser } from "./NavUser";

export function AppSidebar() {
  const { user, permissions } = useAuth();
  const roleLabel = user?.is_superuser ? "Platform administrator" : user?.roles?.join(", ") || "User";
  const canAccess = (permission?: string) => Boolean(user?.is_superuser || (permission && permissions.includes(permission)));
  const items = navMain.flatMap((item): SidebarItem[] => !item.items
    ? (canAccess(item.permission) ? [item] : [])
    : (item.items.filter((child) => canAccess(child.permission)).length ? [{ ...item, items: item.items.filter((child) => canAccess(child.permission)) }] : []));
  return <Sidebar collapsible="icon" className="border-r border-gray-200 bg-white text-slate-900"><SidebarHeader className="border-b border-gray-100"><div className="flex items-center gap-3 px-4 py-4"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">E</div><div className="min-w-0 group-data-[collapsible=icon]:hidden"><h1 className="truncate text-sm font-semibold text-slate-900">ESG<span className="text-blue-600">360</span></h1><p className="truncate text-xs text-gray-500">{roleLabel}</p></div></div></SidebarHeader><SidebarContent className="py-2"><NavMain items={items} /></SidebarContent><NavUser /></Sidebar>;
}
