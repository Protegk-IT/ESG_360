import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../services/api";
import type { Organization } from "../../types/organization";

export default function OrganizationsPage() {
  const [items, setItems] = useState<Organization[]>([]);
  const [form, setForm] = useState({ company: "", name: "", organization_code: "" });

  useEffect(() => {
    api.get("/organizations/organizations/").then((r) => setItems(r.data));
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/organizations/organizations/", form);
  };

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Organizations</h1>
            <p className="text-sm text-slate-300">Organizations, departments, and facilities map to the company structure.</p>
          </div>
          <Link to="/dashboard" className="text-sm text-cyan-300">Back to dashboard</Link>
        </div>
        <form onSubmit={submit} className="mb-8 grid gap-3 rounded-3xl border border-white/10 bg-white/5 p-6 md:grid-cols-4">
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Company UUID" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Organization code" value={form.organization_code} onChange={(e) => setForm({ ...form, organization_code: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3 md:col-span-2" placeholder="Organization name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <button className="rounded-xl bg-cyan-400 px-4 py-3 font-semibold text-slate-950 md:col-span-4">Create organization</button>
        </form>
        <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-xl font-semibold">Organizations</h2>
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-2xl bg-slate-900 p-4">
                <div className="font-medium">{item.name}</div>
                <div className="text-sm text-slate-400">{item.organization_code}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
