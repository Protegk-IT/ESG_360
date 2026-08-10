import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import Login from "./pages/auth/Login";
import Orgtree from "./pages/organizations/OrgTree";
import OrganizationForm from "./pages/organizations/OrganizationsForm";
import Departmentlist from "./pages/departments/DepartmentList";
import DepartmentsForm from "./pages/departments/DepartmentsForm";
import ReportingPeriodForm from "./pages/reporting_periods/ReportingPeriodForm";

import { Toaster } from "@/components/ui/sonner";

// User Management
import UserList from "./pages/users/UserList";
import UserCreate from "./pages/users/UserCreate";

//Role Management
import RoleList from "./pages/roles/RoleList";
import RoleForm from "./pages/roles/RoleForm";

// Platform Admin
import PlatformAdminDashboard from "./pages/platform_admin/Dashboard";
import CompanyList from "./pages/companies/CompanyView";
import CompanyForm from "./pages/companies/CompanyForm";
import ReportingPeriodList from "./pages/reporting_periods/ReportingPeriodList";

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
    element={<ProtectedRoute permission="dashboard.view"><PlatformAdminDashboard /></ProtectedRoute>}
  />

  {/* Company */}
  <Route
    path="/companies"
    element={
      <ProtectedRoute permission="company.view">
        <CompanyList />
      </ProtectedRoute>
    }
  />

  <Route
  path="/companies/profile/create"
  element={
    <ProtectedRoute permission="company.create">
      <CompanyForm />
    </ProtectedRoute>
  }
/>

<Route
  path="/company/profile/edit"
  element={
    <ProtectedRoute permission="company.edit">
      <CompanyForm />
    </ProtectedRoute>
  }
/>

  {/* Organization */}
  <Route
    path="/organizations"
    element={
      <ProtectedRoute permission="organization.view">
        <Orgtree />
      </ProtectedRoute>
    }
  />
   <Route
    path="/org/nodes"
    element={
      <ProtectedRoute permission="organization.create">
        <OrganizationForm />
      </ProtectedRoute>
    }
  />

  <Route
    path="/org/nodes/:id/edit"
    element={
      <ProtectedRoute permission="organization.edit">
        <OrganizationForm />
      </ProtectedRoute>
    }
  />

  {/* Department */}
  <Route
    path="/company/departments"
    element={
      <ProtectedRoute permission="department.view">
        <Departmentlist />
      </ProtectedRoute>
    }
  />

   <Route
    path="/company/departments/create"
    element={
      <ProtectedRoute permission="department.create">
        <DepartmentsForm />
      </ProtectedRoute>
    }
  />

  <Route
    path="/company/departments/:id/edit"
    element={
      <ProtectedRoute permission="department.edit">
        <DepartmentsForm />
      </ProtectedRoute>
    }
  />

 

  {/* Users */}
  <Route
    path="/accounts/users"
    element={
      <ProtectedRoute permission="user.view">
        <UserList />
      </ProtectedRoute>
    }
  />

  <Route
  path="/accounts/users/edit/:id"
  element={<ProtectedRoute permission="user.edit">
        <UserCreate />
      </ProtectedRoute>
  }
/>

  <Route
    path="/accounts/users/create"
    element={
      <ProtectedRoute permission="user.create">
        <UserCreate />
      </ProtectedRoute>
    }
  />

  {/* Roles */}
  <Route
    path="/accounts/roles"
    element={
      <ProtectedRoute permission="role.view">
        <RoleList />
      </ProtectedRoute>
    }
  />

  <Route
    path="/accounts/roles/create"
    element={
      <ProtectedRoute permission="role.create" superuserOnly>
        <RoleForm />
      </ProtectedRoute>
    }
  />

  <Route
    path="/accounts/roles/:id/edit"
    element={
      <ProtectedRoute permission="role.edit" superuserOnly>
        <RoleForm />
      </ProtectedRoute>
    }
  />

  {/* Reporting Periods */}

  <Route
    path="/periods"
    element={
      <ProtectedRoute permission="reporting_period.view">
        <ReportingPeriodList />
      </ProtectedRoute>
    }
  />

  <Route
    path="/periods/create"
    element={
      <ProtectedRoute permission="reporting_period.create">
        <ReportingPeriodForm />
      </ProtectedRoute>
    }
  />

  <Route
    path="/periods/:id/edit"
    element={
      <ProtectedRoute permission="reporting_period.edit">
        <ReportingPeriodForm />
      </ProtectedRoute>
    }
  />




  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
<Toaster
        position="top-center"
        richColors
      />
    </BrowserRouter>
  );
}
