from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ReportRunViewSet,
    ReportRunFreezeView,
    ReportRunResolvedValuesView,
    ReportRunSnapshotView,
)


router = DefaultRouter()

router.register(
    r"report-runs",
    ReportRunViewSet,
    basename="report-run",
)


urlpatterns = [
    # ------------------------------------------------------------
    # ReportRun CRUD
    #
    # GET    /api/reporting/report-runs/
    # POST   /api/reporting/report-runs/
    #
    # GET    /api/reporting/report-runs/<uuid>/
    # PATCH  /api/reporting/report-runs/<uuid>/
    # DELETE /api/reporting/report-runs/<uuid>/
    # ------------------------------------------------------------
    path(
        "",
        include(router.urls),
    ),

    # ------------------------------------------------------------
    # Freeze ReportRun
    #
    # POST /api/reporting/report-runs/<uuid>/freeze/
    # ------------------------------------------------------------
    path(
        "report-runs/<uuid:run_id>/freeze/",
        ReportRunFreezeView.as_view(),
        name="report-run-freeze",
    ),

    # ------------------------------------------------------------
    # Frozen Framework Snapshot
    #
    # GET /api/reporting/report-runs/<uuid>/snapshot/
    # ------------------------------------------------------------
    path(
        "report-runs/<uuid:run_id>/snapshot/",
        ReportRunSnapshotView.as_view(),
        name="report-run-snapshot",
    ),

    path(
        "report-runs/<uuid:run_id>/resolved-values/",
        ReportRunResolvedValuesView.as_view(),
        name="report-run-resolved-values",
    ),
]