import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import AccessDenied from "@/components/AccessDenied";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  permission?: string;
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

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (user.is_superuser) {
    return <>{children}</>;
  }
  if (superuserOnly) {
    return <AccessDenied />;
  }
    if (!permission || permissions.includes(permission)) {
    return <>{children}</>;
  }

  return <AccessDenied />;
}
