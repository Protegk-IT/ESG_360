import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "@/services/api";
import { SidebarFooter } from "@/components/ui/sidebar";

interface User {
  id: number;
  full_name: string;
  username: string;
  email: string;
}

export function NavUser() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api
      .get("/accounts/me/")
      .then((res) => setUser(res.data))
      .catch((err) => console.error(err));
  }, []);

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
          {user?.full_name || user?.username || "Loading..."}
        </p>

        <p className="text-xs text-muted-foreground">
          {user?.email || ""}
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