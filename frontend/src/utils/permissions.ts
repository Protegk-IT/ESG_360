// src/utils/permissions.ts

/**
 * Get all permissions of the logged-in user.
 */
export const getPermissions = (): string[] => {
  try {
    const permissions = localStorage.getItem("permissions");

    if (!permissions) {
      return [];
    }

    return JSON.parse(permissions);
  } catch (error) {
    console.error("Failed to parse permissions:", error);
    return [];
  }
};

/**
 * Check if user has a permission.
 */
export const hasPermission = (permission: string): boolean => {
  return getPermissions().includes(permission);
};

/**
 * Check if user has any permission.
 */
export const hasAnyPermission = (permissions: string[]): boolean => {
  const userPermissions = getPermissions();

  return permissions.some((permission) =>
    userPermissions.includes(permission)
  );
};

/**
 * Check if user has all permissions.
 */
export const hasAllPermissions = (permissions: string[]): boolean => {
  const userPermissions = getPermissions();

  return permissions.every((permission) =>
    userPermissions.includes(permission)
  );
};