import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useParams,
} from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import {
  DataTable,
} from "@/common/DataTable";

import {
  DataTableToolbar,
} from "@/common/DataTableToolbar";

import ConfirmDialog from "@/common/ConfirmDialog";

import {
  Badge,
} from "@/components/ui/badge";

import {
  Button,
} from "@/components/ui/button";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";



import {
  Progress,
} from "@/components/ui/progress";

import {
  Pencil,
  Plus,
  Trash2,
  Users,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

import {
  type ColumnDef,
} from "@tanstack/react-table";

import {
  toast,
} from "sonner";

import api from "@/services/api";

import StakeholderGroupDialog from "@/pages/materiality/StakeholderGroupDialog";

import type {
  StakeholderGroup,
  StakeholderGroupFormData,
} from "@/types/materiality/stakeholder";



// ============================================================
// COMPONENT
// ============================================================

export default function StakeholderGroups() {

  const {
    id: assessmentId,
  } = useParams<{
    id: string;
  }>();


  // ==========================================================
  // STATE
  // ==========================================================

  const [
    groups,
    setGroups,
  ] = useState<StakeholderGroup[]>([]);


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    saving,
    setSaving,
  ] = useState(false);


  const [
    search,
    setSearch,
  ] = useState("");


  const [
    dialogOpen,
    setDialogOpen,
  ] = useState(false);


  const [
    editingGroup,
    setEditingGroup,
  ] = useState<
    StakeholderGroup | null
  >(null);


  const [
    selectedGroup,
    setSelectedGroup,
  ] = useState<
    StakeholderGroup | null
  >(null);


  const [
    deleteDialogOpen,
    setDeleteDialogOpen,
  ] = useState(false);


  const [
    deleting,
    setDeleting,
  ] = useState(false);


  // ==========================================================
  // LOAD GROUPS
  // ==========================================================

  const loadGroups = useCallback(
    async () => {

      if (!assessmentId) {
        return;
      }

      try {

        setLoading(true);

        const response =
          await api.get<StakeholderGroup[]>(
            `/materiality/assessments/${assessmentId}/groups/`
          );

        setGroups(
          response.data
        );

      } catch (error) {

        console.error(
          "Failed to load stakeholder groups:",
          error
        );

        toast.error(
          "Unable to load stakeholder groups."
        );

      } finally {

        setLoading(false);

      }

    },
    [assessmentId]
  );


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

 useEffect(() => {
  const load = async () => {
    await loadGroups();
  };

  void load();
}, [loadGroups]);


  // ==========================================================
  // TOTAL WEIGHT
  // ==========================================================

  const totalWeight =
    useMemo(() => {

      return groups.reduce(
        (
          total,
          group
        ) => {

          return (
            total +
            Number(group.weight || 0)
          );

        },
        0
      );

    }, [groups]);


  // ==========================================================
  // WEIGHT STATUS
  // ==========================================================

  const weightStatus =
    useMemo(() => {

      if (
        Math.abs(totalWeight - 100) <
        0.01
      ) {
        return "complete";
      }

      if (
        totalWeight > 100
      ) {
        return "over";
      }

      return "incomplete";

    }, [totalWeight]);


  // ==========================================================
  // FILTERED GROUPS
  // ==========================================================

  const filteredGroups =
    useMemo(() => {

      const keyword =
        search
          .trim()
          .toLowerCase();

      if (!keyword) {
        return groups;
      }

      return groups.filter(
        (group) =>
          group.name
            .toLowerCase()
            .includes(keyword) ||
          group.description
            .toLowerCase()
            .includes(keyword)
      );

    }, [
      groups,
      search,
    ]);


  // ==========================================================
  // OPEN CREATE DIALOG
  // ==========================================================

  const handleCreate =
    () => {

      setEditingGroup(null);

      setDialogOpen(true);

    };


  // ==========================================================
  // OPEN EDIT DIALOG
  // ==========================================================

  const handleEdit =
    (group: StakeholderGroup) => {

      setEditingGroup(group);

      setDialogOpen(true);

    };

      // ==========================================================
  // SAVE GROUP
  // ==========================================================

  const handleSave =
    async (
      formData: StakeholderGroupFormData
    ) => {

      if (!assessmentId) {

        toast.error(
          "Assessment ID is missing."
        );

        return;

      }

      try {

        setSaving(true);


        // ----------------------------------------------------
        // CREATE
        // ----------------------------------------------------

        if (!editingGroup) {

          await api.post(
            `/materiality/assessments/${assessmentId}/groups/`,
            {
              name:
                formData.name.trim(),

              description:
                formData.description.trim(),

              weight:
                formData.weight,

              is_internal:
                formData.is_internal,
            }
          );


          toast.success(
            "Stakeholder group created successfully."
          );

        }

        // ----------------------------------------------------
        // UPDATE
        // ----------------------------------------------------

        else {

          await api.patch(
            `/materiality/assessments/${assessmentId}/groups/${editingGroup.id}/`,
            {
              name:
                formData.name.trim(),

              description:
                formData.description.trim(),

              weight:
                formData.weight,

              is_internal:
                formData.is_internal,
            }
          );


          toast.success(
            "Stakeholder group updated successfully."
          );

        }


        setDialogOpen(false);

        setEditingGroup(null);

        await loadGroups();

      } catch (error) {

        console.error(
          "Failed to save stakeholder group:",
          error
        );


        toast.error(
          "Unable to save stakeholder group."
        );

      } finally {

        setSaving(false);

      }

    };


  // ==========================================================
  // OPEN DELETE CONFIRMATION
  // ==========================================================

  const handleDeleteClick =
    (group: StakeholderGroup) => {

      setSelectedGroup(group);

      setDeleteDialogOpen(true);

    };


  // ==========================================================
  // DELETE GROUP
  // ==========================================================

  const handleDelete =
    async () => {

      if (
        !assessmentId ||
        !selectedGroup
      ) {
        return;
      }

      try {

        setDeleting(true);


        await api.delete(
          `/materiality/assessments/${assessmentId}/groups/${selectedGroup.id}/`
        );


        toast.success(
          "Stakeholder group deleted successfully."
        );


        setDeleteDialogOpen(false);

        setSelectedGroup(null);

        await loadGroups();

      } catch (error) {

        console.error(
          "Failed to delete stakeholder group:",
          error
        );


        toast.error(
          "Unable to delete stakeholder group."
        );

      } finally {

        setDeleting(false);

      }

    };


  // ==========================================================
  // TABLE COLUMNS
  // ==========================================================

  const columns =
    useMemo<
      ColumnDef<StakeholderGroup>[]
    >(
      () => [

        // ----------------------------------------------------
        // GROUP NAME
        // ----------------------------------------------------

        {
          accessorKey: "name",

          header: "Stakeholder Group",

          cell: ({
            row,
          }) => {

            const group =
              row.original;

            return (
              <div className="flex items-center gap-3">

                <div
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-lg
                    bg-emerald-50
                    text-emerald-700
                  "
                >
                  <Users
                    className="h-4 w-4"
                  />
                </div>


                <div>

                  <p
                    className="
                      font-medium
                      text-slate-900
                    "
                  >
                    {group.name}
                  </p>


                  {group.description && (
                    <p
                      className="
                        max-w-[350px]
                        truncate
                        text-xs
                        text-muted-foreground
                      "
                    >
                      {group.description}
                    </p>
                  )}

                </div>

              </div>
            );

          },
        },


        // ----------------------------------------------------
        // TYPE
        // ----------------------------------------------------

        {
          accessorKey: "is_internal",

          header: "Type",

          cell: ({
            row,
          }) => {

            const isInternal =
              row.original.is_internal;

            return isInternal ? (

              <Badge
                className="
                  border
                  border-blue-200
                  bg-blue-50
                  text-blue-700
                  hover:bg-blue-50
                "
              >
                Internal
              </Badge>

            ) : (

              <Badge
                className="
                  border
                  border-violet-200
                  bg-violet-50
                  text-violet-700
                  hover:bg-violet-50
                "
              >
                External
              </Badge>

            );

          },
        },


        // ----------------------------------------------------
        // WEIGHT
        // ----------------------------------------------------

        {
          accessorKey: "weight",

          header: "Weight",

          cell: ({
            row,
          }) => {

            const weight =
              Number(
                row.original.weight || 0
              );

            return (
              <div
                className="
                  flex
                  items-center
                  gap-2
                "
              >

                <span
                  className="
                    font-medium
                    text-slate-900
                  "
                >
                  {weight.toFixed(2)}%
                </span>

              </div>
            );

          },
        },


        // ----------------------------------------------------
        // ACTIONS
        // ----------------------------------------------------

        {
          id: "actions",

          header: "Actions",

          cell: ({
            row,
          }) => {

            const group =
              row.original;

            return (
              <div
                className="
                  flex
                  items-center
                  gap-1
                "
              >

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    handleEdit(group)
                  }
                  title="Edit group"
                >
                  <Pencil
                    className="
                      h-4
                      w-4
                    "
                  />
                </Button>


                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    handleDeleteClick(
                      group
                    )
                  }
                  title="Delete group"
                  className="
                    text-red-600
                    hover:bg-red-50
                    hover:text-red-700
                  "
                >
                  <Trash2
                    className="
                      h-4
                      w-4
                    "
                  />
                </Button>

              </div>
            );

          },
        },

      ],
      []
    );


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
   <AppShell
  title="Stakeholder Groups"
  description="Configure stakeholder groups and assign their respective weights for this materiality assessment."
