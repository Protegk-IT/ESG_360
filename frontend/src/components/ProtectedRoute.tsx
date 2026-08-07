import type { ReactNode } from "react";
import AccessDenied from "@/components/AccessDenied";
import { hasPermission } from "@/utils/permissions";

interface ProtectedRouteProps {
  permission: string;
  children: ReactNode;
}

export default function ProtectedRoute({
  permission,
  children,
}: ProtectedRouteProps) {
  const user = JSON.parse(localStorage.getItem("user") || "{}");


  if (user.is_superuser) {
    return <>{children}</>;
  }
  if (hasPermission(permission)) {
    return <>{children}</>;
  }

  return <AccessDenied />;
}