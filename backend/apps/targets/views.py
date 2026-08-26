from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.services.rbac import RBACService
from apps.core.response import created_response, success_response
from .authorization import (
    can_read_targets,
    has_company_wide_target_scope,
    has_target_scope,
    read_scoped_queryset,
    write_scoped_queryset,
)
from .models import Goal, KPI, KPIInitiative, Target
from .serializers import GoalSerializer, GoalWriteSerializer, InitiativeSerializer, InitiativeWriteSerializer, KPISerializer, KPIWriteSerializer, TargetSerializer, TargetWriteSerializer
from .services.progress import progress_for, trajectory_value


class TargetsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def require_write_access(self):
        if not RBACService.has_permission(self.request.user, "target.set"):
            raise PermissionDenied("You don't have permission to perform this action.")

    def require_read_access(self):
        if not can_read_targets(self.request.user):
            raise PermissionDenied("You don't have permission to perform this action.")

    def call(self, fn):
        try:
            return fn()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc

    def target_base_queryset(self):
        return Target.objects.select_related("kpi__goal", "org_node", "baseline_period", "target_period")

    def readable_targets(self):
        self.require_read_access()
        return read_scoped_queryset(self.target_base_queryset(), self.request.user)

    def writable_targets(self):
        self.require_write_access()
        return write_scoped_queryset(self.target_base_queryset(), self.request.user)

    def setup_kpis(self):
        """Unscoped setup is visible only to its creator until first Target.

        Goal and KPI records intentionally have no OrgNode field.  A scoped
        setter may create them, but can only configure their first Target in a
        qualifying OrgNode.  Once one exists, every read/write path resolves
        through its actual target scope; creator identity never becomes a
        permanent cross-scope override.
        """
        return KPI.objects.filter(goal__created_by=self.request.user, targets__isnull=True)

    def writable_kpis(self):
        self.require_write_access()
        if self.request.user.is_superuser or has_company_wide_target_scope(self.request.user):
            return KPI.objects.select_related("goal", "datapoint", "default_unit")
        return KPI.objects.filter(
            Q(targets__in=self.writable_targets()) | Q(pk__in=self.setup_kpis())
        ).distinct().select_related("goal", "datapoint", "default_unit")

    def readable_kpis(self):
        self.require_read_access()
        queryset = KPI.objects.filter(targets__in=self.readable_targets())
        if RBACService.has_permission(self.request.user, "target.set"):
            queryset = queryset | self.setup_kpis()
        return queryset.distinct().select_related("goal", "datapoint", "default_unit")

    def readable_goals(self):
        return Goal.objects.filter(
            Q(kpis__in=self.readable_kpis())
        ).distinct().annotate(kpi_count=Count("kpis"))

    def writable_goals(self):
        self.require_write_access()
        return Goal.objects.filter(
            Q(kpis__in=self.writable_kpis()) | Q(kpis__isnull=True, created_by=self.request.user)
        ).distinct().annotate(kpi_count=Count("kpis"))

    def ensure_write_scope(self, org_node):
        if org_node is None:
            if not has_company_wide_target_scope(self.request.user):
                raise NotFound("Organization node not found.")
        elif not has_target_scope(self.request.user, org_node.id):
            raise NotFound("Organization node not found.")

    def ensure_payload_scope(self, payload):
        """Reject a company-wide write before serializer validation.

        A scoped setter must not get a serializer-specific response while
        attempting to create a company-wide record.  Non-null values still go
        through relation validation before their resolved OrgNode is checked.
        """
        if payload.get("org_node") in (None, "", "none"):
            self.ensure_write_scope(None)

    def readable_initiatives(self):
        self.require_read_access()
        queryset = read_scoped_queryset(
            KPIInitiative.objects.select_related("kpi__goal", "org_node", "owner"),
            self.request.user,
        )
        if RBACService.has_permission(self.request.user, "target.set"):
            queryset = queryset | KPIInitiative.objects.filter(kpi__in=self.setup_kpis())
        return queryset.distinct()

    def writable_initiatives(self):
        self.require_write_access()
        queryset = write_scoped_queryset(
            KPIInitiative.objects.select_related("kpi__goal", "org_node", "owner"),
            self.request.user,
        )
        return (queryset | KPIInitiative.objects.filter(kpi__in=self.setup_kpis())).distinct()


class GoalListCreateAPIView(TargetsAPIView):
    def get(self, request):
        qs = self.readable_goals()
        if term := request.query_params.get("search"):
            qs = qs.filter(name__icontains=term)
        if status := request.query_params.get("status"):
            qs = qs.filter(status=status)
        return success_response(GoalSerializer(qs, many=True).data)
    def post(self, request):
        self.require_write_access()
        serializer = GoalWriteSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        goal = self.call(lambda: serializer.save(created_by=request.user))
        return created_response(GoalSerializer(goal).data, "Goal created.")


