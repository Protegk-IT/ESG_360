import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/components/ProtectedRoute";
import Login from "./pages/auth/Login";
import Orgtree from "./pages/organizations/OrgTree";
import OrganizationForm from "./pages/organizations/OrganizationsForm";
import Departmentlist from "./pages/departments/DepartmentList";
import DepartmentsForm from "./pages/departments/DepartmentsForm";
import ReportingPeriodForm from "./pages/reporting_periods/ReportingPeriodForm";
import ScoringDashboard from "./pages/materiality/ScoringDashboard";

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

//Materiality
import TopicLibrary from "./pages/materiality/TopicLibrary";
import AssessmentList from "./pages/materiality/AssessmentList";
import AssessmentDetail from "./pages/materiality/AssessmentDetail";
import AssessmentOverview from "./pages/materiality/AssessmentOverview";
import StakeholderGroups from "@/pages/materiality/StakeholderGroups";
import AssessmentStakeholders from "./pages/materiality/AssessmentStakeholders";
import SurveyManager from "@/pages/materiality/SurveyManager";
import SurveyDistribution from "@/pages/materiality/SurveyDistribution";
import PublicSurvey from "./pages/materiality/PublicSurvey";
import SurveyThankYou from "./pages/materiality/SurveyThankYou";
const MaterialityMatrixPage = lazy(
  () => import("./pages/materiality/MaterialityMatrixPage"),
);

//Datapoints
import DatapointList from "./pages/datapoints/DatapointList";
import DatapointDetail from "./pages/datapoints/DatapointDetail";
import DatapointCreate from "./pages/datapoints/DatapointCreate";
import DatapointTableDefinitionManager from "./pages/datapoints/DPtabledefinitionmanager";
import UnitFamilyManager from "./pages/datapoints/Unitfamilymanager";
import UnitManager from "./pages/datapoints/Unitmanager";
import DatapointEdit from "./pages/datapoints/Datapointedit";
import CategoryManager from "./pages/datapoints/Categorymanager";
import DatapointOptionsManager from "./pages/datapoints/DatapointOptionsManager";
import GoalsList from "./pages/targets/GoalsList";
import GoalDetail from "./pages/targets/GoalDetail";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Navigate to="/" replace />} />

        <Route path="/goals" element={<ProtectedRoute permission="target.set"><GoalsList /></ProtectedRoute>} />
        <Route path="/goals/:id" element={<ProtectedRoute permission="target.set"><GoalDetail /></ProtectedRoute>} />

        <Route
          path="/dashboard"
          element={<Navigate to="/accounts/dashboard/" replace />}
        />

        <Route
          path="/accounts/dashboard/"
          element={
            <ProtectedRoute permission="dashboard.view">
              <PlatformAdminDashboard />
            </ProtectedRoute>
          }
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
          element={
            <ProtectedRoute permission="user.edit">
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
            <ProtectedRoute permission="materiality.view">
              <ReportingPeriodForm />
            </ProtectedRoute>
          }
        />

        {/*Materiality */}

        <Route
          path="/materiality/topics"
          element={
            <ProtectedRoute permission="reporting_period.edit">
              <TopicLibrary />
            </ProtectedRoute>
          }
        />
{/* DataPoints Routes */}


<Route
  path="/datapoints"
  element={
    <ProtectedRoute>
      <DatapointList />
    </ProtectedRoute>
  }
/>

<Route
  path="/datapoints/create"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <DatapointCreate />
    </ProtectedRoute>
  }
/>

<Route
  path="/datapoints/:id/edit"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <DatapointEdit />
    </ProtectedRoute>
  }
/>

<Route
  path="/datapoints/:id"
  element={
    <ProtectedRoute>
      <DatapointDetail />
    </ProtectedRoute>
  }
/>

{/* ==================================================
    DATAPOINT — OPTIONS (SELECT datapoints)
    Contextual to a single datapoint; linked from the
    datapoint detail/edit page rather than the sidebar.
================================================== */}
<Route
  path="/datapoints/:id/options"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <DatapointOptionsManager />
    </ProtectedRoute>
  }
/>

{/* ==================================================
    DATAPOINT — TABLE DEFINITION (TABLE datapoints)
================================================== */}
<Route
  path="/datapoints/:id/table-definition"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <DatapointTableDefinitionManager />
    </ProtectedRoute>
  }
/>

{/* ==================================================
    UNIT FAMILIES
================================================== */}
<Route
  path="/units/families"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <UnitFamilyManager />
    </ProtectedRoute>
  }
/>

{/* ==================================================
    UNITS
================================================== */}
<Route
  path="/units"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <UnitManager />
    </ProtectedRoute>
  }
/>


{/* Category */}

<Route
  path="/datapoints/categories"
  element={
    <ProtectedRoute permission="datapoint.manage">
      <CategoryManager />
    </ProtectedRoute>
  }
/>

{/* Materiality */}



        <Route
          path="/materiality/assessments"
          element={
            <ProtectedRoute permission="materiality.view">
              <AssessmentList />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:assessmentId"
          element={
            <ProtectedRoute permission="materiality.view">
              <AssessmentOverview />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:id/select-topics"
          element={
            <ProtectedRoute permission="materiality.view">
              <AssessmentDetail />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:id/groups"
          element={
            <ProtectedRoute permission="materiality.view">
              <StakeholderGroups />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:id/stakeholders"
          element={
            <ProtectedRoute permission="materiality.view">
              <AssessmentStakeholders />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:id/survey"
          element={
            <ProtectedRoute permission="materiality.view">
              <SurveyManager />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:id/survey/distribution"
          element={
            <ProtectedRoute permission="materiality.view">
              <SurveyDistribution />
            </ProtectedRoute>
          }
        />

        <Route path="/survey/:token" element={<PublicSurvey />} />

        <Route path="/survey/:token/thank-you" element={<SurveyThankYou />} />

        <Route
          path="/materiality/assessments/:assessmentId/scoring"
          element={
            <ProtectedRoute permission="materiality.view">
              <ScoringDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/materiality/assessments/:assessmentId/matrix"
          element={
            <ProtectedRoute permission="materiality.view">
              <Suspense
                fallback={
                  <div className="p-6 text-sm text-muted-foreground">
                    Loading results and matrix…
                  </div>
                }
              >
                <MaterialityMatrixPage />
              </Suspense>
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster position="top-center" richColors />
    </BrowserRouter>
  );
}
