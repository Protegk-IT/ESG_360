import { Building2, MapPin, Factory } from "lucide-react";
import type { OrgNodeType } from "@/types/organization";

export const NODE_TYPE_CONFIG: Record<OrgNodeType, {
  label: string;
    icon: typeof Building2;
    iconBg: string;
    iconColor: string;
    badgeClass: string;
    defaultChildType: OrgNodeType | null;
}> = {
  LEGAL_ENTITY: {
    label: "Legal Entity",
    icon: Building2,
    iconBg: "bg-[#DCFCE7]",
    iconColor: "text-[#16A34A]",
    badgeClass: "bg-[#DCFCE7] text-[#16A34A] border-transparent",
    defaultChildType: "BUSINESS_UNIT",
  },
  BUSINESS_UNIT: {
    label: "Business Unit",
    icon: Building2,
    iconBg: "bg-[#DBEAFE]",
    iconColor: "text-[#2563EB]",
    badgeClass: "bg-[#DBEAFE] text-[#2563EB] border-transparent",
    defaultChildType: "REGION",
  },
  DIVISION: {
    label: "Division",
    icon: Building2,
    iconBg: "bg-[#EDE9FE]",
    iconColor: "text-[#7C3AED]",
    badgeClass: "bg-[#EDE9FE] text-[#7C3AED] border-transparent",
    defaultChildType: "REGION",
  },
  REGION: {
    label: "Region",
    icon: MapPin,
    iconBg: "bg-[#FFEDD5]",
    iconColor: "text-[#F97316]",
    badgeClass: "bg-[#FFEDD5] text-[#F97316] border-transparent",
    defaultChildType: "FACILITY",
  },
  FACILITY: {
    label: "Facility",
    icon: Factory,
    iconBg: "bg-[#CFFAFE]",
    iconColor: "text-[#0891B2]",
    badgeClass: "bg-[#CFFAFE] text-[#0891B2] border-transparent",
    defaultChildType: null,
  },
};