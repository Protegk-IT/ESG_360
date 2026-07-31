import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/auth/Login";
import CompaniesPage from "./pages/companies/CompaniesPage";
import OrganizationsPage from "./pages/organizations/OrganizationsPage";
import DepartmentsPage from "./pages/departments/DepartmentsPage";
import FacilitiesPage from "./pages/facilities/FacilitiesPage";

// User Management
import UserList from "./pages/users/UserList";
import UserCreate from "./pages/users/UserCreate";

//Role Management
import RoleList from "./pages/roles/RoleList";
import RoleForm from "./pages/roles/RoleForm";

// Platform Admin
import PlatformAdminDashboard from "./pages/platform_admin/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route
          path="/dashboard"
          element={<Navigate to="/accounts/dashboard/" replace />}
        />

        <Route
          path="/accounts/dashboard/"
          element={<PlatformAdminDashboard />}
        />

        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/organizations" element={<OrganizationsPage />} />
        <Route path="/departments" element={<DepartmentsPage />} />
        <Route path="/facilities" element={<FacilitiesPage />} />

        {/* User Management */}
        <Route path="/accounts/users" element={<UserList />} />
        <Route path="/accounts/users/create" element={<UserCreate />} />
        <Route path="/accounts/roles" element={<RoleList />} />
        <Route path="/accounts/roles/create" element={<RoleForm />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}