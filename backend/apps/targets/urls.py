from django.urls import path
from .views import GoalDetailAPIView, GoalListCreateAPIView, GoalKPIListCreateAPIView, InitiativeDetailAPIView, KPIInitiativeListCreateAPIView, KPIDetailAPIView, KPITargetListCreateAPIView, TargetDetailAPIView, TargetProgressAPIView

urlpatterns = [
    path("goals/", GoalListCreateAPIView.as_view()), path("goals/<uuid:goal_id>/", GoalDetailAPIView.as_view()),
    path("goals/<uuid:goal_id>/kpis/", GoalKPIListCreateAPIView.as_view()), path("kpis/<uuid:kpi_id>/", KPIDetailAPIView.as_view()),
    path("kpis/<uuid:kpi_id>/targets/", KPITargetListCreateAPIView.as_view()), path("targets/<uuid:target_id>/", TargetDetailAPIView.as_view()),
    path("targets/<uuid:target_id>/progress/", TargetProgressAPIView.as_view()),
    path("kpis/<uuid:kpi_id>/initiatives/", KPIInitiativeListCreateAPIView.as_view()), path("initiatives/<uuid:initiative_id>/", InitiativeDetailAPIView.as_view()),
]
