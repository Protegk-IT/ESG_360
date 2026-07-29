import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-10 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">ESG360</p>
            <h1 className="mt-2 text-3xl font-semibold">Operations dashboard</h1>
            <p className="mt-1 text-sm text-slate-300">Manage authentication, companies, and organizations from one place.</p>
          </div>
          <nav className="flex flex-wrap gap-3">
            <Link className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950" to="/companies">
              Companies
            </Link>
            <Link className="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold" to="/organizations">
              Organizations
            </Link>
          </nav>
        </header>

        <section className="grid gap-6 md:grid-cols-3">
          <Link to="/companies" className="rounded-3xl border border-white/10 bg-slate-900 p-6 transition hover:-translate-y-1 hover:border-cyan-400/60">
            <h2 className="text-xl font-semibold">Companies</h2>
            <p className="mt-2 text-sm text-slate-300">Create countries, states, cities, and company profiles.</p>
          </Link>
          <Link to="/organizations" className="rounded-3xl border border-white/10 bg-slate-900 p-6 transition hover:-translate-y-1 hover:border-cyan-400/60">
            <h2 className="text-xl font-semibold">Organizations</h2>
            <p className="mt-2 text-sm text-slate-300">Create organizations, departments, and facilities linked to companies.</p>
          </Link>
          <div className="rounded-3xl border border-white/10 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Auth</h2>
            <p className="mt-2 text-sm text-slate-300">Login uses the backend accounts app and session-based authentication.</p>
          </div>
        </section>
      </div>
    </div>
  );
}
