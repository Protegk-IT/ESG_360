import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import OrganizationApi from "@/api/organizations/OrganizationApi";
import CompanyApi from "@/api/companies/CompanyApi";
import type { OrgNode, OrgNodePayload, OrgNodeType } from "@/types/organization";
import type { Country, State, City } from "@/types/company";
import { NODE_TYPE_CONFIG } from "./nodeTypeConfig";

interface OrgNodeFormPanelProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  mode: "create" | "edit";
  parentNode: OrgNode | null;
  editingNode: OrgNode | null;
  rootCompany: string;
}

const ALL_NODE_TYPES: OrgNodeType[] = [
  "LEGAL_ENTITY",
  "BUSINESS_UNIT",
  "DIVISION",
  "REGION",
  "FACILITY",
];
function buildDefaultPayload(parentNode: OrgNode | null, companyId: string): OrgNodePayload  {
  const defaultType: OrgNodeType = parentNode
    ? NODE_TYPE_CONFIG[parentNode.node_type].defaultChildType ?? "FACILITY"
    : "LEGAL_ENTITY";

  return {
    company: companyId,
    parent: parentNode?.id ?? null,
    node_type: defaultType,
    code: "",
    name: "",
    facility_type: "",
    address: "",
    grid_region: "",
    water_stressed_area: false,
    latitude: "",
    longitude: "",
    country: parentNode?.country ?? "",
    state: parentNode?.state ?? "",
    city: parentNode?.city ?? "",
    ownership_percentage: "100.00",
    operational_control: true,
    consolidation_method: "FULL",
    commissioned_on: null,
    decommissioned_on: null,
    is_active: true,
  };
}

