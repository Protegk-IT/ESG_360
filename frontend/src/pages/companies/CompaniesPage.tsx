import { FormEvent, useEffect, useState } from "react";
import api from "../../services/api";
import type { Company, Country } from "../../types/company";
import { Link } from "react-router-dom";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [form, setForm] = useState({ company_code: "", company_name: "", contact_person: "", email: "", mobile_number: "" });

  useEffect(() => {
    api.get("/companies/companies/").then((r) => setCompanies(r.data));
    api.get("/companies/countries/").then((r) => setCountries(r.data));
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/companies/companies/", form);
  };

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Companies</h1>
            <p className="text-sm text-slate-300">Master data for countries, states, cities, and companies.</p>
          </div>
          <Link to="/dashboard" className="text-sm text-cyan-300">Back to dashboard</Link>
        </div>
        <form onSubmit={submit} className="mb-8 grid gap-3 rounded-3xl border border-white/10 bg-white/5 p-6 md:grid-cols-5">
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Code" value={form.company_code} onChange={(e) => setForm({ ...form, company_code: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3 md:col-span-2" placeholder="Company name" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Contact person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="rounded-xl bg-slate-900 px-4 py-3" placeholder="Mobile" value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} />
          <button className="rounded-xl bg-cyan-400 px-4 py-3 font-semibold text-slate-950 md:col-span-5">Create company</button>
        </form>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="mb-4 text-xl font-semibold">Companies</h2>
            <div className="space-y-3">
              {companies.map((company) => (
                <div key={company.id} className="rounded-2xl bg-slate-900 p-4">
                  <div className="font-medium">{company.company_name}</div>
                  <div className="text-sm text-slate-400">{company.company_code} · {company.email}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="mb-4 text-xl font-semibold">Countries</h2>
            <div className="space-y-3">
              {countries.map((country) => (
                <div key={country.id} className="rounded-2xl bg-slate-900 p-4">
                  <div className="font-medium">{country.name}</div>
                  <div className="text-sm text-slate-400">{country.iso_code}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
