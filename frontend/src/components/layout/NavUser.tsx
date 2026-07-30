import {
  SidebarFooter,
} from "@/components/ui/sidebar";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";

export function NavUser() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.post("/accounts/logout/");
    } catch {
      // Keep logout resilient even if the backend call fails.
    } finally {
      navigate("/");
    }
  };

  return (
    <SidebarFooter className="group-data-[collapsible=icon]:p-2">

      <div className="w-full border-t p-4 group-data-[collapsible=icon]:hidden">

        <p className="font-medium">
          Platform Admin
        </p>

        <p className="text-xs text-muted-foreground">
          admin@esg360.com
        </p>

        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 w-30 rounded-md bg-orange-500 px-3 py-2 text-sm font-medium text-white transition hover:bg-orange-600"
        >
          Logout
        </button>

      </div>

    </SidebarFooter>
  );
}
