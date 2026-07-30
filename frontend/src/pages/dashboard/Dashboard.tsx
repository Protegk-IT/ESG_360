import { Link } from "react-router-dom";
import AppShell from "../../components/layout/AppShell";

export default function Dashboard() {
  return (
    <AppShell
      title="Welcome to ESG360"
      description="Choose a module to continue."
      showLogoutButton
    >
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Link
            to="/companies"
            className="rounded-lg border bg-white p-6 shadow-sm transition hover:border-orange-300"
          >
            <h2 className="text-lg font-semibold text-gray-900">Companies</h2>
            <p className="mt-2 text-sm text-gray-600">
              Add and manage company information.
            </p>
          </Link>

          <Link
            to="/organizations"
            className="rounded-lg border bg-white p-6 shadow-sm transition hover:border-orange-300"
          >
            <h2 className="text-lg font-semibold text-gray-900">Organizations</h2>
            <p className="mt-2 text-sm text-gray-600">
              View organization structure details.
            </p>
          </Link>

          <Link
            to="/departments"
            className="rounded-lg border bg-white p-6 shadow-sm transition hover:border-orange-300"
          >
            <h2 className="text-lg font-semibold text-gray-900">Departments</h2>
            <p className="mt-2 text-sm text-gray-600">
              Access department-related pages.
            </p>
          </Link>

          <Link
            to="/facilities"
            className="rounded-lg border bg-white p-6 shadow-sm transition hover:border-orange-300"
          >
            <h2 className="text-lg font-semibold text-gray-900">Facilities</h2>
            <p className="mt-2 text-sm text-gray-600">
              Access facility-related pages.
            </p>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
