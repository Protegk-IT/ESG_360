import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
} from "@/components/ui/sidebar";

import { useAuth } from "@/context/AuthContext";
import { useLocation } from "react-router-dom";

import { navMain } from "./sidebar-data";
import { NavMain } from "./NavMain";
import { NavUser } from "./NavUser";
import { getAssessmentNav } from "./assessmentNavigation";

interface AppSidebarProps {
  isAssessmentMode?: boolean;
  assessmentId?: string | null;
}

export function AppSidebar({
  isAssessmentMode,
  assessmentId,
}: AppSidebarProps) {
  const { user } = useAuth();
  const location = useLocation();

  /*
   * ==========================================================
   * AUTO-DETECT ASSESSMENT FROM URL
   * ==========================================================
   *
   * Example:
   *
   * /materiality/assessments/f90762ca-79cc-43cf-8a38-019f2c8d045f/select-topics/
   *
   * assessmentId =
   * f90762ca-79cc-43cf-8a38-019f2c8d045f
   */

  const assessmentMatch = location.pathname.match(
    /^\/materiality\/assessments\/([^/]+)/
  );

  const detectedAssessmentId =
    assessmentMatch?.[1] ?? null;

  /*
   * If AppSidebar is explicitly given an assessmentId,
   * use it.
   *
   * Otherwise use the ID detected from the URL.
   */

  const currentAssessmentId =
    assessmentId ?? detectedAssessmentId;

  /*
   * Assessment mode is automatically enabled when
   * we are inside an assessment URL.
   *
   * Explicit true is also respected.
   */

  const currentAssessmentMode =
    isAssessmentMode ??
    Boolean(currentAssessmentId);

  return (
    <Sidebar
      collapsible="icon"
      className="border-r border-gray-200 bg-white text-slate-900"
    >
      {/* =====================================================
          SIDEBAR HEADER
      ===================================================== */}

      <SidebarHeader
        className="
          border-b
          border-gray-100
        "
      >
        {currentAssessmentMode ? (
          /* ==================================================
             ASSESSMENT MODE HEADER
          ================================================== */

          <div
            className="
              px-4
              py-4
              transition-all
              group-data-[collapsible=icon]:px-2
            "
          >
            <div
              className="
                flex
                items-center
                gap-3
                group-data-[collapsible=icon]:justify-center
              "
            >
              {/* Assessment icon */}

              <div
                className="
                  flex
                  h-9
                  w-9
                  shrink-0
                  items-center
                  justify-center
                  rounded-xl
                  bg-[#0F766E]
                  text-sm
                  font-bold
                  text-white
                  shadow-sm
                "
              >
                A
              </div>

              {/* Assessment information */}

              <div
                className="
                  min-w-0
                  group-data-[collapsible=icon]:hidden
                "
              >
                <p
                  className="
                    text-[10px]
                    font-semibold
                    uppercase
                    tracking-[0.16em]
                    text-[#0F766E]
                  "
                >
                  Assessment
                </p>

                <h1
                  className="
                    mt-0.5
                    truncate
                    text-sm
                    font-semibold
                    text-slate-900
                  "
                >
                  Materiality Assessment
                </h1>

                <p
                  className="
                    mt-0.5
                    truncate
                    text-xs
                    text-gray-500
                  "
                >
                  {currentAssessmentId
                    ? `ID: ${currentAssessmentId.slice(0, 8)}...`
                    : "Current Assessment"}
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* ==================================================
             NORMAL MODE HEADER
          ================================================== */

          <div
            className="
              flex
              items-center
              gap-3
              px-4
              py-4
              transition-all
              group-data-[collapsible=icon]:justify-center
              group-data-[collapsible=icon]:px-2
            "
          >
            <div className="relative shrink-0">
              <div
                className="
                  flex
                  h-9
                  w-9
                  items-center
                  justify-center
                  rounded-full
                  bg-slate-900
                  text-sm
                  font-bold
                  text-white
                "
              >
                E
              </div>

              <span
                className="
                  absolute
                  -right-0.5
                  -top-0.5
                  h-2.5
                  w-2.5
                  rounded-full
                  border-2
                  border-white
                  bg-green-500
                "
              />
            </div>

            <div
              className="
                min-w-0
                group-data-[collapsible=icon]:hidden
              "
            >
              <h1
                className="
                  truncate
                  text-sm
                  font-semibold
                  text-slate-900
                "
              >
                ESG
                <span className="text-blue-600">
                  360
                </span>
              </h1>

              <p
                className="
                  truncate
                  text-xs
                  text-gray-500
                "
              >
                {user?.role_name ?? "User"}
              </p>
            </div>
          </div>
        )}
      </SidebarHeader>

      {/* =====================================================
          NAVIGATION
      ===================================================== */}

      <SidebarContent className="py-2">
        <NavMain
          items={
            currentAssessmentMode
              ? getAssessmentNav(currentAssessmentId)
              : navMain
          }
          isAssessmentMode={currentAssessmentMode}
          assessmentId={currentAssessmentId}
        />
      </SidebarContent>

      {/* =====================================================
          USER
      ===================================================== */}

      <NavUser />
    </Sidebar>
  );
}