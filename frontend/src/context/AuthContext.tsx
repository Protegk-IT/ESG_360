import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { AuthUser } from "@/types/auth";
import api, { registerLogoutHandler, setCsrfToken } from "@/services/api";

interface AuthContextType {
  user: AuthUser | null;
  permissions: string[];
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface Props {
  children: ReactNode;
}

export function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(
    () => !["/", "/login"].includes(window.location.pathname)
  );
  const authGeneration = useRef(0);

  const login = useCallback((user: AuthUser) => {
    authGeneration.current += 1;
    setUser(user);
    setPermissions(user.permissions ?? []);

    // Authentication and authorisation are server-session state. Remove the
    // legacy cache so no component can accidentally treat it as authoritative.
    localStorage.removeItem("user");
    localStorage.removeItem("permissions");
  }, []);

  const logout = useCallback(() => {
    authGeneration.current += 1;
    setUser(null);
    setPermissions([]);

    localStorage.removeItem("user");
    localStorage.removeItem("permissions");
  }, []);

  useEffect(() => {
    registerLogoutHandler(logout);
  }, [logout]);

  useEffect(() => {
    let mounted = true;

    if (["/", "/login"].includes(window.location.pathname)) {
      return () => { mounted = false; };
    }

    async function restoreSession() {
      const generation = authGeneration.current;
      try {
        const [meResponse, csrfResponse] = await Promise.all([
          api.get<AuthUser>("/accounts/me/"),
          api.get<{ csrfToken: string }>("/accounts/csrf/"),
        ]);
        if (!mounted || authGeneration.current !== generation) return;
        setCsrfToken(csrfResponse.data.csrfToken);
        setUser(meResponse.data);
        setPermissions(meResponse.data.permissions ?? []);
      } catch {
        if (mounted && authGeneration.current === generation) logout();
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    restoreSession();
    return () => { mounted = false; };
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        isAuthenticated: !!user,
        isLoading,
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