>

      <div
        className="
          flex
          flex-col
          gap-6
          p-6
        "
      >

        {/* ====================================================
            PAGE HEADER
        ===================================================== */}

        <div
          className="
            flex
            flex-col
            gap-4
            md:flex-row
            md:items-center
            md:justify-between
          "
        >

          <div>

            <div
              className="
                mb-1
                flex
                items-center
                gap-2
              "
            >

              <Users
                className="
                  h-5
                  w-5
                  text-emerald-600
                "
              />

              <span
                className="
                  text-sm
                  font-medium
                  text-emerald-600
                "
              >
                Materiality Assessment
              </span>

            </div>


            <h1
              className="
                text-2xl
                font-bold
                tracking-tight
                text-slate-900
              "
            >
              Stakeholder Groups
            </h1>


            <p
              className="
                mt-1
                text-sm
                text-muted-foreground
              "
            >
              Configure stakeholder groups
              and assign their materiality
              assessment weights.
            </p>

          </div>


          <Button
            onClick={handleCreate}
            className="
              bg-emerald-600
              hover:bg-emerald-700
            "
          >

            <Plus
              className="
                mr-2
                h-4
                w-4
              "
            />

            Add Stakeholder Group

          </Button>

        </div>


        {/* ====================================================
            WEIGHT SUMMARY
        ===================================================== */}

        <Card
          className="
            border-slate-200
            shadow-sm
          "
        >

          <CardHeader
            className="
              px-6  pb-4
            "
          >

            <CardTitle
              className="
                text-base
                font-semibold
              "
            >
              Stakeholder Weight Allocation
            </CardTitle>

          </CardHeader>


          <CardContent>

            <div
              className="
                flex
                flex-col
                gap-4
              "
            >

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <div>

                  <p
                    className="
                      text-sm
                      text-muted-foreground
                       px-6  pb-3
                    "
                  >
                    Total assigned weight
                  </p>


                  <p
                    className="
                      mt-1
                      text-2xl
                      font-bold
                      text-slate-900
                       px-6  pb-4
                    "
                  >
                    {totalWeight.toFixed(2)}%
                  </p>

                </div>


                {weightStatus ===
                  "complete" && (

                  <Badge
                    className="
                      gap-1
                      border
                      border-emerald-200
                      bg-emerald-50
                      text-emerald-700
                      hover:bg-emerald-50
                    "
                  >

                    <CheckCircle2
                      className="
                        h-3.5
                        w-3.5
                      "
                    />

                    Allocation Complete

                  </Badge>

                )}


                {weightStatus ===
                  "incomplete" && (

                  <Badge
                    className="
                      gap-1
                      border
                      border-amber-200
                      bg-amber-50
                      text-amber-700
                      hover:bg-amber-50
                      
                    "
                  >

                    <AlertCircle
                      className="
                        h-3.5
                        w-3.5
                        
                        
                      "
                    />

                    {(
                      100 -
                      totalWeight
                    ).toFixed(2)}
                    % remaining

                  </Badge>

                )}


                {weightStatus ===
                  "over" && (

                  <Badge
                    className="
                      gap-1
                      border
                      border-red-200
                      bg-red-50
                      text-red-700
                      hover:bg-red-50
                    "
                  >

                    <AlertCircle
                      className="
                        h-3.5
                        w-3.5
                      "
                    />

                    Over allocation

                  </Badge>

                )}

              </div>


              <Progress
                value={Math.min(
                  totalWeight,
                  100
                )}
                className="h-2"
              />

            </div>

          </CardContent>

        </Card>
                {/* ====================================================
            GROUP TABLE
        ===================================================== */}

        <Card
          className="
            border-slate-200
            shadow-sm
          "
        >

          <CardHeader
            className="
              border-b
              border-slate-100
              px-6  pb-4
            "
          >

            <div
              className="
                flex
                flex-col
                gap-20
                md:flex-row
                md:items-center
                md:justify-between
              "
            >

              <div>

                <CardTitle
                  className="
                    text-base
                    font-semibold
                     whitespace-nowrap
                    
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


              <DataTableToolbar
                search={search}
                onSearchChange={setSearch}
              />

            </div>

          </CardHeader>


          <CardContent
            className="pt-4"
          >

            <DataTable
              columns={columns}
              data={filteredGroups}
              loading={loading}
            />

          </CardContent>

        </Card>


        {/* ====================================================
            WEIGHT VALIDATION MESSAGE
        ===================================================== */}

        {groups.length > 0 &&
          weightStatus !==
            "complete" && (

          <div
            className="
              flex
              items-start
              gap-3
              rounded-lg
              border
              border-amber-200
              bg-amber-50
              p-4
            "
          >

            <AlertCircle
              className="
                mt-0.5
                h-5
                w-5
                shrink-0
                text-amber-600
              "
            />


            <div>

              <p
                className="
                  text-sm
                  font-medium
                  text-amber-800
                "
              >
                Stakeholder weights must total
                100%.
              </p>


              <p
                className="
                  mt-1
                  text-xs
                  text-amber-700
                "
              >
                Current allocation is{" "}
                {totalWeight.toFixed(2)}%.
                Please adjust the group
                weights before continuing
                with the assessment.
              </p>

            </div>

          </div>

        )}


        {/* ====================================================
            CREATE / EDIT DIALOG
        ===================================================== */}

       <StakeholderGroupDialog
  open={dialogOpen}
  onClose={() => setDialogOpen(false)}
  group={editingGroup}
  onSave={handleSave}
  currentTotalWeight={totalWeight}
  saving={saving}
/>


        {/* ====================================================
            DELETE CONFIRMATION
        ===================================================== */}

        <ConfirmDialog
                  open={deleteDialogOpen}
                  title="Delete Stakeholder Group"
                  description={selectedGroup
                      ? `Are you sure you want to delete "${selectedGroup.name}"? All stakeholders belonging to this group will also be removed.`
                      : "Are you sure you want to delete this stakeholder group?"}
                  confirmText="Delete Group"
                  cancelText="Cancel"
                  onConfirm={handleDelete}
                  loading={deleting} onCancel={function (): void {
                      throw new Error("Function not implemented.");
                  } }        />

      </div>

    </AppShell>
  );
}