import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useParams,
} from "react-router-dom";

import {
  ChevronDown,
  ChevronRight,
  Users,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";

import SurveyApi, {
  type SurveyInvitationResult,
} from "@/api/materiality/surveyApi";

import type {
  Survey,
} from "@/types/materiality/survey";

import type {
  Stakeholder,
} from "@/types/materiality/stakeholder";

import {
  Card,
  CardContent,
  CardDescription,
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
  Checkbox,
} from "@/components/ui/checkbox";

import {
  Separator,
} from "@/components/ui/separator";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  AlertCircle,
  Check,
  Copy,
  Loader2,
  Mail,
  RefreshCw,
  Send,
} from "lucide-react";

import {
  toast,
} from "sonner";


/* ==========================================================
   COMPONENT
========================================================== */

export default function SurveyDistribution() {

  const {
    id,
  } = useParams<{
    id: string;
  }>();


  /* ========================================================
     SURVEY
  ======================================================== */

  const [
    survey,
    setSurvey,
  ] = useState<Survey | null>(
    null
  );

  const [
  expandedGroups,
  setExpandedGroups,
] = useState<Set<string>>(
  new Set()
);

  /* ========================================================
     STAKEHOLDERS
  ======================================================== */

  const [
    stakeholders,
    setStakeholders,
  ] = useState<Stakeholder[]>(
    []
  );


  const [
    selectedStakeholderIds,
    setSelectedStakeholderIds,
  ] = useState<Set<string>>(
    new Set()
  );


  /* ========================================================
     INVITATION RESULTS
  ======================================================== */

  const [
    invitations,
    setInvitations,
  ] = useState<
    SurveyInvitationResult[]
  >([]);


  /* ========================================================
     LOADING
  ======================================================== */

  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    refreshing,
    setRefreshing,
  ] = useState(false);


  const [
    sending,
    setSending,
  ] = useState(false);


  /* ========================================================
     SEND DIALOG
  ======================================================== */

  const [
    sendDialogOpen,
    setSendDialogOpen,
  ] = useState(false);


  /* ========================================================
     ERROR
  ======================================================== */

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  /* ========================================================
     LOAD SURVEY
  ======================================================== */

  const loadSurvey =
    useCallback(
      async () => {

        if (!id) {
          return;
        }

        const response =
          await SurveyApi.getSurvey(
            id
          );

        setSurvey(
          response.data
        );

      },
      [id]
    );


    const toggleGroup = (
  groupId: string
) => {
  setExpandedGroups(
    (previous) => {
      const next = new Set(
        previous
      );

      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }

      return next;
    }
  );
};

const toggleGroupStakeholders = (
  groupStakeholders: Stakeholder[]
) => {
  const groupIds =
    groupStakeholders.map(
      (stakeholder) =>
        stakeholder.id
    );

  const allGroupSelected =
    groupIds.length > 0 &&
    groupIds.every((id) =>
      selectedStakeholderIds.has(id)
    );

  setSelectedStakeholderIds(
    (previous) => {
      const next = new Set(
        previous
      );

      if (allGroupSelected) {
        groupIds.forEach((id) =>
          next.delete(id)
        );
      } else {
        groupIds.forEach((id) =>
          next.add(id)
        );
      }

      return next;
    }
  );
};
    // Stakeholder Group

