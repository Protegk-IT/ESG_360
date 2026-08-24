import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { toast } from "sonner";

import CompanyApi from "@/api/companies/CompanyApi";
import { getApiErrorMessage } from "@/services/errors";

import type {
  CompanyPayload,
  Country,
  State,
  City,
} from "@/types/company";

import AppShell from "@/components/layout/AppShell";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";

import { Label } from "@/components/ui/label";

import { Textarea } from "@/components/ui/textarea";

import { Button } from "@/components/ui/button";

import { Switch } from "@/components/ui/switch";

import { Checkbox } from "@/components/ui/checkbox";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Separator } from "@/components/ui/separator";

export default function CompanyForm() {

  const navigate =
    useNavigate();

  const { id } =
    useParams();

  /* ==========================================================
      MASTER DATA
  ========================================================== */

  const [countries, setCountries] =
    useState<Country[]>([]);

  const [states, setStates] =
    useState<State[]>([]);

  const [cities, setCities] =
    useState<City[]>([]);

  /* ==========================================================
      UI STATES
  ========================================================== */

  const [loading, setLoading] =
    useState(false);

  const [sameAsRegistered, setSameAsRegistered] =
    useState(false);


  /* ==========================================================
      FORM STATE
  ========================================================== */

  const [formData, setFormData] =
    useState<CompanyPayload>({

      /* ==========================
         Basic Information
      ========================== */

      company_logo: null,

      company_name: "",

      company_code: "",

      about_company: "",

      date_of_incorporation: "",

      /* ==========================
         Legal Information
      ========================== */

      cin_number: "",

      gst_number: "",

      listed_company: false,

      stock_exchanges: "",

      paid_up_capital: "",

      turnover: "",

      ownership_form: "",

      /* ==========================
         Address
      ========================== */

      registered_address: "",

      corporate_address: "",

      country: "",

      state: "",

      city: "",

      /* ==========================
         Contact
      ========================== */

      contact_person: "",

      email: "",

      mobile_number: "",

      website: "",

      /* ==========================
         Reporting
      ========================== */

      employee_count: 0,

      financial_year_start_month: 4,

      /* ==========================
         Status
      ========================== */

      is_active: true,

    });

      /* ==========================================================
      UPDATE FIELD
  ========================================================== */

  const updateField = <
    K extends keyof CompanyPayload
  >(
    key: K,
    value: CompanyPayload[K]
  ) => {

    setFormData((prev) => ({

      ...prev,

      [key]: value,

    }));

  };

  /* ==========================================================
      LOAD MASTER DATA
  ========================================================== */

  const loadStates =
    async (
      countryId: string
    ) => {

      if (!countryId) {

        setStates([]);

        setCities([]);

        return;

      }

      try {

        const response =
          await CompanyApi.getStates(
            countryId
          );

        setStates(
          response.data
        );

      } catch {

        toast.error(
          "Unable to load states."
        );

      }

    };

  const loadCities =
    async (
      stateId: string
    ) => {

      if (!stateId) {

        setCities([]);

        return;

      }

      try {

        const response =
          await CompanyApi.getCities(
            stateId
          );

        setCities(
          response.data
        );

      } catch {

        toast.error(
          "Unable to load cities."
        );

      }

    };

  /* ==========================================================
      LOAD COMPANY (EDIT)
  ========================================================== */
  /* ==========================================================
      INITIAL LOAD
  ========================================================== */
  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        setLoading(true);
        const [countriesResponse, companyResponse] = await Promise.all([
          CompanyApi.getCountries(),
          CompanyApi.getProfile(),
        ]);
        const company = companyResponse.data;
        const [statesResponse, citiesResponse] = await Promise.all([
          company.country ? CompanyApi.getStates(company.country) : Promise.resolve({ data: [] as State[] }),
          company.state ? CompanyApi.getCities(company.state) : Promise.resolve({ data: [] as City[] }),
        ]);

        if (cancelled) return;
        setCountries(countriesResponse.data);
        setStates(statesResponse.data);
        setCities(citiesResponse.data);
        setFormData({
          company_logo: null,
          company_name: company.company_name ?? "", company_code: company.company_code ?? "",
          about_company: company.about_company ?? "", date_of_incorporation: company.date_of_incorporation ?? "",
          cin_number: company.cin_number ?? "", gst_number: company.gst_number ?? "",
          listed_company: company.listed_company, stock_exchanges: company.stock_exchanges ?? "",
          paid_up_capital: company.paid_up_capital ?? "", turnover: company.turnover ?? "",
          ownership_form: company.ownership_form ?? "", registered_address: company.registered_address ?? "",
          corporate_address: company.corporate_address ?? "", country: company.country ?? "",
          state: company.state ?? "", city: company.city ?? "", contact_person: company.contact_person ?? "",
          email: company.email ?? "", mobile_number: company.mobile_number ?? "", website: company.website ?? "",
          employee_count: company.employee_count ?? 0, financial_year_start_month: company.financial_year_start_month ?? 4,
          is_active: company.is_active,
        });
      } catch (error) {
        console.error(error);
        if (!cancelled) toast.error("Unable to load company.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadInitialData();
    return () => { cancelled = true; };
  }, []);

    /* ==========================================================
      SAME AS REGISTERED ADDRESS
  ========================================================== */

  useEffect(() => {

    if (!sameAsRegistered)
      return;

    updateField(
      "corporate_address",
      formData.registered_address
    );

  }, [
    sameAsRegistered,
    formData.registered_address,
  ]);

  /* ==========================================================
      SUBMIT
  ========================================================== */

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {

    e.preventDefault();

    setLoading(true);


    try {

      const body =
        new FormData();

      Object.entries(
        formData
      ).forEach(
        ([key, value]) => {

          /* ==========================
             FILE
          ========================== */

          if (
            key ===
            "company_logo"
          ) {

            if (
              value instanceof File
            ) {

              body.append(
                key,
                value
              );

            }

            return;

          }

          /* ==========================
             BOOLEAN
          ========================== */

          if (
            typeof value ===
            "boolean"
          ) {

            body.append(
              key,
              String(value)
            );

            return;

          }

          /* ==========================
             NUMBER
          ========================== */

          if (
            typeof value ===
            "number"
          ) {

            body.append(
              key,
              String(value)
            );

            return;

          }

          body.append(
            key,
            value ?? ""
          );

        }
      );

      await CompanyApi.update(body);

toast.success(
  "Company updated successfully."
);
      navigate(
        "/companies"
      );

    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, "Unable to update company."));
    } finally {

      setLoading(false);

    }

  };

  /* ==========================================================
      UI
  ========================================================== */

  return (
<AppShell
  title="Edit Company"
  description="Update company information."
>
  <form onSubmit={handleSubmit} className="space-y-6 px-4 md:px-6 lg:px-8">
    {/* ==========================================================
        PART 1 - BASIC INFORMATION
    ========================================================== */}
    <Card>
      <CardHeader className="px-6 py-6">
        <CardTitle>Basic Information</CardTitle>
        <CardDescription>
          Enter the basic company information.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Company Logo */}
          <div className="space-y-2 lg:col-span-2">
            <Label htmlFor="company_logo">Company Logo</Label>

            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  document.getElementById("company_logo")?.click()
                }
              >
                Choose File
              </Button>

              <span className="text-sm text-muted-foreground">
                {formData.company_logo
                  ? formData.company_logo.name
                  : "No file selected"}
              </span>

              <input
                id="company_logo"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) =>
                  updateField("company_logo", e.target.files?.[0] ?? null)
                }
              />
            </div>
          </div>

          {/* Company Name */}
          <div className="space-y-2">
            <Label>Company Name</Label>
            <Input
              value={formData.company_name}
              onChange={(e) => updateField("company_name", e.target.value)}
            />
          </div>

          {/* Company Code */}
          <div className="space-y-2">
            <Label>Company Code</Label>
            <Input
              value={formData.company_code}
              onChange={(e) => updateField("company_code", e.target.value)}
            />
          </div>

          {/* Date of Incorporation */}
          <div className="space-y-2">
            <Label>Date of Incorporation</Label>
            <Input
              type="date"
              value={formData.date_of_incorporation}
              onChange={(e) =>
                updateField("date_of_incorporation", e.target.value)
              }
            />
          </div>

          {/* About Company */}
          <div className="space-y-2 lg:col-span-2">
            <Label>About Company</Label>
            <Textarea
              rows={5}
              value={formData.about_company}
              onChange={(e) => updateField("about_company", e.target.value)}
            />
          </div>
        </div>
      </CardContent>
    </Card>

    {/* ==========================================================
        PART 2 - LEGAL & COMPLIANCE
    ========================================================== */}
    <Card>
      <CardHeader className="px-6 py-6">
        <CardTitle>Legal & Compliance</CardTitle>
        <CardDescription>
          Configure statutory and financial information.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 px-6 py-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* CIN Number */}
          <div className="space-y-2">
            <Label>CIN Number</Label>
            <Input
              value={formData.cin_number}
              onChange={(e) => updateField("cin_number", e.target.value)}
            />
          </div>

          {/* GST Number */}
          <div className="space-y-2">
            <Label>GST Number</Label>
            <Input
              value={formData.gst_number}
              onChange={(e) => updateField("gst_number", e.target.value)}
            />
          </div>

    <div className="flex items-center justify-between rounded-lg border p-4">

  <div>

    <Label>Listed Company</Label>

    <p className="text-sm text-muted-foreground">
      Enable if the company is publicly listed.
    </p>

  </div>

  <Switch
    checked={formData.listed_company}
    onCheckedChange={(value) =>
      updateField(
        "listed_company",
        value
      )
    }
  />