class GoalDetailAPIView(TargetsAPIView):
    def get_object(self, goal_id, *, writable=False):
        queryset = self.writable_goals() if writable else self.readable_goals()
        return get_object_or_404(queryset, pk=goal_id)
    def get(self, request, goal_id): return success_response(GoalSerializer(self.get_object(goal_id)).data)
    def patch(self, request, goal_id):
        goal = self.get_object(goal_id, writable=True); serializer = GoalWriteSerializer(goal, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        return success_response(GoalSerializer(self.call(serializer.save)).data, "Goal updated.")


class GoalKPIListCreateAPIView(TargetsAPIView):
    def get_goal(self, goal_id, *, writable=False):
        queryset = self.writable_goals() if writable else self.readable_goals()
        return get_object_or_404(queryset, pk=goal_id)
    def get(self, request, goal_id):
        return success_response(KPISerializer(self.readable_kpis().filter(goal=self.get_goal(goal_id)), many=True).data)
    def post(self, request, goal_id):
        goal = self.get_goal(goal_id, writable=True); serializer = KPIWriteSerializer(data={**request.data, "goal": str(goal.id)}); serializer.is_valid(raise_exception=True)
        return created_response(KPISerializer(self.call(serializer.save)).data, "KPI created.")


class KPIDetailAPIView(TargetsAPIView):
    def get_object(self, kpi_id, *, writable=False): return get_object_or_404(self.writable_kpis() if writable else self.readable_kpis(), pk=kpi_id)
    def get(self, request, kpi_id): return success_response(KPISerializer(self.get_object(kpi_id)).data)
    def patch(self, request, kpi_id):
        obj = self.get_object(kpi_id, writable=True); serializer = KPIWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        return success_response(KPISerializer(self.call(serializer.save)).data, "KPI updated.")


class KPITargetListCreateAPIView(TargetsAPIView):
    def get_kpi(self, kpi_id, *, writable=False): return get_object_or_404(self.writable_kpis() if writable else self.readable_kpis(), pk=kpi_id)
    def get(self, request, kpi_id): return success_response(TargetSerializer(self.readable_targets().filter(kpi=self.get_kpi(kpi_id)), many=True).data)
    def post(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id, writable=True); self.ensure_payload_scope(request.data); serializer = TargetWriteSerializer(data={**request.data, "kpi": str(kpi.id)}); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node")
        self.ensure_write_scope(org)
        target = self.call(lambda: serializer.save(created_by=request.user))
        return created_response(TargetSerializer(target).data, "Target created.")


class TargetDetailAPIView(TargetsAPIView):
    def get_object(self, target_id, *, writable=False): return get_object_or_404(self.writable_targets() if writable else self.readable_targets(), pk=target_id)
    def get(self, request, target_id): return success_response(TargetSerializer(self.get_object(target_id)).data)
    def patch(self, request, target_id):
        obj = self.get_object(target_id, writable=True); serializer = TargetWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node", obj.org_node)
        self.ensure_write_scope(org)
        return success_response(TargetSerializer(self.call(serializer.save)).data, "Target updated.")


class TargetProgressAPIView(TargetsAPIView):
    def get_object(self, target_id):
        return get_object_or_404(self.readable_targets(), pk=target_id)

    def get(self, request, target_id):
        target = self.get_object(target_id)
        periods = target.baseline_period.__class__.objects.filter(
            period_type="ANNUAL",
            is_active=True,
            start_date__gte=target.baseline_period.start_date,
            start_date__lte=target.target_period.start_date,
        ).order_by("start_date")
        rows = [progress_for(target, period) for period in periods]
        return success_response({"target": TargetSerializer(target).data, "trajectory": [{"reporting_period": str(p.id), "name": p.name, "value": trajectory_value(target, p)} for p in periods], "progress": rows})


class KPIInitiativeListCreateAPIView(TargetsAPIView):
    def get_kpi(self, kpi_id, *, writable=False): return get_object_or_404(self.writable_kpis() if writable else self.readable_kpis(), pk=kpi_id)
    def get(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id)
        return success_response(InitiativeSerializer(self.readable_initiatives().filter(kpi=kpi), many=True).data)

    def post(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id, writable=True); self.ensure_payload_scope(request.data); serializer = InitiativeWriteSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node")
        self.ensure_write_scope(org)
        return created_response(InitiativeSerializer(self.call(lambda: serializer.save(kpi=kpi))).data, "Initiative created.")


class InitiativeDetailAPIView(TargetsAPIView):
    def get_object(self, initiative_id, *, writable=False):
        queryset = self.writable_initiatives() if writable else self.readable_initiatives()
        return get_object_or_404(queryset, pk=initiative_id)
    def get(self, request, initiative_id):
        return success_response(InitiativeSerializer(self.get_object(initiative_id)).data)
    def patch(self, request, initiative_id):
        obj = self.get_object(initiative_id, writable=True); serializer = InitiativeWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node", obj.org_node)
        self.ensure_write_scope(org)
        return success_response(InitiativeSerializer(self.call(serializer.save)).data, "Initiative updated.")
