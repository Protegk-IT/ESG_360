import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/auth/Login";

// Existing Pages
// import Dashboard from "./pages/dashboard/Dashboard";
import CompaniesPage from "./pages/companies/CompaniesPage";
import OrganizationsPage from "./pages/organizations/OrganizationsPage";

// Platform Admin
import PlatformAdminDashboard from "./pages/platform_admin/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Authentication */}
        <Route path="/" element={<Login />} />

        {/* Existing Dashboard
        <Route path="/dashboard" element={<Dashboard />} /> */}

        {/* Platform Admin Dashboard */}
        <Route
          path="/accounts/dashboard/"
          element={<PlatformAdminDashboard />}
        />

        {/* Existing Pages */}
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/organizations" element={<OrganizationsPage />} />

        {/* Future Company Routes */}
        {/* <Route path="/companies/create" element={<CreateCompany />} /> */}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}