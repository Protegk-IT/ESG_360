import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, UserCircle2 } from "lucide-react";

import api from "@/services/api";

import { SidebarFooter } from "@/components/ui/sidebar";

import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { logoutUser } from "@/services/authService";

import { useAuth } from "@/context/AuthContext";

interface User {
  id: number;
  full_name: string;
  username: string;
  email: string;
}

export function NavUser() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api
      .get("/accounts/me/")
      .then((res) => setUser(res.data))
      .catch(console.error);
  }, []);

  const handleLogout = async () => {
    try {
      await logoutUser();

      toast.success("Logout successful.");
    } catch (error) {
      console.error(error);

      toast.error("Unable to contact server. Logging out locally.");
    } finally {
      logout();
      navigate("/login", { replace: true });
    }
  };

  return (
    <SidebarFooter className="border-t border-gray-100 p-3">
      <div className="group-data-[collapsible=icon]:hidden">
        <div className="mb-2 flex items-center gap-3 px-1">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-green-500 text-white">
            <UserCircle2 className="h-5 w-5" />
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user?.full_name || user?.username || "Loading..."}
            </p>

            <p className="truncate text-xs text-gray-500">{user?.email}</p>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={handleLogout}
          className="
            w-full
            justify-center
            rounded-lg
            border-red-100
            bg-red-50
            text-red-600

            hover:bg-red-100
            hover:text-red-700
            hover:border-red-200

            focus-visible:ring-2
            focus-visible:ring-red-200
          "
        >
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </Button>
      </div>

      {/* Collapsed sidebar */}
      <div className="hidden justify-center group-data-[collapsible=icon]:flex">
        <Button
          size="icon"
          variant="ghost"
          onClick={handleLogout}
          className="text-gray-600 hover:bg-red-50 hover:text-red-600"
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </SidebarFooter>
  );
}