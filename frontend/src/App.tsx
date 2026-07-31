import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/auth/Login";
import CompaniesPage from "./pages/companies/CompaniesPage";
import OrganizationsPage from "./pages/organizations/OrganizationsPage";
import DepartmentsPage from "./pages/departments/DepartmentsPage";
import PlatformAdminDashboard from "./pages/platform_admin/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Navigate to="/accounts/dashboard/" replace />} />
        <Route path="/accounts/dashboard/" element={<PlatformAdminDashboard />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/organizations" element={<OrganizationsPage />} />
        <Route path="/departments" element={<DepartmentsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
