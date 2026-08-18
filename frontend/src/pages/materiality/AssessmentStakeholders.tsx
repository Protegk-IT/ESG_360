import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  Button,
} from "@/components/ui/button";

import {
  Badge,
} from "@/components/ui/badge";

import {
  DataTableToolbar,
} from "@/common/DataTableToolbar";

import StakeholderApi from "@/api/materiality/StakeholderApi";
import AssessmentApi from "@/api/materiality/AssessmentApi";

import StakeholderGroupDialog from "./StakeholderGroupDialog";
import StakeholderDialog from "./StakeholderDialog";

import type {
  StakeholderGroup,
  StakeholderGroupFormData,
  Stakeholder,
  StakeholderFormData,
} from "@/types/materiality/stakeholder";
import type { MaterialityAssessment } from "@/types/materiality/assessment";

import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  FileSpreadsheet,
  Loader2,
  Plus,
  Upload,
  UserPlus,
  Users,
  ArrowLeft,
  Download,
  Pencil,
  Trash2,
} from "lucide-react";

import { toast } from "sonner";


/* ==========================================================
   COMPONENT
========================================================== */

export default function AssessmentStakeholders() {

  const {
    id,
  } = useParams<{
    id: string;
  }>();

  const navigate = useNavigate();



  /* ========================================================
     STATES
  ======================================================== */

  const [
    groups,
    setGroups,
  ] = useState<StakeholderGroup[]>([]);

  const [
    stakeholders,
    setStakeholders,
  ] = useState<Stakeholder[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    savingGroup,
    setSavingGroup,
  ] = useState(false);

  const [
    savingStakeholder,
    setSavingStakeholder,
  ] = useState(false);

  const [
    importing,
    setImporting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(null);

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    expandedGroups,
    setExpandedGroups,
  ] = useState<
    Set<string>
  >(new Set());


  /* ========================================================
     GROUP DIALOG
  ======================================================== */

  const [
    groupDialogOpen,
    setGroupDialogOpen,
  ] = useState(false);

  const [
    editingGroup,
    setEditingGroup,
  ] = useState<StakeholderGroup | null>(
    null
  );


  /* ========================================================
     STAKEHOLDER DIALOG
  ======================================================== */

  const [
    stakeholderDialogOpen,
    setStakeholderDialogOpen,
  ] = useState(false);

  const [
    selectedGroup,
    setSelectedGroup,
  ] = useState<StakeholderGroup | null>(
    null
  );

  const [editingStakeholder, setEditingStakeholder] = useState<Stakeholder | null>(null);

  const [assessment, setAssessment] = useState<MaterialityAssessment | null>(null);
  const isReadOnly = Boolean(assessment?.is_locked);


  /* ========================================================
     CSV INPUT
  ======================================================== */

  const fileInputRef =
    useRef<HTMLInputElement | null>(null);


  /* ========================================================
     LOAD DATA
  ======================================================== */

  const loadData = useCallback(
    async () => {

      if (!id) {
        return;
      }

      try {

        setLoading(true);
        setError(null);

        const [
          groupsResponse,
          stakeholdersResponse,
          assessmentResponse,
        ] = await Promise.all([
          StakeholderApi.getGroups(id),
          StakeholderApi.getStakeholders(id),
          AssessmentApi.getById(id),
        ]);

        setGroups(
          groupsResponse.data
        );

        setStakeholders(
          stakeholdersResponse.data
        );
        setAssessment(assessmentResponse.data);

      } catch (err) {

        console.error(
          "Failed to load stakeholder data:",
          err
        );

        setError(
          "Unable to load stakeholder groups."
        );

      } finally {

        setLoading(false);

      }

    },
    [id]
  );


  /* ========================================================
     INITIAL LOAD
  ======================================================== */

  useEffect(() => {

    loadData();

  }, [loadData]);


  /* ========================================================
     TOTAL WEIGHT
  ======================================================== */

  const totalWeight = useMemo(
    () => {

      return groups.reduce(
        (total, group) =>
          total +
          Number(group.weight || 0),
        0
      );

    },
    [groups]
  );


  /* ========================================================
     REMAINING WEIGHT
  ======================================================== */

  const remainingWeight = Math.max(
    0,
    100 - totalWeight
  );


  /* ========================================================
     WEIGHT STATUS
  ======================================================== */

  const weightStatus =
    totalWeight === 100
      ? "complete"
      : totalWeight > 100
        ? "over"
        : "incomplete";


  /* ========================================================
     FILTER GROUPS
  ======================================================== */

  const filteredGroups = useMemo(
    () => {

      const value =
        search
          .trim()
          .toLowerCase();

      if (!value) {
        return groups;
      }

      return groups.filter(
        (group) => {

          const groupStakeholders =
            stakeholders.filter(
              (stakeholder) =>
                stakeholder.group ===
                group.id
            );

          const groupMatches =
            group.name
              .toLowerCase()
              .includes(value) ||
            group.description
              ?.toLowerCase()
              .includes(value);

          const stakeholderMatches =
            groupStakeholders.some(
              (stakeholder) =>
                stakeholder.name
                  .toLowerCase()
                  .includes(value) ||
                stakeholder.email
                  .toLowerCase()
                  .includes(value) ||
                stakeholder.organisation
                  ?.toLowerCase()
                  .includes(value) ||
                stakeholder.designation
                  ?.toLowerCase()
                  .includes(value)
            );

          return (
            groupMatches ||
            stakeholderMatches
          );
        }
      );

    },
    [
      groups,
      stakeholders,
      search,
    ]
  );


  /* ========================================================
     TOGGLE GROUP
  ======================================================== */

  const toggleGroup = (
    groupId: string
  ) => {

    setExpandedGroups(
      (previous) => {

        const next =
          new Set(previous);

        if (next.has(groupId)) {
          next.delete(groupId);
        } else {
          next.add(groupId);
        }

        return next;

      }
    );
  };


  /* ========================================================
     OPEN CREATE GROUP
  ======================================================== */

  const handleAddGroup = () => {

    setEditingGroup(null);

    setGroupDialogOpen(true);

  };


  /* ========================================================
     SAVE GROUP
  ======================================================== */
const handleSaveGroup = async (
  data: StakeholderGroupFormData
) => {
  if (!id) {
    return;
  }

  const newWeight = Number(data.weight || 0);

  const existingWeight = editingGroup
    ? Number(editingGroup.weight || 0)
    : 0;

  const projectedTotal =
    totalWeight -
    existingWeight +
    newWeight;

  // ============================================
  // VALIDATE TOTAL WEIGHT
  // ============================================

  if (projectedTotal > 100) {
    toast.error(
      "Invalid weight allocation",
      {
        description:
          `Total stakeholder group weight cannot exceed 100%. ` +
          `You have ${remainingWeight.toFixed(2)}% remaining.`,
      }
    );

    return;
  }

  // ============================================
  // SAVE GROUP
  // ============================================

  try {
    setSavingGroup(true);

    await StakeholderApi.createGroup(
      id,
      data
    );

    toast.success(
      "Stakeholder group added",
      {
        description:
          `${data.name} has been added successfully.`,
      }
    );

    setGroupDialogOpen(false);
    setEditingGroup(null);

    await loadData();

  } catch (err) {
    console.error(
      "Failed to create stakeholder group:",
      err
    );

    toast.error(
      "Unable to add stakeholder group",
      {
        description:
          "Please check the group details and try again.",
      }
    );

    throw err;

  } finally {
    setSavingGroup(false);
  }
};

  /* ========================================================
     OPEN STAKEHOLDER DIALOG
  ======================================================== */

  const handleAddStakeholder = (
    group: StakeholderGroup
  ) => {

    setSelectedGroup(group);
    setEditingStakeholder(null);

    setStakeholderDialogOpen(true);

  };

  const handleEditStakeholder = (stakeholder: Stakeholder) => {
    const group = groups.find((item) => item.id === stakeholder.group);
    if (!group) return;
    setSelectedGroup(group);
    setEditingStakeholder(stakeholder);
    setStakeholderDialogOpen(true);
  };


  /* ========================================================
     SAVE STAKEHOLDER
  ======================================================== */

  const handleSaveStakeholder =
    async (
      data: StakeholderFormData
    ) => {

      if (!id) {
        return;
      }

      try {

        setSavingStakeholder(true);

        if (editingStakeholder) {
          await StakeholderApi.updateStakeholder(id, editingStakeholder.id, data);
        } else {
          await StakeholderApi.createStakeholder(id, data);
        }

        toast.success(
            editingStakeholder ? "Stakeholder updated successfully." : "Stakeholder has been added successfully.",
        );

        setStakeholderDialogOpen(false);
        setSelectedGroup(null);
        setEditingStakeholder(null);

        await loadData();

      } catch (err) {

        console.error(
          "Failed to create stakeholder:",
          err
        );

        toast.error(
        
            "Unable to add stakeholder",
        
        );

        throw err;

      } finally {

        setSavingStakeholder(false);

      }
    };

  const handleDeleteStakeholder = async (stakeholder: Stakeholder) => {
    if (!id || !window.confirm(`Delete ${stakeholder.name}? This is only allowed before an invitation exists.`)) {
      return;
    }
    try {
      await StakeholderApi.deleteStakeholder(id, stakeholder.id);
      toast.success("Stakeholder deleted successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to delete stakeholder:", err);
      toast.error("Unable to delete stakeholder.", {
        description: "Stakeholders with invitation history are retained for auditability.",
      });
    }
  };


  /* ========================================================
     IMPORT CSV
  ======================================================== */

  const handleImportClick = () => {

    fileInputRef.current?.click();

  };


  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {

    const file =
      event.target.files?.[0];

    if (!file || !id) {
      return;
    }

    if (
      !file.name
        .toLowerCase()
        .endsWith(".csv")
    ) {

      toast.error(
        "Invalid file",
       
      );

      event.target.value = "";

      return;
    }

    try {

      setImporting(true);

      const response = await StakeholderApi.importStakeholders(id, file);

      toast.success(
          response.data?.message ?? "Stakeholders imported",
      );

      await loadData();

    } catch (err) {

      console.error(
        "Failed to import stakeholders:",
        err
      );

      toast.error(
        
     
          "Unable to import the CSV file. Please check the required columns.",
        
      );

    } finally {

      setImporting(false);

      event.target.value = "";

    }
  };

  const handleDownloadTemplate = async () => {
    if (!id) return;
    try {
      const response = await StakeholderApi.downloadTemplate(id);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "stakeholder-import-template.csv";
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download stakeholder template:", err);
      toast.error("Unable to download the CSV template.");
    }
  };


  /* ========================================================
     GET STAKEHOLDERS FOR GROUP
  ======================================================== */

  const getGroupStakeholders = (
    groupId: string
  ) => {

    return stakeholders.filter(
      (stakeholder) =>
        stakeholder.group === groupId
    );

  };


  /* ========================================================
     LOADING STATE
  ======================================================== */

  if (loading) {

    return (
      <AppShell
        title="Stakeholders"
        description="Manage stakeholder groups and participants."
      >

        <div
          className="
            flex
            min-h-[400px]
            items-center
            justify-center
          "
        >

          <Loader2
            className="
              h-7
              w-7
              animate-spin
              text-emerald-600
            "
          />

        </div>

      </AppShell>
    );

  }


  /* ========================================================
     RENDER
  ======================================================== */

  return (
    <AppShell
      title="Stakeholders"
      description="
        Configure stakeholder groups and
        manage their individual participants.
      "
    >

      <div
        className="
          flex
          flex-col
          gap-6
          p-6
        "
      >

        {/* ==================================================
            TOP ACTIONS
        ================================================== */}

        <div
          className="
            flex
            flex-col
            gap-4
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
        >

          <Button
            variant="outline"
            onClick={() =>
              navigate(
                "/materiality/assessments"
              )
            }
            className="
              w-fit
              gap-2
            "
          >

            <ArrowLeft
              className="
                h-4
                w-4
              "
            />

            Back to Assessments

          </Button>


          <div
            className="
              flex
              flex-wrap
              gap-2
            "
          >

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={
                handleFileChange
              }
            />

            <Button
              variant="outline"
              onClick={handleDownloadTemplate}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download CSV Template
            </Button>

            {!isReadOnly && <Button
              variant="outline"
              onClick={handleImportClick}
              disabled={importing}
              className="gap-2"
            >

              {importing ? (
                <Loader2
                  className="
                    h-4
                    w-4
                    animate-spin
                  "
                />
              ) : (
                <Upload
                  className="
                    h-4
                    w-4
                  "
                />
              )}

              Import CSV

            </Button>}


            {!isReadOnly && <Button
              onClick={handleAddGroup}
              className="
                gap-2
                bg-emerald-600
                text-white
                hover:bg-emerald-700
              "
            >

              <Plus
                className="
                  h-4
                  w-4
                "
              />

              Add Stakeholder Group

            </Button>}

          </div>

        </div>


        {/* ==================================================
            WEIGHT SUMMARY
        ================================================== */}

        <Card
          className="
            border
            border-slate-200
            shadow-sm
          "
        >

          <CardContent
            className="
              p-5
            "
          >

            <div
              className="
                flex
                flex-col
                gap-4
                sm:flex-row
                sm:items-center
                sm:justify-between
              "
            >

              <div
                className="
                  flex
                  items-center
                  gap-3
                "
              >

                <div
                  className="
                    flex
                    h-10
                    w-10
                    items-center
                    justify-center
                    rounded-lg
                    bg-emerald-50
                    text-emerald-600
                  "
                >

                  <Users
                    className="
                      h-5
                      w-5
                    "
                  />

                </div>

                <div>

                  <p
                    className="
                      text-sm
                      font-semibold
                      text-slate-900
                    "
                  >
                    Stakeholder Weight Allocation
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      text-slate-500
                    "
                  >
                    Group weights must total 100%.
                  </p>

                </div>

              </div>


              <div
                className="
                  flex
                  items-center
                  gap-3
                "
              >

                <span
                  className="
                    text-sm
                    text-slate-500
                  "
                >
                  Total
                </span>

                <Badge
                  className={
                    weightStatus === "complete"
                      ? `
                        border
                        border-emerald-200
                        bg-emerald-50
                        text-emerald-700
                      `
                      : weightStatus === "over"
                        ? `
                          border
                          border-red-200
                          bg-red-50
                          text-red-700
                        `
                        : `
                          border
                          border-amber-200
                          bg-amber-50
                          text-amber-700
                        `
                  }
                >
                  {totalWeight.toFixed(2)}%
                </Badge>

                <span
                  className="
                    text-xs
                    text-slate-500
                  "
                >
                  {remainingWeight.toFixed(2)}%
                  remaining
                </span>

              </div>

            </div>

          </CardContent>

        </Card>


        {/* ==================================================
            GROUPS CARD
        ================================================== */}

        <Card
          className="
            border
            border-slate-200
            shadow-sm
          "
        >

          <CardHeader
            className="
              border-b
              border-slate-100
              px-5
              py-4
            "
          >

            <div
              className="
                flex
                flex-col
                gap-4
                lg:flex-row
                lg:items-center
                lg:justify-between
              "
            >

              <div>

                <CardTitle
                  className="
                    whitespace-nowrap
                    text-base
                    font-semibold
                    text-slate-900
                  "
                >
                  Stakeholder Groups
                </CardTitle>

                <p
                  className="
                    mt-1
                    text-xs
                    text-muted-foreground
                  "
                >
                  {groups.length}{" "}
                  {groups.length === 1
                    ? "group"
                    : "groups"}{" "}
                  configured
                </p>

              </div>


              <div
                className="
                  min-w-0
                  lg:w-[300px]
                "
              >

                <DataTableToolbar
                  search={search}
                  onSearchChange={
                    setSearch
                  }
                />

              </div>

            </div>

          </CardHeader>


          <CardContent
            className="
              p-0
            "
          >

            {/* =================================================
                ERROR
            ================================================= */}

            {error && (
              <div
                className="
                  m-5
                  flex
                  items-center
                  gap-2
                  rounded-lg
                  border
                  border-red-200
                  bg-red-50
                  px-4
                  py-3
                  text-sm
                  text-red-700
                "
              >

                <AlertCircle
                  className="
                    h-4
                    w-4
                    shrink-0
                  "
                />

                <span>
                  {error}
                </span>

              </div>
            )}


            {/* =================================================
                EMPTY
            ================================================= */}

            {!error &&
              filteredGroups.length === 0 && (
                <div
                  className="
                    flex
                    flex-col
                    items-center
                    justify-center
                    px-6
                    py-16
                    text-center
                  "
                >

                  <div
                    className="
                      mb-4
                      flex
                      h-12
                      w-12
                      items-center
                      justify-center
                      rounded-full
                      bg-slate-100
                      text-slate-500
                    "
                  >

                    <Users
                      className="
                        h-5
                        w-5
                      "
                    />

                  </div>

                  <h3
                    className="
                      text-sm
                      font-semibold
                      text-slate-900
                    "
                  >
                    No stakeholder groups
                  </h3>

                  <p
                    className="
                      mt-1
                      max-w-sm
                      text-xs
                      text-slate-500
                    "
                  >
                    Create a stakeholder group
                    to start adding participants
                    to this assessment.
                  </p>

                  {!isReadOnly && <Button
                    onClick={
                      handleAddGroup
                    }
                    className="
                      mt-5
                      gap-2
                      bg-emerald-600
                      hover:bg-emerald-700
                    "
                  >

                    <Plus
                      className="
                        h-4
                        w-4
                      "
                    />

                    Add Stakeholder Group

                  </Button>}

                </div>
              )}


            {/* =================================================
                GROUP LIST
            ================================================= */}

            <div
              className="
                divide-y
                divide-slate-100
              "
            >

              {filteredGroups.map(
                (group) => {

                  const isExpanded =
                    expandedGroups.has(
                      group.id
                    );

                  const groupStakeholders =
                    getGroupStakeholders(
                      group.id
                    );

                  return (
                    <div
                      key={group.id}
                      className="
                        bg-white
                      "
                    >

                      {/* ========================================
                          GROUP HEADER
                      ======================================== */}

                      <div
                        className="
                          flex
                          cursor-pointer
                          items-center
                          justify-between
                          gap-4
                          px-5
                          py-4
                          transition-colors
                          hover:bg-slate-50
                        "
                        onClick={() =>
                          toggleGroup(
                            group.id
                          )
                        }
                      >

                        <div
                          className="
                            flex
                            min-w-0
                            items-center
                            gap-3
                          "
                        >

                          {isExpanded ? (
                            <ChevronDown
                              className="
                                h-4
                                w-4
                                shrink-0
                                text-slate-400
                              "
                            />
                          ) : (
                            <ChevronRight
                              className="
                                h-4
                                w-4
                                shrink-0
                                text-slate-400
                              "
                            />
                          )}


                          <div
                            className="
                              flex
                              h-9
                              w-9
                              shrink-0
                              items-center
                              justify-center
                              rounded-lg
                              bg-slate-100
                              text-slate-600
                            "
                          >

                            <Users
                              className="
                                h-4
                                w-4
                              "
                            />

                          </div>


                          <div
                            className="
                              min-w-0
                            "
                          >

                            <div
                              className="
                                flex
                                items-center
                                gap-2
                              "
                            >

                              <p
                                className="
                                  truncate
                                  text-sm
                                  font-semibold
                                  text-slate-900
                                "
                              >
                                {group.name}
                              </p>

                              <Badge
                                variant="outline"
                                className="
                                  shrink-0
                                  text-[10px]
                                "
                              >
                                {group.is_internal
                                  ? "Internal"
                                  : "External"}
                              </Badge>

                            </div>

                            {group.description && (
                              <p
                                className="
                                  mt-0.5
                                  truncate
                                  text-xs
                                  text-slate-500
                                "
                              >
                                {group.description}
                              </p>
                            )}

                          </div>

                        </div>


                        <div
                          className="
                            flex
                            shrink-0
                            items-center
                            gap-4
                          "
                          onClick={(event) =>
                            event.stopPropagation()
                          }
                        >

                          <div
                            className="
                              hidden
                              text-right
                              sm:block
                            "
                          >

                            <p
                              className="
                                text-sm
                                font-semibold
                                text-slate-800
                              "
                            >
                              {Number(
                                group.weight || 0
                              ).toFixed(2)}
                              %
                            </p>

                            <p
                              className="
                                text-[10px]
                                text-slate-400
                              "
                            >
                              Weight
                            </p>

                          </div>


                          <Badge
                            className="
                              border
                              border-slate-200
                              bg-slate-50
                              text-slate-600
                              hover:bg-slate-50
                            "
                          >
                            {groupStakeholders.length}{" "}
                            {groupStakeholders.length === 1
                              ? "stakeholder"
                              : "stakeholders"}
                          </Badge>

                        </div>

                      </div>


                      {/* ========================================
                          EXPANDED STAKEHOLDERS
                      ======================================== */}

                      {isExpanded && (
                        <div
                          className="
                            border-t
                            border-slate-100
                            bg-slate-50/50
                            px-5
                            pb-5
                            pt-4
                          "
                        >

                          <div
                            className="
                              overflow-hidden
                              rounded-lg
                              border
                              border-slate-200
                              bg-white
                            "
                          >

                            {/* ==================================
                                TABLE HEADER
                            ================================== */}

                            <div
                              className="
                                hidden
                                grid-cols-[1.2fr_1.5fr_1.2fr_1.2fr_auto]
                                gap-4
                                border-b
                                border-slate-200
                                bg-slate-50
                                px-4
                                py-3
                                text-xs
                                font-medium
                                text-slate-500
                                md:grid
                              "
                            >

                              <span>
                                Name
                              </span>

                              <span>
                                Email
                              </span>

                              <span>
                                Organisation
                              </span>

                              <span>
                                Designation
                              </span>

                              <span>
                                Action
                              </span>

                            </div>


                            {/* ==================================
                                STAKEHOLDERS
                            ================================== */}

                            {groupStakeholders.length >
                            0 ? (
                              <div
                                className="
                                  divide-y
                                  divide-slate-100
                                "
                              >

                                {groupStakeholders.map(
                                  (
                                    stakeholder
                                  ) => (
                                    <div
                                      key={
                                        stakeholder.id
                                      }
                                      className="
                                        grid
                                        grid-cols-1
                                        gap-2
                                        px-4
                                        py-3
                                        md:grid-cols-[1.2fr_1.5fr_1.2fr_1.2fr_auto]
                                        md:items-center
                                        md:gap-4
                                      "
                                    >

                                      <div>

                                        <p
                                          className="
                                            text-sm
                                            font-medium
                                            text-slate-800
                                          "
                                        >
                                          {
                                            stakeholder.name
                                          }
                                        </p>

                                        <p
                                          className="
                                            mt-0.5
                                            text-xs
                                            text-slate-500
                                            md:hidden
                                          "
                                        >
                                          {
                                            stakeholder.email
                                          }
                                        </p>

                                      </div>


                                      <p
                                        className="
                                          hidden
                                          truncate
                                          text-xs
                                          text-slate-600
                                          md:block
                                        "
                                      >
                                        {
                                          stakeholder.email
                                        }
                                      </p>

                                      <p
                                        className="
                                          text-xs
                                          text-slate-600
                                        "
                                      >
                                        {
                                          stakeholder.organisation ||
                                          "—"
                                        }
                                      </p>


                                      <p
                                        className="
                                          text-xs
                                          text-slate-600
                                        "
                                      >
                                        {
                                          stakeholder.designation ||
                                          "—"
                                        }
                                      </p>

                                      {!isReadOnly && <div className="flex gap-1">
                                        <Button type="button" variant="ghost" size="icon" aria-label={`Edit ${stakeholder.name}`} onClick={() => handleEditStakeholder(stakeholder)}>
                                          <Pencil className="h-3.5 w-3.5" />
                                        </Button>
                                        <Button type="button" variant="ghost" size="icon" aria-label={`Delete ${stakeholder.name}`} className="text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => void handleDeleteStakeholder(stakeholder)}>
                                          <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                      </div>}

                                    </div>
                                  )
                                )}

                              </div>
                            ) : (
                              <div
                                className="
                                  flex
                                  flex-col
                                  items-center
                                  justify-center
                                  px-6
                                  py-8
                                  text-center
                                "
                              >

                                <UserPlus
                                  className="
                                    mb-2
                                    h-5
                                    w-5
                                    text-slate-400
                                  "
                                />

                                <p
                                  className="
                                    text-sm
                                    font-medium
                                    text-slate-700
                                  "
                                >
                                  No stakeholders yet
                                </p>

                                <p
                                  className="
                                    mt-1
                                    text-xs
                                    text-slate-500
                                  "
                                >
                                  Add an individual
                                  stakeholder to this
                                  group.
                                </p>

                              </div>
                            )}


                            {/* ==================================
                                ADD STAKEHOLDER
                            ================================== */}

                            <div
                              className="
                                border-t
                                border-slate-100
                                bg-slate-50
                                px-4
                                py-3
                              "
                            >

                              {!isReadOnly && <Button
                                variant="outline"
                                size="sm"
                                className="
                                  gap-2
                                  border-emerald-200
                                  text-emerald-700
                                  hover:bg-emerald-50
                                "
                                onClick={() =>
                                  handleAddStakeholder(
                                    group
                                  )
                                }
                              >

                                <UserPlus
                                  className="
                                    h-4
                                    w-4
                                  "
                                />

                                Add Stakeholder

                              </Button>}

                            </div>

                          </div>

                        </div>
                      )}

                    </div>
                  );
                }
              )}

            </div>

          </CardContent>

        </Card>


        {/* ==================================================
            CSV INFORMATION
        ================================================== */}

        <div
          className="
            flex
            items-start
            gap-3
            rounded-lg
            border
            border-slate-200
            bg-slate-50
            px-4
            py-3
          "
        >

          <FileSpreadsheet
            className="
              mt-0.5
              h-4
              w-4
              shrink-0
              text-slate-500
            "
          />

          <div>

            <p
              className="
                text-xs
                font-medium
                text-slate-700
              "
            >
              CSV import format
            </p>

            <p
              className="
                mt-1
                text-xs
                text-slate-500
              "
            >
              Required columns: group, name,
              email. Optional columns:
              organisation, designation.
            </p>

          </div>

        </div>

      </div>


      {/* ====================================================
          GROUP DIALOG
      ==================================================== */}

     <StakeholderGroupDialog
  open={groupDialogOpen}
  onClose={() => {
    if (!savingGroup) {
      setGroupDialogOpen(false);
      setEditingGroup(null);
    }
  }}
  group={editingGroup}
  onSave={handleSaveGroup}
  currentTotalWeight={totalWeight}
  saving={savingGroup}
/>


      {/* ====================================================
          STAKEHOLDER DIALOG
      ==================================================== */}

      {selectedGroup && (
        <StakeholderDialog
          open={
            stakeholderDialogOpen
          }
          onClose={() => {

            if (!savingStakeholder) {

              setStakeholderDialogOpen(
                false
              );

              setSelectedGroup(null);
              setEditingStakeholder(null);

            }

          }}
          groupId={
            selectedGroup.id
          }
          groupName={
            selectedGroup.name
          }
          onSave={
            handleSaveStakeholder
          }
          saving={
            savingStakeholder
          }
          stakeholder={editingStakeholder}
        />
      )}

    </AppShell>
  );
}
