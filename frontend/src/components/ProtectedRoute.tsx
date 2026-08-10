import type { ReactNode } from "react";
import AccessDenied from "@/components/AccessDenied";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  permission: string;
  superuserOnly?: boolean;
  children: ReactNode;
}

export default function ProtectedRoute({
  permission,
  superuserOnly = false,
  children,
}: ProtectedRouteProps) {
  const { user, permissions, isLoading } = useAuth();

  if (isLoading) return null;

  if (user?.is_superuser) {
    return <>{children}</>;
  }
  if (superuserOnly) {
    return <AccessDenied />;
  }
  if (permissions.includes(permission)) {
    return <>{children}</>;
  }

  return <AccessDenied />;
}
