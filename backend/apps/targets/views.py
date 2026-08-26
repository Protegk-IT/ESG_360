from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.services.rbac import RBACService
from apps.core.response import created_response, success_response
from .authorization import has_target_scope, scoped_queryset
from .models import Goal, KPI, KPIInitiative, Target
from .serializers import GoalSerializer, GoalWriteSerializer, InitiativeSerializer, InitiativeWriteSerializer, KPISerializer, KPIWriteSerializer, TargetSerializer, TargetWriteSerializer
from .services.progress import progress_for, trajectory_value


class TargetsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def require_access(self):
        if not RBACService.has_permission(self.request.user, "target.set"):
            raise PermissionDenied("You don't have permission to perform this action.")

    def call(self, fn):
        try:
            return fn()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc

    def target_queryset(self):
        return scoped_queryset(Target.objects.select_related("kpi__goal", "org_node", "baseline_period", "target_period"), self.request.user)

    def visible_kpis(self):
        self.require_access()
        if self.request.user.is_superuser or RBACService.get_allowed_org_nodes(self.request.user, "target.set", module_code="target") is None:
            return KPI.objects.select_related("goal", "datapoint", "default_unit")
        # A newly created KPI has no Target (and therefore no OrgNode scope)
        # yet.  Its creator must still be able to configure its first target
        # or initiative; otherwise the normal Goal → KPI → Target flow is
        # dead-ended.  Once a target exists, other visibility remains tied to
        # the same-assignment scoped target queryset.
        return KPI.objects.filter(
            Q(targets__in=self.target_queryset()) | Q(goal__created_by=self.request.user)
        ).distinct().select_related("goal", "datapoint", "default_unit")

    def visible_goals(self):
        return Goal.objects.filter(
            Q(kpis__in=self.visible_kpis()) | Q(created_by=self.request.user)
        ).distinct().annotate(kpi_count=Count("kpis"))


class GoalListCreateAPIView(TargetsAPIView):
    def get(self, request):
        qs = self.visible_goals()
        if term := request.query_params.get("search"):
            qs = qs.filter(name__icontains=term)
        if status := request.query_params.get("status"):
            qs = qs.filter(status=status)
        return success_response(GoalSerializer(qs, many=True).data)
    def post(self, request):
        self.require_access()
        serializer = GoalWriteSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        goal = self.call(lambda: serializer.save(created_by=request.user))
        return created_response(GoalSerializer(goal).data, "Goal created.")


class GoalDetailAPIView(TargetsAPIView):
    def get_object(self, goal_id):
        return get_object_or_404(self.visible_goals(), pk=goal_id)
    def get(self, request, goal_id): return success_response(GoalSerializer(self.get_object(goal_id)).data)
    def patch(self, request, goal_id):
        goal = self.get_object(goal_id); serializer = GoalWriteSerializer(goal, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        return success_response(GoalSerializer(self.call(serializer.save)).data, "Goal updated.")


class GoalKPIListCreateAPIView(TargetsAPIView):
    def get_goal(self, goal_id): return get_object_or_404(self.visible_goals(), pk=goal_id)
    def get(self, request, goal_id):
        return success_response(KPISerializer(self.visible_kpis().filter(goal=self.get_goal(goal_id)), many=True).data)
    def post(self, request, goal_id):
        goal = self.get_goal(goal_id); serializer = KPIWriteSerializer(data={**request.data, "goal": str(goal.id)}); serializer.is_valid(raise_exception=True)
        return created_response(KPISerializer(self.call(serializer.save)).data, "KPI created.")


class KPIDetailAPIView(TargetsAPIView):
    def get_object(self, kpi_id): return get_object_or_404(self.visible_kpis(), pk=kpi_id)
    def get(self, request, kpi_id): return success_response(KPISerializer(self.get_object(kpi_id)).data)
    def patch(self, request, kpi_id):
        obj = self.get_object(kpi_id); serializer = KPIWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        return success_response(KPISerializer(self.call(serializer.save)).data, "KPI updated.")


class KPITargetListCreateAPIView(TargetsAPIView):
    def get_kpi(self, kpi_id): return get_object_or_404(self.visible_kpis(), pk=kpi_id)
    def get(self, request, kpi_id): return success_response(TargetSerializer(self.target_queryset().filter(kpi=self.get_kpi(kpi_id)), many=True).data)
    def post(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id); serializer = TargetWriteSerializer(data={**request.data, "kpi": str(kpi.id)}); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node")
        if org and not has_target_scope(request.user, org.id): raise NotFound("Organization node not found.")
        target = self.call(lambda: serializer.save(created_by=request.user))
        return created_response(TargetSerializer(target).data, "Target created.")


class TargetDetailAPIView(TargetsAPIView):
    def get_object(self, target_id): return get_object_or_404(self.target_queryset(), pk=target_id)
    def get(self, request, target_id): return success_response(TargetSerializer(self.get_object(target_id)).data)
    def patch(self, request, target_id):
        obj = self.get_object(target_id); serializer = TargetWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node", obj.org_node)
        if org and not has_target_scope(request.user, org.id): raise NotFound("Organization node not found.")
        return success_response(TargetSerializer(self.call(serializer.save)).data, "Target updated.")


class TargetProgressAPIView(TargetsAPIView):
    def get_object(self, target_id):
        return get_object_or_404(self.target_queryset(), pk=target_id)

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
    def get_kpi(self, kpi_id): return get_object_or_404(self.visible_kpis(), pk=kpi_id)
    def get(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id)
        return success_response(InitiativeSerializer(self.initiative_queryset().filter(kpi=kpi), many=True).data)

    def initiative_queryset(self):
        queryset = KPIInitiative.objects.select_related("kpi__goal", "org_node", "owner")
        if self.request.user.is_superuser or RBACService.get_allowed_org_nodes(self.request.user, "target.set", module_code="target") is None:
            return queryset
        allowed = RBACService.get_allowed_org_nodes(self.request.user, "target.set", module_code="target")
        return queryset.filter(Q(org_node_id__in=allowed) | Q(kpi__goal__created_by=self.request.user)).distinct()
    def post(self, request, kpi_id):
        kpi = self.get_kpi(kpi_id); serializer = InitiativeWriteSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node")
        if org and not has_target_scope(request.user, org.id): raise NotFound("Organization node not found.")
        return created_response(InitiativeSerializer(self.call(lambda: serializer.save(kpi=kpi))).data, "Initiative created.")


class InitiativeDetailAPIView(TargetsAPIView):
    def get_object(self, initiative_id):
        queryset = KPIInitiative.objects.select_related("kpi__goal", "org_node", "owner")
        if not self.request.user.is_superuser and RBACService.get_allowed_org_nodes(self.request.user, "target.set", module_code="target") is not None:
            allowed = RBACService.get_allowed_org_nodes(self.request.user, "target.set", module_code="target")
            queryset = queryset.filter(Q(org_node_id__in=allowed) | Q(kpi__goal__created_by=self.request.user)).distinct()
        return get_object_or_404(queryset, pk=initiative_id)
    def patch(self, request, initiative_id):
        obj = self.get_object(initiative_id); serializer = InitiativeWriteSerializer(obj, data=request.data, partial=True); serializer.is_valid(raise_exception=True)
        org = serializer.validated_data.get("org_node", obj.org_node)
        if org and not has_target_scope(request.user, org.id): raise NotFound("Organization node not found.")
        return success_response(InitiativeSerializer(self.call(serializer.save)).data, "Initiative updated.")