export default function OrgNodeFormPanel({
  open,
  onClose,
  onSaved,
  mode,
  parentNode,
  editingNode,
  rootCompany,
}: OrgNodeFormPanelProps) {
  const [form, setForm] = useState<OrgNodePayload>(() =>
    buildDefaultPayload(parentNode, rootCompany)
  );
  const [saving, setSaving] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [companyId, setCompanyId] = useState<string>("");

  const [countries, setCountries] = useState<Country[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [cities, setCities] = useState<City[]>([]);

  /* ==========================================================
      POPULATE FORM ON OPEN
  ========================================================== */
/* ==========================================================
    POPULATE FORM ON OPEN
========================================================== */

useEffect(() => {
  const populate = () => {
    if (!open) return;

    if (mode === "edit" && editingNode) {
      setForm({
        company: editingNode.company,
        parent: editingNode.parent,
        node_type: editingNode.node_type,
        code: editingNode.code,
        name: editingNode.name,
        facility_type: editingNode.facility_type ?? "",
        address: editingNode.address ?? "",
        grid_region: editingNode.grid_region ?? "",
        water_stressed_area: editingNode.water_stressed_area,
        latitude: editingNode.latitude ?? "",
        longitude: editingNode.longitude ?? "",
        country: editingNode.country ?? "",
        state: editingNode.state ?? "",
        city: editingNode.city ?? "",
        ownership_percentage: editingNode.ownership_percentage,
        operational_control: editingNode.operational_control,
        consolidation_method: editingNode.consolidation_method,
        commissioned_on: editingNode.commissioned_on ?? null,
        decommissioned_on: editingNode.decommissioned_on ?? null,
        is_active: editingNode.is_active,
      });
    } else {
      setForm(buildDefaultPayload(parentNode, companyId));
    }
    setShowAdvanced(false);
  };

  populate();
}, [open, mode, editingNode, parentNode, companyId]);

useEffect(() => {
  const load = () => {
    if (!open) return;
    CompanyApi.getProfile()
      .then((res) => setCompanyId(res.data?.id ?? ""))
      .catch(() => toast.error("Unable to load company."));
  };

  load();
}, [open]);

/* ==========================================================
    LOCATION CASCADE
========================================================== */

useEffect(() => {
  const load = () => {
    if (!open) return;
    CompanyApi.getCountries()
      .then((res) => setCountries(res.data))
      .catch(() => toast.error("Unable to load countries."));
  };

  load();
}, [open]);

useEffect(() => {
  const load = () => {
    if (!form.country) {
      setStates([]);
      return;
    }
    CompanyApi.getStates(form.country)
      .then((res) => setStates(res.data))
      .catch(() => toast.error("Unable to load states."));
  };

  load();
}, [form.country]);

useEffect(() => {
  const load = () => {
    if (!form.state) {
      setCities([]);
      return;
    }
    CompanyApi.getCities(form.state)
      .then((res) => setCities(res.data))
      .catch(() => toast.error("Unable to load cities."));
  };

  load();
}, [form.state]);
  const isFacility = form.node_type === "FACILITY";

  const update = <K extends keyof OrgNodePayload>(key: K, value: OrgNodePayload[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSave = async () => {
    if (!companyId) {
    toast.error("Company could not be determined. Please try again.");
    return;
  }
  if (!form.name.trim() || !form.code.trim()) {
    toast.error("Name and code are required.");
    return;
  }

    try {
      setSaving(true);
      const payload = { ...form, company: companyId };

      if (mode === "edit" && editingNode) {
        await OrganizationApi.update(editingNode.id, form);
        toast.success("Node updated successfully.");
      } else {
        await OrganizationApi.create(payload);
        toast.success("Node created successfully.");
      }

      onSaved();
      onClose();
    } catch (error) {
      console.error(error);
      toast.error("Unable to save organization node.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto bg-white shadow-2xl sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {mode === "edit"
              ? `Edit ${NODE_TYPE_CONFIG[form.node_type].label}`
              : parentNode
                ? `Add Child under ${parentNode.name}`
                : "Add Node"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Node Type */}
          <div className="space-y-1.5">
            <Label>Node Type</Label>
            <Select
              value={form.node_type}
              onValueChange={(value) => update("node_type", value as OrgNodeType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ALL_NODE_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {NODE_TYPE_CONFIG[type].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Name / Code */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input value={form.name} onChange={(e) => update("name", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Code</Label>
              <Input value={form.code} onChange={(e) => update("code", e.target.value)} />
            </div>
          </div>

          {/* Country / State / City — always visible, mandatory */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label>Country</Label>
              <Select
                value={form.country}
                onValueChange={(value) => {
                  // The Select can emit an empty value while its options are
                  // mounting. Ignore that internal event so an edit dialog
                  // keeps the location loaded from the existing OrgNode.
                  if (!value) return;
                  setForm((previous) => ({
                    ...previous,
                    country: value,
                    state: "",
                    city: "",
                  }));
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select country" />
                </SelectTrigger>
                <SelectContent>
                  {countries.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>State</Label>
              <Select
                value={form.state}
                onValueChange={(value) => {
                  if (!value) return;
                  setForm((previous) => ({
                    ...previous,
                    state: value,
                    city: "",
                  }));
                }}
                disabled={!form.country}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  {states.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>City</Label>
              <Select
                value={form.city}
                onValueChange={(value) => {
                  if (value) update("city", value);
                }}
                disabled={!form.state}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select city" />
                </SelectTrigger>
                <SelectContent>
                  {cities.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Active */}
          <div className="flex items-center gap-2">
            <Checkbox
              checked={form.is_active}
              onCheckedChange={(checked) => update("is_active", checked === true)}
            />
            <Label>Active</Label>
          </div>

          {/* Facility-only fields */}
          {isFacility && (
            <div className="space-y-3 rounded-lg border border-[#E5E7EB] p-3">
              <p className="text-xs font-semibold uppercase text-[#6B7280]">Facility Details</p>

              <div className="space-y-1.5">
                <Label>Facility Type</Label>
                <Input
                  value={form.facility_type ?? ""}
                  onChange={(e) => update("facility_type", e.target.value)}
                  placeholder="e.g. Manufacturing Plant, Warehouse"
                />
              </div>

              <div className="space-y-1.5">
                <Label>Address</Label>
                <Input
                  value={form.address ?? ""}
                  onChange={(e) => update("address", e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Grid Region</Label>
                  <Input
                    value={form.grid_region ?? ""}
                    onChange={(e) => update("grid_region", e.target.value)}
                  />
                </div>
                <div className="flex items-end gap-2 pb-2">
                  <Checkbox
                    checked={form.water_stressed_area}
                    onCheckedChange={(checked) => update("water_stressed_area", checked === true)}
                  />
                  <Label>Water Stressed Area</Label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Latitude</Label>
                  <Input
                    value={form.latitude ?? ""}
                    onChange={(e) => update("latitude", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Longitude</Label>
                  <Input
                    value={form.longitude ?? ""}
                    onChange={(e) => update("longitude", e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Advanced (ownership / consolidation only) */}
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="text-sm font-medium text-[#4A3FD6]"
          >
            {showAdvanced ? "Hide advanced fields" : "Show advanced fields"}
          </button>

          {showAdvanced && (
            <div className="space-y-3 rounded-lg border border-[#E5E7EB] p-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Ownership %</Label>
                  <Input
                    value={form.ownership_percentage}
                    onChange={(e) => update("ownership_percentage", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Consolidation Method</Label>
                  <Select
                    value={form.consolidation_method}
                    onValueChange={(value) =>
                      update("consolidation_method", value as OrgNodePayload["consolidation_method"])
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="FULL">Full</SelectItem>
                      <SelectItem value="PROPORTIONAL">Proportional</SelectItem>
                      <SelectItem value="EQUITY">Equity</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  checked={form.operational_control}
                  onCheckedChange={(checked) => update("operational_control", checked === true)}
                />
                <Label>Operational Control</Label>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
