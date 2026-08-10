import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import type { AuthUser } from "@/types/auth";
import { registerLogoutHandler } from "@/services/api";

interface AuthContextType {
  user: AuthUser | null;
  permissions: string[];
  isAuthenticated: boolean;

  login: (user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface Props {
  children: ReactNode;
}

export function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const stored = localStorage.getItem("user");

      if (!stored || stored === "undefined") {
        return null;
      }

      return JSON.parse(stored);
    } catch {
      localStorage.removeItem("user");
      return null;
    }
  });

  const [permissions, setPermissions] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem("permissions");

      if (!stored || stored === "undefined") {
        return [];
      }

      return JSON.parse(stored);
    } catch {
      localStorage.removeItem("permissions");
      return [];
    }
  });

  const login = useCallback((user: AuthUser) => {
    console.log("Login User:", user);

    setUser(user);
    setPermissions(user.permissions ?? []);

    localStorage.setItem("user", JSON.stringify(user));
    localStorage.setItem(
      "permissions",
      JSON.stringify(user.permissions ?? [])
    );
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setPermissions([]);

    localStorage.removeItem("user");
    localStorage.removeItem("permissions");
  }, []);

  useEffect(() => {
    registerLogoutHandler(logout);
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}