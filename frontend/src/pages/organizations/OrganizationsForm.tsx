import { useCallback,useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { toast } from "sonner";

import OrganizationApi from "@/api/organizations/OrganizationApi";
import CompanyApi from "@/api/companies/CompanyApi";
import { getApiErrorMessage } from "@/services/errors";

import type {
  OrgNode,
  OrgNodePayload,
  OrgNodeType,
  ConsolidationMethod,
} from "@/types/organization";
import type { Country, State, City } from "@/types/company";

import AppShell from "@/components/layout/AppShell";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

/* ==============================================================
    STATIC OPTIONS
============================================================== */

const nodeTypes: { value: OrgNodeType; label: string }[] = [
  { value: "LEGAL_ENTITY", label: "Legal Entity" },
  { value: "BUSINESS_UNIT", label: "Business Unit" },
  { value: "DIVISION", label: "Division" },
  { value: "REGION", label: "Region" },
  { value: "FACILITY", label: "Facility" },
];

const consolidationMethods: { value: ConsolidationMethod; label: string }[] = [
  { value: "FULL", label: "Full Consolidation" },
  { value: "PROPORTIONAL", label: "Proportional Consolidation" },
  { value: "EQUITY", label: "Equity Method" },
];

interface Company {
  id: string;
  company_name: string;
}

const ROOT_VALUE = "__root__";

/* ==============================================================
    FORM STATE
============================================================== */

const emptyFormState: OrgNodePayload = {
  company: "",
  parent: null,
  node_type: "LEGAL_ENTITY",
  code: "",
  name: "",
  facility_type: "",
  address: "",
  grid_region: "",
  water_stressed_area: false,
  latitude: "",
  longitude: "",
  country: "",
  state: "",
  city: "",
  ownership_percentage: "",
  operational_control: true,
  consolidation_method: "FULL",
  commissioned_on: null,
  decommissioned_on: null,
  is_active: true,
  
};

export default function OrganizationForm() {
  const navigate = useNavigate();
  const { id } = useParams();

  /* ==========================================================
      MASTER DATA
  ========================================================== */

  // The platform is provisioned for a single company, so there is no
  // company picker — the org's own company is loaded once and used
  // for every node.
  const [company, setCompany] = useState<Company | null>(null);
  const [countries, setCountries] = useState<Country[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [siblingNodes, setSiblingNodes] = useState<OrgNode[]>([]);

  /* ==========================================================
      UI STATE
  ========================================================== */

  const [loading, setLoading] = useState(false);

  /* ==========================================================
      FORM STATE
  ========================================================== */

  const [formData, setFormData] = useState<OrgNodePayload>(emptyFormState);
  

  const updateField = <K extends keyof OrgNodePayload>(
    key: K,
    value: OrgNodePayload[K],
  ) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const isFacility = formData.node_type === "FACILITY";
  const isLegalEntity = formData.node_type === "LEGAL_ENTITY";

  /* ==========================================================
      LOAD MASTER DATA
  ========================================================== */

  const loadSiblingNodes = useCallback(async (companyId: string) => {
  try {
    const response = await OrganizationApi.getAll();
    setSiblingNodes(response.data.filter((node) => node.company === companyId));
  } catch {
    toast.error("Unable to load organization nodes.");
  }
}, []);


  const loadCompany = useCallback(async () => {
  try {
    const response = await CompanyApi.getProfile();
    const ownCompany = response.data ?? null;
    setCompany(ownCompany);

    if (ownCompany) {
      setFormData((prev) => ({ ...prev, company: ownCompany.id }));
      void loadSiblingNodes(ownCompany.id);
    }
  } catch {
    toast.error("Unable to load company.");
  }
}, [loadSiblingNodes]);

const loadCountries = useCallback(async () => {
  try {
    const response = await CompanyApi.getCountries();
    setCountries(response.data);
  } catch {
    toast.error("Unable to load countries.");
  }
}, []);
  const loadStates = async (countryId: string) => {
    if (!countryId) {
      setStates([]);
      setCities([]);
      return;
    }

    try {
      const response = await CompanyApi.getStates(countryId);
      setStates(response.data);
    } catch {
      toast.error("Unable to load states.");
    }
  };

  const loadCities = async (stateId: string) => {
    if (!stateId) {
      setCities([]);
      return;
    }

    try {
      const response = await CompanyApi.getCities(stateId);
      setCities(response.data);
    } catch {
      toast.error("Unable to load cities.");
    }
  };

  // Nodes belonging to the company — used to populate the Parent
  // dropdown and to check the one-root-LEGAL_ENTITY rule.


  
const loadOrgNode = useCallback(async (nodeId: string) => {
  try {
    setLoading(true);

    const response = await OrganizationApi.getById(nodeId);
    const node = response.data;
    setFormData({
      company: node.company,
      parent: node.parent ?? null,
      node_type: node.node_type,
      code: node.code ?? "",
      name: node.name,
      facility_type: node.facility_type ?? "",
      address: node.address ?? "",
      grid_region: node.grid_region ?? "",
      water_stressed_area: node.water_stressed_area,
      latitude: node.latitude ?? "",
      longitude: node.longitude ?? "",
      country: node.country ?? "",
      state: node.state ?? "",
      city: node.city ?? "",
      ownership_percentage: node.ownership_percentage ?? "",
      operational_control: node.operational_control,
      consolidation_method: node.consolidation_method,
      commissioned_on: node.commissioned_on ??null,
      decommissioned_on: node.decommissioned_on ?? null,
      is_active: node.is_active,
    });

    if (node.country) await loadStates(node.country);
    if (node.state) await loadCities(node.state);
  } catch {
    toast.error("Unable to load OrgNode.");
  } finally {
    setLoading(false);
  }
}, []);

  useEffect(() => {
  const load = async () => {
    await loadCompany();
    await loadCountries();
  };

  void load();
}, [loadCompany, loadCountries]);

useEffect(() => {
  if (!id) return;

  const load = async () => {
    await loadOrgNode(id);
  };

  void load();
}, [id, loadOrgNode]);

useEffect(() => {
  const load = async () => {
    if (formData.country) {
      await loadStates(formData.country);
    }
  };

  void load();
}, [formData.country]);

useEffect(() => {
  const load = async () => {
    if (formData.state) {
      await loadCities(formData.state);
    }
  };

  void load();
}, [formData.state]);
  /* ==========================================================
      BUSINESS RULES (mirrors OrgNode.clean())
  ========================================================== */

  // A FACILITY cannot have children, so it can never be selected as
  // someone else's parent. A LEGAL_ENTITY is always a root node.
  const parentOptions = useMemo(
    () =>
      siblingNodes.filter(
        (node) => node.id !== id && node.node_type !== "FACILITY",
      ),
    [siblingNodes, id],
  );

  // Only one root LEGAL_ENTITY is allowed per company.
  const rootLegalEntityExists = useMemo(
    () =>
      siblingNodes.some(
        (node) =>
          node.id !== id && node.node_type === "LEGAL_ENTITY" && !node.parent,
      ),
    [siblingNodes, id],
  );

  const handleNodeTypeChange = (value: OrgNodeType) => {
    setFormData((prev) => ({
      ...prev,
      node_type: value,
      // LEGAL_ENTITY can never have a parent.
      parent: value === "LEGAL_ENTITY" ? null : prev.parent,
    }));
  };

  /* ==========================================================
      SUBMIT
  ========================================================== */

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formData.company) {
      toast.error("Company could not be determined.");
      return;
    }

    if (!formData.name.trim()) {
      toast.error("Name is required.");
      return;
    }

    if (!formData.code.trim()) {
      toast.error("Node code is required.");
      return;
    }

    if (formData.ownership_percentage) {
      const ownership = Number(formData.ownership_percentage);
      if (Number.isNaN(ownership) || ownership < 0 || ownership > 100) {
        toast.error("Ownership percentage must be between 0 and 100.");
        return;
      }
    }

    if (
      formData.commissioned_on &&
      formData.decommissioned_on &&
      formData.decommissioned_on < formData.commissioned_on
    ) {
      toast.error("Decommission date cannot be before commissioned date.");
      return;
    }

    if (isLegalEntity && !id && rootLegalEntityExists) {
      toast.error("Only one root Legal Entity is allowed per company.");
      return;
    }

    setLoading(true);

    try {
      const payload: OrgNodePayload = {
        ...formData,
        name: formData.name.trim(),
        code: formData.code.trim(),
        parent: isLegalEntity ? null : formData.parent || null,
        // Facility-specific fields are only allowed on FACILITY nodes.
        facility_type: isFacility ? formData.facility_type : "",
        address: isFacility ? formData.address : "",
        grid_region: isFacility ? formData.grid_region : "",
        water_stressed_area: isFacility ? formData.water_stressed_area : false,
        latitude: isFacility ? formData.latitude : "",
        longitude: isFacility ? formData.longitude : "",
      };

      if (id) {
        await OrganizationApi.update(id, payload);
        toast.success("OrgNode updated successfully.");
      } else {
        await OrganizationApi.create(payload);
        toast.success("OrgNode created successfully.");
      }

      navigate("/organizations");
    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, "Unable to save OrgNode. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <AppShell
      title={id ? "Edit Organization" : "Create Organization"}
      description={
        id
          ? "Update this organization in the hierarchy."
          : "Add a legal entity, business unit, or facility to the organization hierarchy."
      }
    >
      <form onSubmit={handleSubmit} className="px-4 md:px-6 lg:px-8">
        <Card>
          <CardHeader className="px-6 py-6">
            <CardTitle>{id ? "Edit Organization" : "Create Organization"}</CardTitle>
            <CardDescription>
              Define where this node sits in the company hierarchy and how it
              consolidates.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-8 px-6 py-6">
            {/* ==========================================================
                BASIC INFORMATION
            ========================================================== */}
            <div className="space-y-6">
              <h4 className="text-sm font-semibold">Basic Information</h4>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-2">
                  <Label>Company</Label>
                  <Input value={company?.company_name ?? "Loading..."} disabled />
                </div>

                <div className="space-y-2">
                  <Label>Parent Node</Label>
                  <Select
                    value={formData.parent ?? ROOT_VALUE}
                    onValueChange={(value) =>
                      updateField("parent", value === ROOT_VALUE ? null : value)
                    }
                    disabled={isLegalEntity}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Root node" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={ROOT_VALUE}>Root node</SelectItem>
                      {parentOptions.map((node) => (
                        <SelectItem key={node.id} value={node.id}>
                          {node.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {isLegalEntity && (
                    <p className="text-sm text-muted-foreground">
                      A Legal Entity is always a root node.
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Node Type</Label>
                  <Select
                    value={formData.node_type}
                    onValueChange={(value) =>
                      handleNodeTypeChange(value as OrgNodeType)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Node Type" />
                    </SelectTrigger>
                    <SelectContent>
                      {nodeTypes.map((nodeType) => (
                        <SelectItem key={nodeType.value} value={nodeType.value}>
                          {nodeType.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {isLegalEntity && !id && rootLegalEntityExists && (
                    <p className="text-sm text-destructive">
                      This company already has a root Legal Entity.
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => updateField("name", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Node Code</Label>
                  <Input
                    value={formData.code}
                    onChange={(e) => updateField("code", e.target.value)}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* ==========================================================
                LOCATION
            ========================================================== */}
            <div className="space-y-6">
              <h4 className="text-sm font-semibold">Location</h4>

              <div className="grid gap-6 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Country</Label>
                  <Select
                    value={formData.country}
                    onValueChange={(value) => {
                      // Radix can emit an empty value while options mount.
                      // It is not a user action and must not erase hydrated
                      // location values on the edit form.
                      if (!value) return;
                      setFormData((previous) => ({
                        ...previous,
                        country: value,
                        state: "",
                        city: "",
                      }));
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

                <div className="space-y-2">
                  <Label>State</Label>
                  <Select
                    value={formData.state}
                    onValueChange={(value) => {
                      if (!value) return;
                      setFormData((previous) => ({
                        ...previous,
                        state: value,
                        city: "",
                      }));
                    }}
                    disabled={!formData.country}
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

                <div className="space-y-2">
                  <Label>City</Label>
                  <Select
                    value={formData.city}
                    onValueChange={(value) => {
                      if (value) updateField("city", value);
                    }}
                    disabled={!formData.state}
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

            {/* ==========================================================
                FACILITY INFORMATION
            ========================================================== */}
            <div className="space-y-6">
              <h4 className="text-sm font-semibold">Facility Information</h4>
              {!isFacility && (
                <p className="-mt-4 text-sm text-muted-foreground">
                  Only applicable when Node Type is set to Facility.
                </p>
              )}

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Facility Type</Label>
                  <Input
                    disabled={!isFacility}
                    value={formData.facility_type}
                    onChange={(e) => updateField("facility_type", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Grid Region</Label>
                  <Input
                    disabled={!isFacility}
                    value={formData.grid_region}
                    onChange={(e) => updateField("grid_region", e.target.value)}
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label>Address</Label>
                  <Textarea
                    rows={3}
                    disabled={!isFacility}
                    value={formData.address}
                    onChange={(e) => updateField("address", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Latitude</Label>
                  <Input
                    type="number"
                    step="0.000001"
                    disabled={!isFacility}
                    value={formData.latitude}
                    onChange={(e) => updateField("latitude", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Longitude</Label>
                  <Input
                    type="number"
                    step="0.000001"
                    disabled={!isFacility}
                    value={formData.longitude}
                    onChange={(e) => updateField("longitude", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Commissioned On</Label>
                  <Input
                    type="date"
                    disabled={!isFacility}
                    value={formData.commissioned_on ?? ""}
                    onChange={(e) =>
                      updateField("commissioned_on", e.target.value)
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>Decommissioned On</Label>
                  <Input
                    type="date"
                    disabled={!isFacility}
                    value={formData.decommissioned_on ?? ""}
                    onChange={(e) =>
                      updateField("decommissioned_on", e.target.value)
                    }
                  />
                </div>

                <div className="flex items-center gap-2 md:col-span-2">
                  <Checkbox
                    id="water_stressed_area"
                    disabled={!isFacility}
                    checked={formData.water_stressed_area}
                    onCheckedChange={(checked) =>
                      updateField("water_stressed_area", checked === true)
                    }
                  />
                  <Label htmlFor="water_stressed_area" className="font-medium">
                    Water Stressed Area
                  </Label>
                </div>
              </div>
            </div>

            <Separator />

            {/* ==========================================================
                CONSOLIDATION
            ========================================================== */}
            <div className="space-y-6">
              <h4 className="text-sm font-semibold">Consolidation</h4>

              <div className="grid gap-6 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Ownership Percentage</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={formData.ownership_percentage}
                    onChange={(e) =>
                      updateField("ownership_percentage", e.target.value)
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>Consolidation Method</Label>
                  <Select
                    value={formData.consolidation_method}
                    onValueChange={(value) =>
                      updateField(
                        "consolidation_method",
                        value as ConsolidationMethod,
                      )
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Method" />
                    </SelectTrigger>
                    <SelectContent>
                      {consolidationMethods.map((method) => (
                        <SelectItem key={method.value} value={method.value}>
                          {method.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center gap-2">
                  <Checkbox
                    id="operational_control"
                    checked={formData.operational_control}
                    onCheckedChange={(checked) =>
                      updateField("operational_control", checked === true)
                    }
                  />
                  <Label htmlFor="operational_control" className="font-medium">
                    Operational Control
                  </Label>
                </div>
              </div>
            </div>

            <Separator />

            {/* ==========================================================
                STATUS
            ========================================================== */}
            <div className="flex items-center gap-2">
              <Checkbox
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) =>
                  updateField("is_active", checked === true)
                }
              />
              <Label htmlFor="is_active" className="font-medium">
                Active Status
              </Label>
            </div>
          </CardContent>

          {/* ==========================================================
              ACTIONS
          ========================================================== */}
          <CardContent className="flex items-center justify-end gap-3 border-t px-6 py-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/organizations")}
            >
              Cancel
            </Button>

            <Button type="submit" disabled={loading}>
              {loading
                ? id
                  ? "Updating..."
                  : "Creating..."
                : id
                ? "Update OrgNode"
                : "Create OrgNode"}
            </Button>
          </CardContent>
        </Card>
      </form>
    </AppShell>
  );
}

/* ==============================================================
    HELPERS
============================================================== */
