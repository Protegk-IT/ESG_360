import {
  SidebarFooter,
} from "@/components/ui/sidebar";

export function NavUser() {
  return (
    <SidebarFooter className="group-data-[collapsible=icon]:p-2">

      <div className="w-full border-t p-4 group-data-[collapsible=icon]:hidden">

        <p className="font-medium">
          Platform Admin
        </p>

        <p className="text-xs text-muted-foreground">
          admin@esg360.com
        </p>

      </div>

    </SidebarFooter>
  );
}