</div>

<div className="space-y-2">

  <Label>Stock Exchange(s)</Label>

  <Input
    placeholder="NSE, BSE"
    disabled={!formData.listed_company}
    value={formData.stock_exchanges}
    onChange={(e) =>
      updateField(
        "stock_exchanges",
        e.target.value
      )
    }
  />

</div>
          {/* Ownership Form */}
          <div className="space-y-2">
            <Label>Ownership Form</Label>
            <Select
              value={formData.ownership_form}
              onValueChange={(value) => updateField("ownership_form", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select Ownership" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Private">Private Limited</SelectItem>
                <SelectItem value="Public">Public Limited</SelectItem>
                <SelectItem value="Government">Government</SelectItem>
                <SelectItem value="Partnership">Partnership</SelectItem>
                <SelectItem value="LLP">LLP</SelectItem>
                <SelectItem value="Proprietorship">
                  Proprietorship
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Paid-up Capital */}
          <div className="space-y-2">
            <Label>Paid-up Capital</Label>
            <Input
              type="number"
              value={formData.paid_up_capital}
              onChange={(e) =>
                updateField("paid_up_capital", e.target.value)
              }
            />
          </div>

          {/* Annual Turnover */}
          <div className="space-y-2">
            <Label>Annual Turnover</Label>
            <Input
              type="number"
              value={formData.turnover}
              onChange={(e) => updateField("turnover", e.target.value)}
            />
          </div>
        </div>
      </CardContent>
    </Card>

    {/* ==========================================================
        PART 3 - ADDRESS INFORMATION
    ========================================================== */}
    <Card>
      <CardHeader className="px-6 py-6">
        <CardTitle>Address Information</CardTitle>
        <CardDescription>
          Configure registered and corporate office details.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-8 px-6 py-6">
        {/* REGISTERED OFFICE */}
        <div className="space-y-6">
          <h4 className="text-sm font-semibold">Registered Office</h4>

          <div className="space-y-2">
            <Label>Registered Address</Label>
            <Textarea
              rows={4}
              value={formData.registered_address}
              onChange={(e) =>
                updateField("registered_address", e.target.value)
              }
            />
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {/* Country */}
            <div className="space-y-2">
              <Label>Country</Label>
              <Select
                value={formData.country}
                onValueChange={(value) => {
                  // Radix can emit an empty value while its options mount;
                  // that must not erase a hydrated company location.
                  if (!value) return;
                  setFormData((previous) => ({
                    ...previous,
                    country: value,
                    state: "",
                    city: "",
                  }));
                  void loadStates(value);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Country" />
                </SelectTrigger>
                <SelectContent>
                  {countries.map((country) => (
                    <SelectItem key={country.id} value={country.id}>
                      {country.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* State */}
            <div className="space-y-2">
              <Label>State</Label>
              <Select
                value={formData.state}
                onValueChange={(value) => {
                  if (!value) return;
                  setFormData((previous) => ({ ...previous, state: value, city: "" }));
                  void loadCities(value);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select State" />
                </SelectTrigger>
                <SelectContent>
                  {states.map((state) => (
                    <SelectItem key={state.id} value={state.id}>
                      {state.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* City */}
            <div className="space-y-2">
              <Label>City</Label>
              <Select
                value={formData.city}
                onValueChange={(value) => {
                  if (value) updateField("city", value);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select City" />
                </SelectTrigger>
                <SelectContent>
                  {cities.map((city) => (
                    <SelectItem key={city.id} value={city.id}>
                      {city.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <Separator />

        {/* CORPORATE OFFICE */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">Corporate Office</h4>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="same_address"
                checked={sameAsRegistered}
                onCheckedChange={(checked) => {
                  const value = checked === true;
                  setSameAsRegistered(value);
                  if (value) {
                    updateField(
                      "corporate_address",
                      formData.registered_address
                    );
                  }
                }}
              />
              <Label htmlFor="same_address">Same as Registered Address</Label>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Corporate Address</Label>
            <Textarea
              rows={4}
              disabled={sameAsRegistered}
              value={formData.corporate_address}
              onChange={(e) =>
                updateField("corporate_address", e.target.value)
              }
            />
          </div>
        </div>
      </CardContent>
    </Card>

    {/* ==========================================================
        PART 4 - CONTACT & REPORTING
    ========================================================== */}
    <Card>
      <CardHeader className="px-6 py-6">
        <CardTitle>Contact & Reporting</CardTitle>
        <CardDescription>
          Configure primary contact and reporting information.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-8 px-6 py-6">
        {/* CONTACT INFORMATION */}
        <div className="space-y-6">
          <h4 className="text-sm font-semibold">Contact Information</h4>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Contact Person</Label>
              <Input
                value={formData.contact_person}
                onChange={(e) =>
                  updateField("contact_person", e.target.value)
                }
              />
            </div>

            <div className="space-y-2">
              <Label>Email Address</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => updateField("email", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Mobile Number</Label>
              <Input
                value={formData.mobile_number}
                onChange={(e) =>
                  updateField("mobile_number", e.target.value)
                }
              />
            </div>

            <div className="space-y-2">
              <Label>Website</Label>
              <Input
                placeholder="https://example.com"
                value={formData.website}
                onChange={(e) => updateField("website", e.target.value)}
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* REPORTING */}
        <div className="space-y-6">
          <h4 className="text-sm font-semibold">Reporting Configuration</h4>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Employee Count</Label>
              <Input
                type="number"
                value={formData.employee_count}
                onChange={(e) =>
                  updateField("employee_count", Number(e.target.value))
                }
              />
            </div>

            <div className="space-y-2">
              <Label>Financial Year Start Month</Label>
              <Select
                value={String(formData.financial_year_start_month)}
                onValueChange={(value) =>
                  updateField("financial_year_start_month", Number(value))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Month" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">January</SelectItem>
                  <SelectItem value="2">February</SelectItem>
                  <SelectItem value="3">March</SelectItem>
                  <SelectItem value="4">April</SelectItem>
                  <SelectItem value="5">May</SelectItem>
                  <SelectItem value="6">June</SelectItem>
                  <SelectItem value="7">July</SelectItem>
                  <SelectItem value="8">August</SelectItem>
                  <SelectItem value="9">September</SelectItem>
                  <SelectItem value="10">October</SelectItem>
                  <SelectItem value="11">November</SelectItem>
                  <SelectItem value="12">December</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <Separator />

        {/* STATUS */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label>Active Company</Label>
            <p className="text-sm text-muted-foreground">
              Inactive companies cannot access the ESG platform.
            </p>
          </div>
          <Switch
            checked={formData.is_active}
            onCheckedChange={(value) => updateField("is_active", value)}
          />
        </div>
      </CardContent>
    </Card>

    {/* ==========================================================
        ACTIONS
    ========================================================== */}
    <Card>
      <CardContent className="flex items-center justify-end gap-3 px-6 py-6">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate("/companies")}
        >
          Cancel
        </Button>

        <Button type="submit" disabled={loading}>
          {loading
            ? id
              ? "Updating..."
              : "Creating..."
            : id
            ? "Update Company"
            : "Save Changes"}
        </Button>
      </CardContent>
    </Card>
  </form>
</AppShell>

  );

}
