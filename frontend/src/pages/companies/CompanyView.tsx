import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import AppShell from "@/components/layout/AppShell";
import CompanyApi from "@/api/companies/CompanyApi";
import type { Company } from "@/types/company";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  Building2,
  Mail,
  Phone,
  Globe,
  MapPin,
  Calendar,
  User,
  Landmark,
  TrendingUp,
  Users,
  Clock3,
  FileText,
} from "lucide-react";

export default function CompanyProfile() {
  const navigate = useNavigate();

  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);

  const formatDate = (value?: string | null) => {
    if (!value) return "-";
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(value));
  };

  const formatCurrency = (value?: string | number | null) => {
    if (!value) return "-";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(value));
  };

  const formatMonth = (month?: number) => {
    if (!month) return "-";
    return new Date(2025, month - 1, 1).toLocaleString("en-IN", {
      month: "long",
    });
  };

  useEffect(() => {
    let cancelled = false;

    async function fetchProfile() {
      try {
        const response = await CompanyApi.getProfile();
        if (cancelled) return;
        setCompany(response.data);
      } catch (error) {
        // A fresh local deployment may not have its singleton company profile
        // configured yet. That is an intentional empty state, not a failed
        // page load.
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          return;
        }
        console.error(error);
        if (!cancelled) {
          toast.error("Unable to load company profile.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchProfile();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <AppShell
        title="Company Profile"
        description="Loading company information..."
      >
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="h-56 animate-pulse rounded-2xl bg-[#F3F4F6]" />
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="h-96 animate-pulse rounded-2xl bg-[#F3F4F6]" />
            <div className="h-96 animate-pulse rounded-2xl bg-[#F3F4F6]" />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="h-80 animate-pulse rounded-2xl bg-[#F3F4F6]" />
            <div className="h-80 animate-pulse rounded-2xl bg-[#F3F4F6]" />
          </div>
        </div>
      </AppShell>
    );
  }

  if (!company) {
    return (
      <AppShell title="Company Profile" description="View company information.">
        <Card className="border border-[#E5E7EB] bg-white">
          <CardContent className="flex flex-col items-center justify-center py-24">
            <Building2 className="mb-4 h-16 w-16 text-[#CBD5E1]" />
            <h2 className="text-xl font-semibold text-[#1F2937]">
              Company Profile Not Found
            </h2>
            <p className="mt-2 text-[#6B7280]">
              No company profile has been configured yet.
            </p>
          </CardContent>
        </Card>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Company Profile"
      description="View company information aligned with BRSR and GRI disclosures."
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <Card className="border border-[#E5E7EB] bg-white">
          <CardContent className="p-6 md:p-8">
            <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
              <div className="flex h-32 w-32 shrink-0 items-center justify-center overflow-hidden rounded-3xl border border-[#E5E7EB] bg-[#EEF2FF]">
                {company.company_logo ? (
                  <img
                    src={company.company_logo}
                    alt={company.company_name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <Building2 className="h-12 w-12 text-[#4A3FD6]" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-3">
                      <h1 className="break-words text-3xl font-bold text-[#1F2937]">
                        {company.company_name}
                      </h1>
                      <Badge variant={company.is_active ? "success" : "inactive"}>
                        {company.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                    <p className="mt-3 max-w-3xl break-words leading-7 text-[#6B7280]">
                      {company.about_company || "No company description available."}
                    </p>
                  </div>

                  <Button
                    className="shrink-0 bg-[#4A3FD6] hover:bg-[#3C32B8]"
                    onClick={() => navigate("/company/profile/edit")}
                  >
                    Edit Company
                  </Button>
                </div>

                <div className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wide text-[#9CA3AF]">
                      Company Code
                    </p>
                    <p className="mt-1 break-words font-semibold text-[#111827]">
                      {company.company_code || "-"}
                    </p>
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-[#9CA3AF]">
                        CIN
                      </p>
                      <Badge variant="info">BRSR</Badge>
                    </div>
                    <p className="mt-1 break-words font-semibold">
                      {company.cin_number || "-"}
                    </p>
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-[#9CA3AF]">
                        GST
                      </p>
                      <Badge variant="info">BRSR</Badge>
                    </div>
                    <p className="mt-1 break-words font-semibold">
                      {company.gst_number || "-"}
                    </p>
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wide text-[#9CA3AF]">
                      Financial Year
                    </p>
                    <p className="mt-1 font-semibold">
                      {formatMonth(company.financial_year_start_month)}
                    </p>
                  </div>
                </div>

                <Separator className="my-8" />

                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-medium text-[#6B7280]">
                    Applicable Disclosure Frameworks
                  </span>
                  <Badge variant="system">GRI 2</Badge>
                  <Badge variant="info">BRSR Section A</Badge>
                  {company.listed_company && (
                    <Badge variant="success">Listed Company</Badge>
                  )}
                  {company.stock_exchanges && (
                    <Badge variant="outline">{company.stock_exchanges}</Badge>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="border border-[#E5E7EB] bg-white">
            <CardHeader className="p-6 pb-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>GRI 2 — Organizational Profile</CardTitle>
                  <CardDescription>
                    General organization disclosures required under GRI 2.
                  </CardDescription>
                </div>
                <Badge variant="system" className="shrink-0">
                  GRI 2
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-6 p-6 pt-0">
              <div className="flex items-start gap-4">
                <Calendar className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Date of Incorporation</p>
                  <p className="mt-1 font-semibold">
                    {formatDate(company.date_of_incorporation)}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <Landmark className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Ownership Form</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.ownership_form || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <MapPin className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Registered Country</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.country_name || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div>
                <p className="mb-2 text-sm text-[#6B7280]">About Organization</p>
                <p className="break-words leading-7 text-[#374151]">
                  {company.about_company || "-"}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-[#E5E7EB] bg-white">
            <CardHeader className="p-6 pb-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>BRSR Section A</CardTitle>
                  <CardDescription>
                    Statutory and business disclosure information.
                  </CardDescription>
                </div>
                <Badge variant="info" className="shrink-0">
                  BRSR
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-6 p-6 pt-0">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#6B7280]">Listed Company</span>
                <Badge variant={company.listed_company ? "success" : "inactive"}>
                  {company.listed_company ? "Yes" : "No"}
                </Badge>
              </div>

              <Separator />

              <div className="flex items-center justify-between gap-3">
                <span className="text-[#6B7280]">Stock Exchange</span>
                <span className="break-words text-right font-semibold">
                  {company.stock_exchanges || "-"}
                </span>
              </div>

              <Separator />

              <div className="flex items-center justify-between gap-3">
                <span className="text-[#6B7280]">Paid-up Capital</span>
                <span className="font-semibold">
                  {formatCurrency(company.paid_up_capital)}
                </span>
              </div>

              <Separator />

              <div className="flex items-center justify-between gap-3">
                <span className="text-[#6B7280]">Annual Turnover</span>
                <span className="font-semibold">
                  {formatCurrency(company.turnover)}
                </span>
              </div>

              <Separator />

              <div className="flex items-center justify-between gap-3">
                <span className="text-[#6B7280]">Employee Count</span>
                <span className="font-semibold">
                  {company.employee_count?.toLocaleString("en-IN") ?? "-"}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="border border-[#E5E7EB] bg-white">
            <CardHeader className="p-6 pb-4">
              <CardTitle>Contact Information</CardTitle>
              <CardDescription>
                Primary contact details for the organization.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 p-6 pt-0">
              <div className="flex items-start gap-4">
                <User className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Contact Person</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.contact_person || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <Mail className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Email Address</p>
                  <p className="mt-1 break-all font-semibold">
                    {company.email || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <Phone className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Mobile Number</p>
                  <p className="mt-1 font-semibold">
                    {company.mobile_number || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <Globe className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Website</p>
                  {company.website ? (
                    <a
                      href={company.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block break-all font-semibold text-[#4A3FD6] hover:underline"
                    >
                      {company.website}
                    </a>
                  ) : (
                    <p className="mt-1 font-semibold">Not Provided</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-[#E5E7EB] bg-white">
            <CardHeader className="p-6 pb-4">
              <CardTitle>Address Information</CardTitle>
              <CardDescription>
                Registered and corporate office details.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 p-6 pt-0">
              <div className="flex items-start gap-4">
                <MapPin className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Registered Address</p>
                  <p className="mt-1 break-words leading-7">
                    {company.registered_address || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-start gap-4">
                <Building2 className="mt-1 h-5 w-5 shrink-0 text-[#4A3FD6]" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#6B7280]">Corporate Address</p>
                  <p className="mt-1 break-words leading-7">
                    {company.corporate_address || "-"}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="grid gap-6 md:grid-cols-3">
                <div className="min-w-0">
                  <p className="text-sm text-[#6B7280]">Country</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.country_name || "-"}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-[#6B7280]">State</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.state_name || "-"}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-[#6B7280]">City</p>
                  <p className="mt-1 break-words font-semibold">
                    {company.city_name || "-"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="border border-[#E5E7EB] bg-white">
          <CardHeader className="p-6 pb-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Financial Information</CardTitle>
                <CardDescription>Organization financial disclosures.</CardDescription>
              </div>
              <Badge variant="info" className="shrink-0">
                BRSR
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-6 pt-0">
            <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-4">
              <div className="min-w-0">
                <TrendingUp className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Paid-up Capital</p>
                <p className="mt-2 break-words text-lg font-semibold">
                  {formatCurrency(company.paid_up_capital)}
                </p>
              </div>

              <div className="min-w-0">
                <TrendingUp className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Annual Turnover</p>
                <p className="mt-2 break-words text-lg font-semibold">
                  {formatCurrency(company.turnover)}
                </p>
              </div>

              <div className="min-w-0">
                <Users className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Employees</p>
                <p className="mt-2 text-lg font-semibold">
                  {company.employee_count?.toLocaleString("en-IN") ?? "-"}
                </p>
              </div>

              <div className="min-w-0">
                <Calendar className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Financial Year</p>
                <p className="mt-2 text-lg font-semibold">
                  {formatMonth(company.financial_year_start_month)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-[#E5E7EB] bg-white">
          <CardHeader className="p-6 pb-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>System Information</CardTitle>
                <CardDescription>
                  Internal record metadata and lifecycle information.
                </CardDescription>
              </div>
              <Badge variant="secondary" className="shrink-0">
                Internal
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-6 pt-0">
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              <div className="min-w-0 rounded-xl border border-[#EEF2F7] bg-[#FAFBFD] p-5">
                <Clock3 className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Created On</p>
                <p className="mt-2 font-semibold text-[#111827]">
                  {formatDate(company.created_at)}
                </p>
              </div>

              <div className="min-w-0 rounded-xl border border-[#EEF2F7] bg-[#FAFBFD] p-5">
                <Clock3 className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Last Updated</p>
                <p className="mt-2 font-semibold text-[#111827]">
                  {formatDate(company.updated_at)}
                </p>
              </div>

              <div className="min-w-0 rounded-xl border border-[#EEF2F7] bg-[#FAFBFD] p-5">
                <FileText className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Company ID</p>
                <p className="mt-2 break-all font-medium text-[#111827]">
                  {company.id}
                </p>
              </div>

              <div className="min-w-0 rounded-xl border border-[#EEF2F7] bg-[#FAFBFD] p-5">
                <Building2 className="mb-3 h-6 w-6 text-[#4A3FD6]" />
                <p className="text-sm text-[#6B7280]">Current Status</p>
                <div className="mt-3">
                  <Badge variant={company.is_active ? "success" : "inactive"}>
                    {company.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
