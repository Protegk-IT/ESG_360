import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useParams } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";

import SurveyApi from "@/api/materiality/surveyApi";

import type {
  SurveyInvitationResult,
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
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

import {
  AlertCircle,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  Copy,
  Loader2,
  Mail,
  RefreshCw,
  Send,
  TrendingUp,
  Users,
  UserCheck,
  UserX,
} from "lucide-react";

import {
  toast,
} from "sonner";


/* ==========================================================
   DASHBOARD STATUS
========================================================== */

type ResponseState =
  | "COMPLETED"
  | "PENDING"
  | "FAILED"
  | "UNKNOWN";


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
  ] = useState<Survey | null>(null);


  /* ========================================================
     STAKEHOLDERS
  ======================================================== */

  const [
    stakeholders,
    setStakeholders,
  ] = useState<Stakeholder[]>([]);


  /* ========================================================
     INVITATIONS / RESPONSE DATA
  ======================================================== */

  const [
    invitations,
    setInvitations,
  ] = useState<SurveyInvitationResult[]>([]);


  /* ========================================================
     SELECTION
  ======================================================== */

  const [
    selectedStakeholderIds,
    setSelectedStakeholderIds,
  ] = useState<Set<string>>(
    new Set()
  );


  const [
    expandedGroups,
    setExpandedGroups,
  ] = useState<Set<string>>(
    new Set()
  );


  /* ========================================================
     UI STATE
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


  const [
    sendDialogOpen,
    setSendDialogOpen,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState<string | null>(null);


  /* ========================================================
     STATUS NORMALIZER
  ======================================================== */

  const getResponseState = useCallback(
    (
      status?: string | null
    ): ResponseState => {

      const normalized =
        String(status ?? "")
          .trim()
          .toUpperCase()
          .replace(/[\s-]+/g, "_");


      if (
        [
          "COMPLETED",
          "SUBMITTED",
          "RESPONDED",
          "RESPONSE_RECEIVED",
          "SURVEY_COMPLETED",
        ].includes(normalized)
      ) {
        return "COMPLETED";
      }


      if (
        [
          "FAILED",
          "BOUNCED",
          "EXPIRED",
          "DELIVERY_FAILED",
        ].includes(normalized)
      ) {
        return "FAILED";
      }


      if (
        [
          "SENT",
          "PENDING",
          "INVITED",
          "DELIVERED",
          "OPENED",
          "IN_PROGRESS",
        ].includes(normalized)
      ) {
        return "PENDING";
      }


      return "UNKNOWN";
    },
    []
  );


  /* ========================================================
     LOAD SURVEY
  ======================================================== */

  const loadSurvey = useCallback(
    async () => {

      if (!id) {
        return;
      }

      const response =
        await SurveyApi.getSurvey(id);

      setSurvey(
        response.data
      );
    },
    [id]
  );


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
          await SurveyApi.getStakeholders(id);

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

        } catch (err) {

          console.error(
            "Failed to load survey dashboard:",
            err
          );

          setError(
            "Unable to load survey dashboard."
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

      } catch (err) {

        console.error(
          "Failed to refresh survey dashboard:",
          err
        );

        toast.error(
          "Unable to refresh survey dashboard."
        );

      } finally {

        setRefreshing(false);

      }
    };


  /* ========================================================
     GROUP STAKEHOLDERS
  ======================================================== */

  const groupedStakeholders =
    useMemo(() => {

      return stakeholders.reduce<
        Record<string, Stakeholder[]>
      >(
        (
          groups,
          stakeholder
        ) => {

          const groupId =
            stakeholder.group;

          if (!groups[groupId]) {
            groups[groupId] = [];
          }

          groups[groupId].push(
            stakeholder
          );

          return groups;

        },
        {}
      );

    }, [stakeholders]);


  /* ========================================================
     INVITATION MAP
  ======================================================== */

  const invitationByStakeholder =
    useMemo(() => {

      const map =
        new Map<
          string,
          SurveyInvitationResult
        >();

      invitations.forEach(
        (invitation) => {

          const stakeholderId =
            (invitation as SurveyInvitationResult & {
              stakeholder_id?: string;
            }).stakeholder_id;

          if (stakeholderId) {
            map.set(
              stakeholderId,
              invitation
            );
          }

        }
      );

      return map;

    }, [invitations]);


  /* ========================================================
     DASHBOARD METRICS
  ======================================================== */

  const metrics =
    useMemo(() => {

      const invited =
        invitations.length;

      const completed =
        invitations.filter(
          (invitation) =>
            getResponseState(
              invitation.status
            ) === "COMPLETED"
        ).length;

      const failed =
        invitations.filter(
          (invitation) =>
            getResponseState(
              invitation.status
            ) === "FAILED"
        ).length;

      const pending =
        invitations.filter(
          (invitation) =>
            getResponseState(
              invitation.status
            ) === "PENDING" ||
            getResponseState(
              invitation.status
            ) === "UNKNOWN"
        ).length;


      const responseRate =
        invited > 0
          ? (completed / invited) * 100
          : 0;


      const deliveryRate =
        invited > 0
          ? ((invited - failed) / invited) * 100
          : 0;


      const pendingRate =
        invited > 0
          ? (pending / invited) * 100
          : 0;


      return {
        invited,
        completed,
        pending,
        failed,
        responseRate,
        deliveryRate,
        pendingRate,
      };

    }, [
      invitations,
      getResponseState,
    ]);
      /* ========================================================
     GROUP RESPONSE ANALYTICS
  ======================================================== */

  const groupAnalytics =
    useMemo(() => {

      return Object.entries(
        groupedStakeholders
      ).map(
        ([
          groupId,
          groupStakeholders,
        ]) => {

          const groupInvitations =
            groupStakeholders
              .map(
                (stakeholder) =>
                  invitationByStakeholder.get(
                    stakeholder.id
                  )
              )
              .filter(
                (
                  invitation
                ): invitation is SurveyInvitationResult =>
                  Boolean(invitation)
              );


          const invited =
            groupInvitations.length;


          const completed =
            groupInvitations.filter(
              (invitation) =>
                getResponseState(
                  invitation.status
                ) === "COMPLETED"
            ).length;


          const pending =
            groupInvitations.filter(
              (invitation) =>
                getResponseState(
                  invitation.status
                ) === "PENDING" ||
                getResponseState(
                  invitation.status
                ) === "UNKNOWN"
            ).length;


          const failed =
            groupInvitations.filter(
              (invitation) =>
                getResponseState(
                  invitation.status
                ) === "FAILED"
            ).length;


          const responseRate =
            invited > 0
              ? (completed / invited) * 100
              : 0;


          const groupName =
            groupStakeholders[0]
              ?.group_name ??
            "Stakeholder Group";


          return {
            groupId,
            groupName,
            totalStakeholders:
              groupStakeholders.length,
            invited,
            completed,
            pending,
            failed,
            responseRate,
          };
        }
      );

    }, [
      groupedStakeholders,
      invitationByStakeholder,
      getResponseState,
    ]);


  /* ========================================================
     SELECTION
  ======================================================== */

  const toggleStakeholder =
    (
      stakeholderId: string
    ) => {

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
     GROUP TOGGLE
  ======================================================== */

  const toggleGroup =
    (
      groupId: string
    ) => {

      setExpandedGroups(
        (previous) => {

          const next =
            new Set(previous);


          if (
            next.has(groupId)
          ) {

            next.delete(groupId);

          } else {

            next.add(groupId);

          }


          return next;
        }
      );
    };


  /* ========================================================
     GROUP SELECTION
  ======================================================== */

  const toggleGroupStakeholders =
    (
      groupStakeholders: Stakeholder[]
    ) => {

      const ids =
        groupStakeholders.map(
          (stakeholder) =>
            stakeholder.id
        );


      const allSelected =
        ids.length > 0 &&
        ids.every(
          (stakeholderId) =>
            selectedStakeholderIds.has(
              stakeholderId
            )
        );


      setSelectedStakeholderIds(
        (previous) => {

          const next =
            new Set(previous);


          if (allSelected) {

            ids.forEach(
              (stakeholderId) =>
                next.delete(
                  stakeholderId
                )
            );

          } else {

            ids.forEach(
              (stakeholderId) =>
                next.add(
                  stakeholderId
                )
            );

          }


          return next;
        }
      );
    };


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


  const selectedCount =
    selectedStakeholderIds.size;


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

      } catch (err) {

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

      } catch (err) {

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
     RESPONSE STATUS UI
  ======================================================== */

  const getStatusBadge =
    (
      status?: string | null
    ) => {

      const state =
        getResponseState(status);


      if (state === "COMPLETED") {

        return (
          <Badge
            className="
              border-emerald-200
              bg-emerald-50
              text-emerald-700
              hover:bg-emerald-50
            "
          >
            <Check className="mr-1 h-3.5 w-3.5" />
            Completed
          </Badge>
        );
      }


      if (state === "FAILED") {

        return (
          <Badge
            className="
              border-red-200
              bg-red-50
              text-red-700
              hover:bg-red-50
            "
          >
            <UserX className="mr-1 h-3.5 w-3.5" />
            Failed
          </Badge>
        );
      }


      return (
        <Badge
          className="
            border-amber-200
            bg-amber-50
            text-amber-700
            hover:bg-amber-50
          "
        >
          <Clock3 className="mr-1 h-3.5 w-3.5" />
          Pending
        </Badge>
      );
    };


  /* ========================================================
     MISSING ID
  ======================================================== */

  if (!id) {

    return (
      <AppShell
        title="Survey Dashboard"
        description="Monitor survey distribution and stakeholder responses."
      >

        <Alert variant="destructive">

          <AlertCircle className="h-4 w-4" />

          <AlertTitle>
            Assessment ID is missing
          </AlertTitle>

          <AlertDescription>
            A valid assessment is required to
            display the survey dashboard.
          </AlertDescription>

        </Alert>

      </AppShell>
    );
  }


  /* ========================================================
     LOADING
  ======================================================== */

  if (loading) {

    return (
      <AppShell
        title="Survey Dashboard"
        description="Monitor survey distribution and stakeholder responses."
      >

        <div
          className="
            flex
            min-h-[520px]
            items-center
            justify-center
          "
        >

          <div className="flex flex-col items-center gap-3">

            <Loader2
              className="
                h-8
                w-8
                animate-spin
                text-[#4A3FD6]
              "
            />

            <p className="text-sm text-slate-500">
              Loading survey dashboard...
            </p>

          </div>

        </div>

      </AppShell>
    );
  }
    return (
    <AppShell
      title="Survey Distribution & Response Dashboard"
      description="Monitor stakeholder invitations, response rates, and survey completion across groups."
    >

      <div className="space-y-6">


        {/* ==================================================
            PAGE HEADER
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

              <BarChart3
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
              Survey Distribution & Response
            </h1>


            <p
              className="
                mt-1
                max-w-3xl
                text-sm
                leading-6
                text-slate-500
              "
            >
              Track invitation delivery, stakeholder
              participation, response progress and
              group-level completion.
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
              disabled={refreshing}
              onClick={handleRefresh}
              className="gap-2"
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
                setSendDialogOpen(true)
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

          <Alert variant="destructive">

            <AlertCircle className="h-4 w-4" />

            <AlertTitle>
              Dashboard unavailable
            </AlertTitle>

            <AlertDescription>
              {error}
            </AlertDescription>

          </Alert>

        )}


        {/* ==================================================
            SURVEY OVERVIEW HERO
        ================================================== */}

        <Card
          className="
            overflow-hidden
            border-[#DDD8FF]
            bg-gradient-to-br
            from-[#FBFAFF]
            via-white
            to-[#F6F7FF]
            shadow-sm
          "
        >

          <CardContent className="p-6">

            <div
              className="
                flex
                flex-col
                gap-6
                lg:flex-row
                lg:items-center
                lg:justify-between
              "
            >

              <div className="min-w-0">

                <div
                  className="
                    flex
                    items-center
                    gap-2
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
                      rounded-xl
                      bg-[#4A3FD6]
                      text-white
                      shadow-sm
                    "
                  >

                    <ClipboardCheck
                      className="
                        h-5
                        w-5
                      "
                    />

                  </div>


                  <div className="min-w-0">

                    <p
                      className="
                        truncate
                        text-base
                        font-semibold
                        text-[#22243A]
                      "
                    >
                      {survey?.title ??
                        "Materiality Survey"}
                    </p>

                    <p
                      className="
                        mt-0.5
                        text-xs
                        text-slate-500
                      "
                    >
                      Stakeholder response monitoring
                    </p>

                  </div>

                </div>


                <div
                  className="
                    mt-5
                    max-w-xl
                  "
                >

                  <div
                    className="
                      flex
                      items-end
                      justify-between
                      gap-4
                    "
                  >

                    <div>

                      <p
                        className="
                          text-xs
                          font-medium
                          uppercase
                          tracking-wide
                          text-slate-500
                        "
                      >
                        Overall Response Rate
                      </p>

                      <p
                        className="
                          mt-1
                          text-4xl
                          font-bold
                          tracking-tight
                          text-[#22243A]
                        "
                      >
                        {metrics.responseRate.toFixed(1)}%
                      </p>

                    </div>


                    <Badge
                      className="
                        border-[#DDD8FF]
                        bg-white
                        text-[#4A3FD6]
                        hover:bg-white
                      "
                    >
                      {metrics.completed} of{" "}
                      {metrics.invited} responded
                    </Badge>

                  </div>


                  <div
                    className="
                      mt-4
                      h-3
                      overflow-hidden
                      rounded-full
                      bg-slate-200
                    "
                  >

                    <div
                      className="
                        h-full
                        rounded-full
                        bg-[#4A3FD6]
                        transition-all
                        duration-500
                      "
                      style={{
                        width: `${Math.min(
                          metrics.responseRate,
                          100
                        )}%`,
                      }}
                    />

                  </div>


                  <div
                    className="
                      mt-2
                      flex
                      justify-between
                      text-xs
                      text-slate-500
                    "
                  >

                    <span>
                      {metrics.completed} completed
                    </span>

                    <span>
                      {metrics.pending} pending
                    </span>

                  </div>

                </div>

              </div>


              {/* HERO CALCULATIONS */}

              <div
                className="
                  grid
                  grid-cols-2
                  gap-3
                  sm:grid-cols-4
                  lg:min-w-[470px]
                "
              >

                <div
                  className="
                    rounded-xl
                    border
                    border-white
                    bg-white/80
                    p-4
                    shadow-sm
                  "
                >

                  <Users
                    className="
                      h-4
                      w-4
                      text-[#4A3FD6]
                    "
                  />

                  <p
                    className="
                      mt-3
                      text-2xl
                      font-bold
                      text-[#22243A]
                    "
                  >
                    {metrics.invited}
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      text-slate-500
                    "
                  >
                    Invited
                  </p>

                </div>


                <div
                  className="
                    rounded-xl
                    border
                    border-white
                    bg-white/80
                    p-4
                    shadow-sm
                  "
                >

                  <UserCheck
                    className="
                      h-4
                      w-4
                      text-emerald-600
                    "
                  />

                  <p
                    className="
                      mt-3
                      text-2xl
                      font-bold
                      text-[#22243A]
                    "
                  >
                    {metrics.completed}
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      text-slate-500
                    "
                  >
                    Responded
                  </p>

                </div>


                <div
                  className="
                    rounded-xl
                    border
                    border-white
                    bg-white/80
                    p-4
                    shadow-sm
                  "
                >

                  <Clock3
                    className="
                      h-4
                      w-4
                      text-amber-600
                    "
                  />

                  <p
                    className="
                      mt-3
                      text-2xl
                      font-bold
                      text-[#22243A]
                    "
                  >
                    {metrics.pending}
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      text-slate-500
                    "
                  >
                    Pending
                  </p>

                </div>


                <div
                  className="
                    rounded-xl
                    border
                    border-white
                    bg-white/80
                    p-4
                    shadow-sm
                  "
                >

                  <TrendingUp
                    className="
                      h-4
                      w-4
                      text-blue-600
                    "
                  />

                  <p
                    className="
                      mt-3
                      text-2xl
                      font-bold
                      text-[#22243A]
                    "
                  >
                    {metrics.deliveryRate.toFixed(0)}%
                  </p>

                  <p
                    className="
                      mt-1
                      text-xs
                      text-slate-500
                    "
                  >
                    Delivery Rate
                  </p>

                </div>

              </div>

            </div>

          </CardContent>

        </Card>


        {/* ==================================================
            KPI CARDS
        ================================================== */}

        <div
          className="
            grid
            gap-4
            sm:grid-cols-2
            xl:grid-cols-4
          "
        >

          {/* RESPONSE RATE */}

          <Card className="border-slate-200 shadow-sm">

            <CardContent className="p-5">

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <p
                  className="
                    text-sm
                    font-medium
                    text-slate-500
                  "
                >
                  Response Rate
                </p>

                <div
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-lg
                    bg-[#F1EFFF]
                    text-[#4A3FD6]
                  "
                >
                  <BarChart3 className="h-4 w-4" />
                </div>

              </div>


              <p
                className="
                  mt-4
                  text-3xl
                  font-bold
                  text-[#22243A]
                "
              >
                {metrics.responseRate.toFixed(1)}%
              </p>


              <div
                className="
                  mt-3
                  h-2
                  rounded-full
                  bg-slate-100
                "
              >

                <div
                  className="
                    h-2
                    rounded-full
                    bg-emerald-500
                  "
                  style={{
                    width: `${Math.min(
                      metrics.responseRate,
                      100
                    )}%`,
                  }}
                />

              </div>


              <p
                className="
                  mt-2
                  text-xs
                  text-slate-500
                "
              >
                Completed ÷ Invited × 100
              </p>

            </CardContent>

          </Card>


          {/* PENDING */}

          <Card className="border-slate-200 shadow-sm">

            <CardContent className="p-5">

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <p
                  className="
                    text-sm
                    font-medium
                    text-slate-500
                  "
                >
                  Pending Responses
                </p>

                <div
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-lg
                    bg-amber-50
                    text-amber-600
                  "
                >
                  <Clock3 className="h-4 w-4" />
                </div>

              </div>


              <p
                className="
                  mt-4
                  text-3xl
                  font-bold
                  text-[#22243A]
                "
              >
                {metrics.pending}
              </p>


              <p
                className="
                  mt-2
                  text-xs
                  text-slate-500
                "
              >
                {metrics.pendingRate.toFixed(1)}%
                of invited stakeholders
              </p>

            </CardContent>

          </Card>


          {/* FAILED */}

          <Card className="border-slate-200 shadow-sm">

            <CardContent className="p-5">

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <p
                  className="
                    text-sm
                    font-medium
                    text-slate-500
                  "
                >
                  Failed Invitations
                </p>

                <div
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-lg
                    bg-red-50
                    text-red-600
                  "
                >
                  <UserX className="h-4 w-4" />
                </div>

              </div>


              <p
                className="
                  mt-4
                  text-3xl
                  font-bold
                  text-[#22243A]
                "
              >
                {metrics.failed}
              </p>


              <p
                className="
                  mt-2
                  text-xs
                  text-slate-500
                "
              >
                Delivery issues requiring attention
              </p>

            </CardContent>

          </Card>


          {/* COMPLETION */}

          <Card className="border-slate-200 shadow-sm">

            <CardContent className="p-5">

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <p
                  className="
                    text-sm
                    font-medium
                    text-slate-500
                  "
                >
                  Completion Progress
                </p>

                <div
                  className="
                    flex
                    h-9
                    w-9
                    items-center
                    justify-center
                    rounded-lg
                    bg-emerald-50
                    text-emerald-600
                  "
                >
                  <ClipboardCheck className="h-4 w-4" />
                </div>

              </div>


              <p
                className="
                  mt-4
                  text-3xl
                  font-bold
                  text-[#22243A]
                "
              >
                {metrics.completed}/
                {metrics.invited}
              </p>


              <p
                className="
                  mt-2
                  text-xs
                  text-slate-500
                "
              >
                {metrics.responseRate.toFixed(1)}%
                assessment completion
              </p>

            </CardContent>

          </Card>

        </div>


        {/* ==================================================
            RESPONSE BREAKDOWN + GROUP ANALYTICS
        ================================================== */}

        <div
          className="
            grid
            gap-6
            xl:grid-cols-[0.85fr_1.15fr]
          "
        >

          {/* RESPONSE BREAKDOWN */}

          <Card className="border-slate-200 shadow-sm px-4">

            <CardHeader>

              <CardTitle
                className="
                  text-base
                  font-semibold
                  text-[#22243A]
                "
              >
                Response Breakdown
              </CardTitle>

              <CardDescription>
                Current survey participation status.
              </CardDescription>

            </CardHeader>


            <Separator />


            <CardContent className="p-6">

              <div
                className="
                  flex
                  flex-col
                  items-center
                  gap-6
                  sm:flex-row
                  sm:items-center
                "
              >

                {/* DONUT */}

                <div
                  className="
                    relative
                    flex
                    h-40
                    w-40
                    shrink-0
                    items-center
                    justify-center
                    rounded-full
                  "
                  style={{
                    background:
                      `conic-gradient(
                        #4A3FD6 ${metrics.responseRate}%,
                        #F59E0B ${metrics.responseRate}% ${
                          metrics.responseRate +
                          metrics.pendingRate
                        }%,
                        #E5E7EB ${
                          metrics.responseRate +
                          metrics.pendingRate
                        }% 100%
                      )`,
                  }}
                >

                  <div
                    className="
                      flex
                      h-28
                      w-28
                      flex-col
                      items-center
                      justify-center
                      rounded-full
                      bg-white
                    "
                  >

                    <span
                      className="
                        text-2xl
                        font-bold
                        text-[#22243A]
                      "
                    >
                      {metrics.responseRate.toFixed(0)}%
                    </span>

                    <span
                      className="
                        text-[11px]
                        text-slate-500
                      "
                    >
                      Response
                    </span>

                  </div>

                </div>


                <div className="w-full space-y-4">

                  <div
                    className="
                      flex
                      items-center
                      justify-between
                    "
                  >

                    <div
                      className="
                        flex
                        items-center
                        gap-2
                      "
                    >

                      <span
                        className="
                          h-2.5
                          w-2.5
                          rounded-full
                          bg-[#4A3FD6]
                        "
                      />

                      <span
                        className="
                          text-sm
                          text-slate-600
                        "
                      >
                        Completed
                      </span>

                    </div>

                    <span
                      className="
                        text-sm
                        font-semibold
                        text-[#22243A]
                      "
                    >
                      {metrics.completed}
                    </span>

                  </div>


                  <div
                    className="
                      flex
                      items-center
                      justify-between
                    "
                  >

                    <div
                      className="
                        flex
                        items-center
                        gap-2
                      "
                    >

                      <span
                        className="
                          h-2.5
                          w-2.5
                          rounded-full
                          bg-amber-500
                        "
                      />

                      <span
                        className="
                          text-sm
                          text-slate-600
                        "
                      >
                        Pending
                      </span>

                    </div>

                    <span
                      className="
                        text-sm
                        font-semibold
                        text-[#22243A]
                      "
                    >
                      {metrics.pending}
                    </span>

                  </div>


                  <div
                    className="
                      flex
                      items-center
                      justify-between
                    "
                  >

                    <div
                      className="
                        flex
                        items-center
                        gap-2
                      "
                    >

                      <span
                        className="
                          h-2.5
                          w-2.5
                          rounded-full
                          bg-slate-300
                        "
                      />

                      <span
                        className="
                          text-sm
                          text-slate-600
                        "
                      >
                        Failed
                      </span>

                    </div>

                    <span
                      className="
                        text-sm
                        font-semibold
                        text-[#22243A]
                      "
                    >
                      {metrics.failed}
                    </span>

                  </div>


                  <Separator />


                  <p
                    className="
                      text-xs
                      leading-5
                      text-slate-500
                    "
                  >
                    Response rate =
                    completed responses ÷
                    total invitations × 100.
                  </p>

                </div>

              </div>

            </CardContent>

          </Card>


          {/* GROUP ANALYTICS */}

          <Card className="border-slate-200 shadow-sm px-4">

            <CardHeader>

              <CardTitle
                className="
                  text-base
                  font-semibold
                  text-[#22243A]
                "
              >
                Stakeholder Group Response
              </CardTitle>

              <CardDescription>
                Compare participation across stakeholder groups.
              </CardDescription>

            </CardHeader>


            <Separator />


            <CardContent className="space-y-5 p-6">

              {groupAnalytics.length === 0 ? (

                <div
                  className="
                    flex
                    min-h-[180px]
                    items-center
                    justify-center
                    text-center
                  "
                >

                  <div>

                    <Users
                      className="
                        mx-auto
                        h-8
                        w-8
                        text-slate-300
                      "
                    />

                    <p
                      className="
                        mt-3
                        text-sm
                        font-medium
                        text-[#22243A]
                      "
                    >
                      No response data available
                    </p>

                    <p
                      className="
                        mt-1
                        text-xs
                        text-slate-500
                      "
                    >
                      Send invitations to begin tracking responses.
                    </p>

                  </div>

                </div>

              ) : (

                groupAnalytics.map(
                  (group) => (

                    <div
                      key={group.groupId}
                      className="space-y-2"
                    >

                      <div
                        className="
                          flex
                          items-center
                          justify-between
                          gap-4
                        "
                      >

                        <div
                          className="
                            flex
                            min-w-0
                            items-center
                            gap-2
                          "
                        >

                          <div
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
                            <Users className="h-4 w-4" />
                          </div>

                          <div className="min-w-0">

                            <p
                              className="
                                truncate
                                text-sm
                                font-medium
                                text-[#22243A]
                              "
                            >
                              {group.groupName}
                            </p>

                            <p
                              className="
                                text-[11px]
                                text-slate-500
                              "
                            >
                              {group.completed} of{" "}
                              {group.invited} responded
                            </p>

                          </div>

                        </div>


                        <span
                          className="
                            shrink-0
                            text-sm
                            font-semibold
                            text-[#4A3FD6]
                          "
                        >
                          {group.responseRate.toFixed(1)}%
                        </span>

                      </div>


                      <div
                        className="
                          h-2
                          overflow-hidden
                          rounded-full
                          bg-slate-100
                        "
                      >

                        <div
                          className="
                            h-full
                            rounded-full
                            bg-[#4A3FD6]
                            transition-all
                          "
                          style={{
                            width: `${Math.min(
                              group.responseRate,
                              100
                            )}%`,
                          }}
                        />

                      </div>


                      <div
                        className="
                          flex
                          justify-between
                          text-[11px]
                          text-slate-400
                        "
                      >

                        <span>
                          {group.pending} pending
                        </span>

                        <span>
                          {group.failed} failed
                        </span>

                      </div>

                    </div>

                  )
                )

              )}

            </CardContent>

          </Card>

        </div>
                {/* ==================================================
            STAKEHOLDER RESPONSE DETAILS
        ================================================== */}

        <Card className="border-slate-200 shadow-sm px-4">

          <CardHeader>

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
                  Stakeholder Response Details
                </CardTitle>

                <CardDescription>
                  Invitation and response status for each stakeholder.
                </CardDescription>

              </div>


              <Badge
                variant="outline"
                className="
                  w-fit
                  border-[#DDD8FF]
                  bg-[#FBFAFF]
                  text-[#4A3FD6]
                "
              >
                {stakeholders.length} stakeholders
              </Badge>

            </div>

          </CardHeader>


          <Separator />


          <CardContent className="p-0">

            {stakeholders.length === 0 ? (

              <div
                className="
                  flex
                  min-h-[220px]
                  flex-col
                  items-center
                  justify-center
                  px-6
                  text-center
                "
              >

                <Users
                  className="
                    h-8
                    w-8
                    text-slate-300
                  "
                />

                <p
                  className="
                    mt-3
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
                  before distributing the survey.
                </p>

              </div>

            ) : (

              <div
                className="
                  overflow-x-auto
                "
              >

                <table
                  className="
                    w-full
                    min-w-[950px]
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
                        Group
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
                        Response
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
                        Participation
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

                    {stakeholders.map(
                      (stakeholder) => {

                        const invitation =
                          invitationByStakeholder.get(
                            stakeholder.id
                          );


                        const state =
                          getResponseState(
                            invitation?.status
                          );


                        const completed =
                          state === "COMPLETED";


                        return (

                          <tr
                            key={
                              stakeholder.id
                            }
                            className="
                              transition-colors
                              hover:bg-slate-50/70
                            "
                          >

                            {/* STAKEHOLDER */}

                            <td className="px-6 py-4">

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


                                <div className="min-w-0">

                                  <p
                                    className="
                                      truncate
                                      font-medium
                                      text-[#22243A]
                                    "
                                  >
                                    {stakeholder.name}
                                  </p>

                                  {stakeholder.designation && (

                                    <p
                                      className="
                                        mt-0.5
                                        truncate
                                        text-xs
                                        text-slate-500
                                      "
                                    >
                                      {stakeholder.designation}
                                    </p>

                                  )}

                                </div>

                              </div>

                            </td>


                            {/* GROUP */}

                            <td className="px-4 py-4">

                              <Badge
                                variant="outline"
                                className="
                                  border-slate-200
                                  bg-white
                                  text-slate-600
                                "
                              >
                                {stakeholder.group_name ??
                                  "Stakeholder Group"}
                              </Badge>

                            </td>


                            {/* EMAIL */}

                            <td
                              className="
                                max-w-[250px]
                                truncate
                                px-4
                                py-4
                                text-slate-600
                              "
                            >
                              {stakeholder.email}
                            </td>


                            {/* RESPONSE */}

                            <td className="px-4 py-4">

                              {invitation ? (

                                getStatusBadge(
                                  invitation.status
                                )

                              ) : (

                                <Badge
                                  variant="outline"
                                  className="
                                    border-slate-200
                                    text-slate-500
                                  "
                                >
                                  Not Invited
                                </Badge>

                              )}

                            </td>


                            {/* PARTICIPATION */}

                            <td className="px-4 py-4">

                              <div className="w-32">

                                <div
                                  className="
                                    flex
                                    items-center
                                    justify-between
                                    text-xs
                                  "
                                >

                                  <span
                                    className="
                                      text-slate-500
                                    "
                                  >
                                    {completed
                                      ? "100%"
                                      : invitation
                                        ? "0%"
                                        : "—"}
                                  </span>

                                  <span
                                    className="
                                      text-slate-400
                                    "
                                  >
                                    {completed
                                      ? "Complete"
                                      : "Pending"}
                                  </span>

                                </div>


                                <div
                                  className="
                                    mt-1.5
                                    h-1.5
                                    overflow-hidden
                                    rounded-full
                                    bg-slate-100
                                  "
                                >

                                  <div
                                    className={`
                                      h-full
                                      rounded-full
                                      ${
                                        completed
                                          ? "bg-emerald-500"
                                          : "bg-amber-400"
                                      }
                                    `}
                                    style={{
                                      width:
                                        completed
                                          ? "100%"
                                          : invitation
                                            ? "8%"
                                            : "0%",
                                    }}
                                  />

                                </div>

                              </div>

                            </td>


                            {/* ACTION */}

                            <td
                              className="
                                px-6
                                py-4
                                text-right
                              "
                            >

                              {invitation?.survey_url ? (

                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="gap-2"
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

                              ) : (

                                <span
                                  className="
                                    text-xs
                                    text-slate-400
                                  "
                                >
                                  Not available
                                </span>

                              )}

                            </td>

                          </tr>

                        );

                      }
                    )}

                  </tbody>

                </table>

              </div>

            )}

          </CardContent>

        </Card>


        {/* ==================================================
            SELECTION / DISTRIBUTION
        ================================================== */}

        <Card className="border-slate-200 shadow-sm px-4">

          <CardHeader>

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
                  Distribute Survey
                </CardTitle>

                <CardDescription>
                  Select stakeholders or entire stakeholder
                  groups to send survey invitations.
                </CardDescription>

              </div>


              <Badge
                variant="outline"
                className="
                  w-fit
                  border-[#DDD8FF]
                  bg-[#FBFAFF]
                  text-[#4A3FD6]
                "
              >
                {selectedCount} selected
              </Badge>

            </div>

          </CardHeader>


          <Separator />


          <CardContent className="p-4">

            {stakeholders.length === 0 ? (

              <div
                className="
                  flex
                  flex-col
                  items-center
                  justify-center
                  px-6
                  py-12
                  text-center
                "
              >

                <Users
                  className="
                    h-8
                    w-8
                    text-slate-300
                  "
                />

                <p
                  className="
                    mt-3
                    text-sm
                    font-semibold
                    text-[#22243A]
                  "
                >
                  No stakeholders available
                </p>

              </div>

            ) : (

              <div className="space-y-2">

                {Object.entries(
                  groupedStakeholders
                ).map(
                  ([
                    groupId,
                    groupStakeholders,
                  ]) => {

                    const expanded =
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


                    const allSelected =
                      groupStakeholders.length > 0 &&
                      selectedGroupCount ===
                        groupStakeholders.length;


                    const someSelected =
                      selectedGroupCount > 0 &&
                      !allSelected;


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

                        <div
                          className={`
                            flex
                            items-center
                            justify-between
                            gap-3
                            px-4
                            py-3
                            ${
                              expanded
                                ? "bg-[#FBFAFF]"
                                : "hover:bg-slate-50"
                            }
                          `}
                        >

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

                              {expanded ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
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
                                {
                                  groupStakeholders.length
                                }{" "}
                                stakeholders
                              </span>

                            </span>

                          </button>


                          <div
                            className="
                              flex
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
                              {
                                groupStakeholders.length
                              }
                            </Badge>


                            <Checkbox
                              checked={
                                allSelected
                                  ? true
                                  : someSelected
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


                        {expanded && (

                          <div
                            className="
                              border-t
                              border-slate-100
                              bg-slate-50/50
                            "
                          >

                            {groupStakeholders.map(
                              (
                                stakeholder
                              ) => {

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

                                    <Checkbox
                                      checked={
                                        selected
                                      }
                                      onCheckedChange={() =>
                                        toggleStakeholder(
                                          stakeholder.id
                                        )
                                      }
                                    />


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

                                      <p
                                        className="
                                          truncate
                                          text-xs
                                          text-slate-500
                                        "
                                      >
                                        {stakeholder.email}
                                      </p>

                                    </div>


                                    {selected && (

                                      <Check
                                        className="
                                          h-4
                                          w-4
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
            SEND INVITATION DIALOG
        ================================================== */}

        <Dialog
          open={sendDialogOpen}
          onOpenChange={(open) => {

            if (!open && !sending) {
              setSendDialogOpen(false);
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

                    You are about to send invitations
                    to{" "}

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
                    max-h-48
                    space-y-2
                    overflow-y-auto
                  "
                >

                  {selectedStakeholders.map(
                    (stakeholder) => (

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

                        <div className="min-w-0">

                          <p
                            className="
                              truncate
                              text-sm
                              font-medium
                              text-slate-800
                            "
                          >
                            {stakeholder.name}
                          </p>

                          <p
                            className="
                              truncate
                              text-xs
                              text-slate-500
                            "
                          >
                            {stakeholder.email}
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
                  receive a unique survey invitation
                  link. Their response will be tracked
                  on this dashboard.
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
                  Once invitations are sent, the
                  response metrics will update as
                  stakeholders complete the survey.
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
                disabled={sending}
                onClick={() =>
                  setSendDialogOpen(false)
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