const groupedStakeholders =
  useMemo(() => {
    return stakeholders.reduce<
      Record<string, Stakeholder[]>
    >((groups, stakeholder) => {
      const groupId =
        stakeholder.group;

      if (!groups[groupId]) {
        groups[groupId] = [];
      }

      groups[groupId].push(
        stakeholder
      );

      return groups;
    }, {});
  }, [stakeholders]);
  /* ========================================================
     LOAD STAKEHOLDERS
  ======================================================== */

  const loadStakeholders =
    useCallback(
      async () => {

        if (!id) {
          return;
        }

        const response =
          await SurveyApi.getStakeholders(
            id
          );

        setStakeholders(
          response.data
        );

      },
      [id]
    );


  /* ========================================================
     INITIAL LOAD
  ======================================================== */

  useEffect(() => {

    const loadData =
      async () => {

        try {

          setLoading(true);

          setError(null);

          await Promise.all([
            loadSurvey(),
            loadStakeholders(),
          ]);

        } catch (
          err: unknown
        ) {

          console.error(
            "Failed to load survey distribution:",
            err
          );

          setError(
            "Unable to load survey distribution."
          );

        } finally {

          setLoading(false);

        }
      };

    void loadData();

  }, [
    loadSurvey,
    loadStakeholders,
  ]);


  /* ========================================================
     REFRESH
  ======================================================== */

  const handleRefresh =
    async () => {

      try {

        setRefreshing(true);

        await Promise.all([
          loadSurvey(),
          loadStakeholders(),
        ]);

      } catch (
        err: unknown
      ) {

        console.error(
          "Failed to refresh survey distribution:",
          err
        );

        toast.error(
          "Unable to refresh survey distribution."
        );

      } finally {

        setRefreshing(false);

      }
    };


  /* ========================================================
     SELECTION HELPERS
  ======================================================== */

  const toggleStakeholder =
    (stakeholderId: string) => {

      setSelectedStakeholderIds(
        (previous) => {

          const next =
            new Set(previous);

          if (
            next.has(
              stakeholderId
            )
          ) {

            next.delete(
              stakeholderId
            );

          } else {

            next.add(
              stakeholderId
            );

          }

          return next;

        }
      );

    };


  
  /* ========================================================
     SELECTED COUNT
  ======================================================== */

  const selectedCount =
    selectedStakeholderIds.size;


  /* ========================================================
     SELECTED STAKEHOLDERS
  ======================================================== */

  const selectedStakeholders =
    useMemo(
      () =>
        stakeholders.filter(
          (stakeholder) =>
            selectedStakeholderIds.has(
              stakeholder.id
            )
        ),
      [
        stakeholders,
        selectedStakeholderIds,
      ]
    );


  /* ========================================================
     SEND INVITATIONS
  ======================================================== */

  const handleSendInvitations =
    async () => {

      if (!id) {
        return;
      }

      const ids =
        Array.from(
          selectedStakeholderIds
        );

      if (ids.length === 0) {

        toast.error(
          "Select at least one stakeholder."
        );

        return;

      }


      try {

        setSending(true);

        const response =
          await SurveyApi.sendSurvey(
            id,
            ids
          );

        setInvitations(
          response.data.invitations
        );

        setSelectedStakeholderIds(
          new Set()
        );

        setSendDialogOpen(
          false
        );

        toast.success(
          "Survey invitations sent successfully.",
          {
            description:
              `${response.data.count} stakeholder invitation${
                response.data.count === 1
                  ? ""
                  : "s"
              } sent.`,
          }
        );

      } catch (
        err: unknown
      ) {

        console.error(
          "Failed to send survey invitations:",
          err
        );

        toast.error(
          "Unable to send survey invitations."
        );

      } finally {

        setSending(false);

      }

    };


  /* ========================================================
     COPY LINK
  ======================================================== */

  const handleCopyLink =
    async (
      surveyUrl: string
    ) => {

      try {

        await navigator.clipboard.writeText(
          surveyUrl
        );

        toast.success(
          "Survey link copied."
        );

      } catch (
        err: unknown
      ) {

        console.error(
          "Failed to copy survey link:",
          err
        );

        toast.error(
          "Unable to copy survey link."
        );

      }

    };


  /* ========================================================
     MISSING ID
  ======================================================== */

  if (!id) {

    return (
      <AppShell
        title="Survey Distribution"
        description="Send stakeholder invitations and manage survey links."
      >

        <div
          className="
            rounded-xl
            border
            border-red-200
            bg-red-50
            p-6
            text-sm
            text-red-700
          "
        >
          Assessment ID is missing.
        </div>

      </AppShell>
    );

  }
    /* ========================================================
     LOADING
  ======================================================== */

  if (loading) {

    return (
      <AppShell
        title="Survey Distribution"
        description="Send stakeholder invitations and manage survey links."
      >

        <div
          className="
            flex
            min-h-[420px]
            items-center
            justify-center
          "
        >

          <Loader2
            className="
              h-7
              w-7
              animate-spin
              text-[#4A3FD6]
            "
          />

        </div>

      </AppShell>
    );

  }


  return (
    <AppShell
      title="Survey Distribution"
      description="Select stakeholders, send invitations, and manage survey links."
    >

      <div
        className="
          space-y-6
        "
      >

        {/* ==================================================
            HEADER
        ================================================== */}

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

            <div
              className="
                mb-1
                flex
                items-center
                gap-2
              "
            >

              <Mail
                className="
                  h-5
                  w-5
                  text-[#4A3FD6]
                "
              />

              <span
                className="
                  text-sm
                  font-medium
                  text-[#4A3FD6]
                "
              >
                Materiality Assessment
              </span>

            </div>


            <h1
              className="
                text-2xl
                font-semibold
                tracking-tight
                text-[#22243A]
              "
            >
              Survey Distribution
            </h1>


            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Select individual stakeholders and
              send their unique survey invitations.
            </p>

          </div>


          <div
            className="
              flex
              items-center
              gap-2
            "
          >

            <Button
              type="button"
              variant="outline"
              disabled={
                refreshing
              }
              onClick={
                handleRefresh
              }
              className="
                gap-2
              "
            >

              {refreshing ? (
                <Loader2
                  className="
                    h-4
                    w-4
                    animate-spin
                  "
                />
              ) : (
                <RefreshCw
                  className="
                    h-4
                    w-4
                  "
                />
              )}

              Refresh

            </Button>


            <Button
              type="button"
              disabled={
                selectedCount === 0 ||
                !survey
              }
              onClick={() =>
                setSendDialogOpen(
                  true
                )
              }
              className="
                gap-2
                bg-[#4A3FD6]
                text-white
                hover:bg-[#3F34C2]
              "
            >

              <Send
                className="
                  h-4
                  w-4
                "
              />

              Send Invitations
              {selectedCount > 0 &&
                ` (${selectedCount})`}

            </Button>

          </div>

        </div>


        {/* ==================================================
            ERROR
        ================================================== */}

        {error && (

          <div
            className="
              flex
              items-start
              gap-3
              rounded-xl
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
                mt-0.5
                h-4
                w-4
                shrink-0
              "
            />

            {error}

          </div>

        )}


        {/* ==================================================
            SURVEY NOT READY
        ================================================== */}

        {!survey && (

          <Card
            className="
              border-amber-200
              bg-amber-50
              shadow-none
            "
          >

            <CardContent
              className="
                flex
                items-start
                gap-3
                px-5
                py-4
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
                    font-semibold
                    text-amber-800
                  "
                >
                  Survey is not ready
                </p>

                <p
                  className="
                    mt-1
                    text-xs
                    leading-5
                    text-amber-700
                  "
                >
                  Generate the survey before
                  sending stakeholder invitations.
                </p>

              </div>

            </CardContent>

          </Card>

        )}


        {/* ==================================================
            SELECTION SUMMARY
        ================================================== */}

        <div
          className="
            grid
            gap-4
            sm:grid-cols-3
          "
        >

          <Card
            className="
              border-slate-200
              shadow-sm
            "
          >

            <CardContent
              className="
                p-5
              "
            >

              <p
                className="
                  text-xs
                  font-medium
                  text-slate-500
                "
              >
                Total Stakeholders
              </p>

              <p
                className="
                  mt-2
                  text-2xl
                  font-semibold
                  text-[#22243A]
                "
              >
                {stakeholders.length}
              </p>

            </CardContent>

          </Card>


          <Card
            className="
              border-[#DDD8FF]
              bg-[#FBFAFF]
              shadow-sm
            "
          >

            <CardContent
              className="
                p-5
              "
            >

              <p
                className="
                  text-xs
                  font-medium
                  text-slate-500
                "
              >
                Selected
              </p>

              <p
                className="
                  mt-2
                  text-2xl
                  font-semibold
                  text-[#4A3FD6]
                "
              >
                {selectedCount}
              </p>

            </CardContent>

          </Card>


          <Card
            className="
              border-slate-200
              shadow-sm
            "
          >

            <CardContent
              className="
                p-5
              "
            >

              <p
                className="
                  text-xs
                  font-medium
                  text-slate-500
                "
              >
                Invitations Sent This Session
              </p>

              <p
                className="
                  mt-2
                  text-2xl
                  font-semibold
                  text-[#22243A]
                "
              >
                {invitations.length}
              </p>

            </CardContent>

          </Card>

        </div>


        {/* ==================================================
            STAKEHOLDER SELECTION
        ================================================== */}

        <Card
          className="
            border-slate-200
            shadow-sm
          "
        >

          <CardHeader
            className="
              px-6
              py-5
            "
          >

            <div
              className="
                flex
                flex-col
                gap-3
                sm:flex-row
                sm:items-center
                sm:justify-between
              "
            >

              <div>

                <CardTitle
                  className="
                    text-base
                    font-semibold
                    text-[#22243A]
                  "
                >
                  Select Stakeholders
                </CardTitle>

                <CardDescription>
                  Choose who should receive a unique
                  survey invitation.
                </CardDescription>

              </div>


              <Badge
                variant="outline"
                className="
                  w-fit
                "
              >
                {selectedCount} selected
              </Badge>

            </div>

          </CardHeader>


          <Separator />


          <CardContent
            className="
              p-0
            "
          >

            {stakeholders.length === 0 ? (

              <div
                className="
                  flex
                  flex-col
                  items-center
                  justify-center
                  px-6
                  py-14
                  text-center
                "
              >

                <Users
                  className="
                    mb-4
                    h-7
                    w-7
                    text-slate-400
                  "
                />

                <p
                  className="
                    text-sm
                    font-semibold
                    text-[#22243A]
                  "
                >
                  No stakeholders found
                </p>

                <p
                  className="
                    mt-1
                    max-w-md
                    text-xs
                    leading-5
                    text-slate-500
                  "
                >
                  Add stakeholders to this assessment
                  before sending survey invitations.
                </p>

              </div>

            ) : (

             <div className="space-y-2 p-4">
  {Object.entries(
    groupedStakeholders
  ).map(
    ([
      groupId,
      groupStakeholders,
    ]) => {
      const isExpanded =
        expandedGroups.has(
          groupId
        );

      const selectedGroupCount =
        groupStakeholders.filter(
          (stakeholder) =>
            selectedStakeholderIds.has(
              stakeholder.id
            )
        ).length;

      const allGroupSelected =
        groupStakeholders.length >
          0 &&
        selectedGroupCount ===
          groupStakeholders.length;

      const someGroupSelected =
        selectedGroupCount > 0 &&
        !allGroupSelected;

      /*
       * If your stakeholder type now contains
       * group_name, use it here.
       *
       * Otherwise replace this with the
       * group name resolved from your groups API.
       */
      const groupName =
        groupStakeholders[0]
          ?.group_name ??
        "Stakeholder Group";

      return (
        <div
          key={groupId}
          className="
            overflow-hidden
            rounded-xl
            border
            border-slate-200
            bg-white
          "
        >
          {/* =================================================
              GROUP HEADER
          ================================================= */}

          <div
            className={`
              flex
              items-center
              justify-between
              gap-3
              px-4
              py-3
              transition-colors
              ${
                isExpanded
                  ? "bg-[#FBFAFF]"
                  : "hover:bg-slate-50"
              }
            `}
          >
            {/* Expand / Collapse */}
            <button
              type="button"
              onClick={() =>
                toggleGroup(
                  groupId
                )
              }
              className="
                flex
                min-w-0
                flex-1
                items-center
                gap-3
                text-left
              "
            >
              <span
                className="
                  flex
                  h-8
                  w-8
                  shrink-0
                  items-center
                  justify-center
                  rounded-lg
                  bg-[#F1EFFF]
                  text-[#4A3FD6]
                "
              >
                {isExpanded ? (
                  <ChevronDown
                    className="
                      h-4
                      w-4
                    "
                  />
                ) : (
                  <ChevronRight
                    className="
                      h-4
                      w-4
                    "
                  />
                )}
              </span>

              <span className="min-w-0">
                <span
                  className="
                    block
                    truncate
                    text-sm
                    font-semibold
                    text-[#22243A]
                  "
                >
                  {groupName}
                </span>

                <span
                  className="
                    mt-0.5
                    block
                    text-xs
                    text-slate-500
                  "
                >
                  {groupStakeholders.length}{" "}
                  {groupStakeholders.length ===
                  1
                    ? "stakeholder"
                    : "stakeholders"}
                </span>
              </span>
            </button>

            {/* Group selection */}
            <div
              className="
                flex
                shrink-0
                items-center
                gap-3
              "
            >
              <Badge
                variant="outline"
                className="
                  border-slate-200
                  bg-white
                  text-slate-600
                "
              >
                {selectedGroupCount}/
                {groupStakeholders.length}
              </Badge>

              <Checkbox
                checked={
                  allGroupSelected
                    ? true
                    : someGroupSelected
                      ? "indeterminate"
                      : false
                }
                onCheckedChange={() =>
                  toggleGroupStakeholders(
                    groupStakeholders
                  )
                }
                aria-label={`Select all stakeholders in ${groupName}`}
              />
            </div>
          </div>

          {/* =================================================
              EXPANDED STAKEHOLDERS
          ================================================= */}

          {isExpanded && (
            <div
              className="
                border-t
                border-slate-100
                bg-slate-50/50
              "
            >
              {groupStakeholders.map(
                (stakeholder) => {
                  const selected =
                    selectedStakeholderIds.has(
                      stakeholder.id
                    );

                  return (
                    <div
                      key={
                        stakeholder.id
                      }
                      className={`
                        flex
                        items-center
                        gap-4
                        border-b
                        border-slate-100
                        px-4
                        py-3
                        last:border-b-0
                        ${
                          selected
                            ? "bg-[#FBFAFF]"
                            : "bg-white"
                        }
                      `}
                    >
                      {/* Individual checkbox */}
                      <Checkbox
                        checked={
                          selected
                        }
                        onCheckedChange={() =>
                          toggleStakeholder(
                            stakeholder.id
                          )
                        }
                        aria-label={`Select ${stakeholder.name}`}
                      />

                      {/* Avatar */}
                      <div
                        className="
                          flex
                          h-9
                          w-9
                          shrink-0
                          items-center
                          justify-center
                          rounded-full
                          bg-[#F1EFFF]
                          text-sm
                          font-semibold
                          text-[#4A3FD6]
                        "
                      >
                        {stakeholder.name
                          .charAt(0)
                          .toUpperCase()}
                      </div>

                      {/* Details */}
                      <div className="min-w-0 flex-1">
                        <p
                          className="
                            truncate
                            text-sm
                            font-medium
                            text-[#22243A]
                          "
                        >
                          {stakeholder.name}
                        </p>

                        <div
                          className="
                            mt-0.5
                            flex
                            flex-col
                            gap-0.5
                            sm:flex-row
                            sm:items-center
                            sm:gap-2
                          "
                        >
                          <span
                            className="
                              truncate
                              text-xs
                              text-slate-500
                            "
                          >
                            {
                              stakeholder.email
                            }
                          </span>

                          {stakeholder.designation && (
                            <>
                              <span className="hidden text-slate-300 sm:inline">
                                •
                              </span>

                              <span
                                className="
                                  truncate
                                  text-xs
                                  text-slate-500
                                "
                              >
                                {
                                  stakeholder.designation
                                }
                              </span>
                            </>
                          )}
                        </div>

                        {stakeholder.organisation && (
                          <p
                            className="
                              mt-0.5
                              truncate
                              text-[11px]
                              text-slate-400
                            "
                          >
                            {
                              stakeholder.organisation
                            }
                          </p>
                        )}
                      </div>

                      {/* Selected indicator */}
                      {selected && (
                        <Check
                          className="
                            h-4
                            w-4
                            shrink-0
                            text-emerald-600
                          "
                        />
                      )}
                    </div>
                  );
                }
              )}
            </div>
          )}
        </div>
      );
    }
  )}
</div>

              
            )}

          </CardContent>

        </Card>
                {/* ==================================================
            INVITATION RESULTS
        ================================================== */}

        {invitations.length > 0 && (

          <Card
            className="
              border-emerald-200
              shadow-sm
            "
          >

            <CardHeader
              className="
                px-6
                py-5
              "
            >

              <div
                className="
                  flex
                  flex-col
                  gap-2
                  sm:flex-row
                  sm:items-center
                  sm:justify-between
                "
              >

                <div>

                  <CardTitle
                    className="
                      text-base
                      font-semibold
                      text-[#22243A]
                    "
                  >
                    Invitation Results
                  </CardTitle>

                  <CardDescription>
                    Survey links returned for the
                    invitations sent in this session.
                  </CardDescription>

                </div>


                <Badge
                  variant="outline"
                  className="
                    w-fit
                    border-emerald-200
                    bg-emerald-50
                    text-emerald-700
                  "
                >
                  {invitations.length} sent
                </Badge>

              </div>

            </CardHeader>


            <Separator />


            <CardContent
              className="
                p-0
              "
            >

              <div
                className="
                  overflow-x-auto
                "
              >

                <table
                  className="
                    w-full
                    min-w-[820px]
                    text-sm
                  "
                >

                  <thead>

                    <tr
                      className="
                        border-b
                        border-slate-200
                        bg-slate-50
                      "
                    >

                      <th
                        className="
                          px-6
                          py-3
                          text-left
                          text-xs
                          font-medium
                          text-slate-500
                        "
                      >
                        Stakeholder
                      </th>

                      <th
                        className="
                          px-4
                          py-3
                          text-left
                          text-xs
                          font-medium
                          text-slate-500
                        "
                      >
                        Email
                      </th>

                      <th
                        className="
                          px-4
                          py-3
                          text-left
                          text-xs
                          font-medium
                          text-slate-500
                        "
                      >
                        Status
                      </th>

                      <th
                        className="
                          px-6
                          py-3
                          text-right
                          text-xs
                          font-medium
                          text-slate-500
                        "
                      >
                        Action
                      </th>

                    </tr>

                  </thead>


                  <tbody
                    className="
                      divide-y
                      divide-slate-100
                    "
                  >

                    {invitations.map(
                      (
                        invitation
                      ) => (

                        <tr
                          key={
                            invitation.id
                          }
                          className="
                            transition-colors
                            hover:bg-slate-50/60
                          "
                        >

                          <td
                            className="
                              px-6
                              py-4
                            "
                          >

                            <p
                              className="
                                font-medium
                                text-[#22243A]
                              "
                            >
                              {
                                invitation
                                  .stakeholder_name
                              }
                            </p>

                          </td>


                          <td
                            className="
                              px-4
                              py-4
                              text-slate-600
                            "
                          >
                            {
                              invitation
                                .stakeholder_email
                            }
                          </td>


                          <td
                            className="
                              px-4
                              py-4
                            "
                          >

                            <Badge
                              variant="outline"
                              className="
                                border-blue-200
                                bg-blue-50
                                text-blue-700
                              "
                            >
                              {
                                invitation.status
                              }
                            </Badge>

                          </td>


                          <td
                            className="
                              px-6
                              py-4
                              text-right
                            "
                          >

                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="
                                gap-2
                              "
                              onClick={() =>
                                handleCopyLink(
                                  invitation.survey_url
                                )
                              }
                            >

                              <Copy
                                className="
                                  h-3.5
                                  w-3.5
                                "
                              />

                              Copy Link

                            </Button>

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            </CardContent>

          </Card>

        )}


        {/* ==================================================
            SEND INVITATION DIALOG
        ================================================== */}

        <Dialog
          open={
            sendDialogOpen
          }
          onOpenChange={(
            open
          ) => {

            if (
              !open &&
              !sending
            ) {

              setSendDialogOpen(
                false
              );

            }

          }}
        >

          <DialogContent
            className="
              w-[95vw]
              max-w-lg
              border-slate-200
              bg-white
              p-0
            "
          >

            <DialogHeader
              className="
                border-b
                border-slate-200
                px-6
                py-5
              "
            >

              <div
                className="
                  flex
                  items-start
                  gap-3
                "
              >

                <div
                  className="
                    flex
                    h-10
                    w-10
                    shrink-0
                    items-center
                    justify-center
                    rounded-lg
                    bg-[#F1EFFF]
                    text-[#4A3FD6]
                  "
                >

                  <Send
                    className="
                      h-5
                      w-5
                    "
                  />

                </div>


                <div>

                  <DialogTitle
                    className="
                      text-lg
                      font-semibold
                      text-[#22243A]
                    "
                  >
                    Send Survey Invitations
                  </DialogTitle>

                  <DialogDescription>
                    You have selected{" "}
                    <span
                      className="
                        font-semibold
                        text-[#22243A]
                      "
                    >
                      {selectedCount}
                    </span>{" "}
                    stakeholder
                    {selectedCount === 1
                      ? ""
                      : "s"}.
                  </DialogDescription>

                </div>

              </div>

            </DialogHeader>


            <div
              className="
                space-y-4
                px-6
                py-6
              "
            >

              <div
                className="
                  rounded-lg
                  border
                  border-slate-200
                  bg-slate-50
                  px-4
                  py-3
                "
              >

                <p
                  className="
                    text-xs
                    font-medium
                    text-slate-600
                  "
                >
                  Selected stakeholders
                </p>

                <div
                  className="
                    mt-3
                    max-h-40
                    space-y-2
                    overflow-y-auto
                  "
                >

                  {selectedStakeholders.map(
                    (
                      stakeholder
                    ) => (

                      <div
                        key={
                          stakeholder.id
                        }
                        className="
                          flex
                          items-center
                          justify-between
                          gap-3
                          rounded-md
                          bg-white
                          px-3
                          py-2
                        "
                      >

                        <div
                          className="
                            min-w-0
                          "
                        >

                          <p
                            className="
                              truncate
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
                              truncate
                              text-xs
                              text-slate-500
                            "
                          >
                            {
                              stakeholder.email
                            }
                          </p>

                        </div>

                        <Check
                          className="
                            h-4
                            w-4
                            shrink-0
                            text-emerald-600
                          "
                        />

                      </div>

                    )
                  )}

                </div>

              </div>


              <div
                className="
                  flex
                  items-start
                  gap-3
                  rounded-lg
                  border
                  border-[#DDD8FF]
                  bg-[#FBFAFF]
                  px-4
                  py-3
                "
              >

                <Mail
                  className="
                    mt-0.5
                    h-4
                    w-4
                    shrink-0
                    text-[#4A3FD6]
                  "
                />

                <p
                  className="
                    text-xs
                    leading-5
                    text-slate-600
                  "
                >
                  Each selected stakeholder will
                  receive their own unique survey
                  invitation link.
                </p>

              </div>


              <div
                className="
                  flex
                  items-start
                  gap-3
                  rounded-lg
                  border
                  border-amber-200
                  bg-amber-50
                  px-4
                  py-3
                "
              >

                <AlertCircle
                  className="
                    mt-0.5
                    h-4
                    w-4
                    shrink-0
                    text-amber-600
                  "
                />

                <p
                  className="
                    text-xs
                    leading-5
                    text-amber-700
                  "
                >
                  Make sure the survey content is
                  ready before sending invitations.
                </p>

              </div>

            </div>


            <DialogFooter
              className="
                border-t
                border-slate-100
                px-6
                py-4
              "
            >

              <Button
                type="button"
                variant="outline"
                disabled={
                  sending
                }
                onClick={() =>
                  setSendDialogOpen(
                    false
                  )
                }
              >
                Cancel
              </Button>


              <Button
                type="button"
                disabled={
                  sending ||
                  selectedCount === 0
                }
                onClick={
                  handleSendInvitations
                }
                className="
                  gap-2
                  bg-[#4A3FD6]
                  text-white
                  hover:bg-[#3F34C2]
                "
              >

                {sending ? (
                  <Loader2
                    className="
                      h-4
                      w-4
                      animate-spin
                    "
                  />
                ) : (
                  <Send
                    className="
                      h-4
                      w-4
                    "
                  />
                )}

                {sending
                  ? "Sending..."
                  : "Send Invitations"}

              </Button>

            </DialogFooter>

          </DialogContent>

        </Dialog>

      </div>
    </AppShell>
  );
}