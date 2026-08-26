import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import AccessDenied from "@/components/AccessDenied";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  permission?: string;
  permissions?: string[];
  superuserOnly?: boolean;
  children: ReactNode;
}

export default function ProtectedRoute({
  permission,
  permissions,
  superuserOnly = false,
  children,
}: ProtectedRouteProps) {
  const { user, permissions: userPermissions, isLoading } = useAuth();

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

  // Preserve existing single-permission behavior.
  if (permission && userPermissions.includes(permission)) {
    return <>{children}</>;
  }

  // Support multiple permissions using OR logic.
  if (
    permissions &&
    permissions.some((item) => userPermissions.includes(item))
  ) {
    return <>{children}</>;
  }

  // Preserve the existing behavior when no permission is provided.
  if (!permission && !permissions) {
    return <>{children}</>;
  }

  return <AccessDenied />;
}