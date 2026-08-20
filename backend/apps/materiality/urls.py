
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MaterialityAssessmentViewSet,
    PublicSurveyAnswerView,
    PublicSurveySubmitView,
    PublicSurveyView,
    TopicCategoryListCreateView,
    MaterialTopicListCreateView,
    MaterialSubTopicListCreateView,
)


app_name = 'materiality'
router = DefaultRouter()


router.register(r"assessments", MaterialityAssessmentViewSet,basename="materiality-assessment",)

urlpatterns = [
               path('', include(router.urls)),
               path("topics/categories/",TopicCategoryListCreateView.as_view(),name="topic-category-list-create",),
               path( "topics/", MaterialTopicListCreateView.as_view(),name="material-topic-list-create",),
               path("topics/subtopics/",MaterialSubTopicListCreateView.as_view(),name="material-subtopic-list-create",),
               ]

public_urlpatterns = [

    # Public survey
    path(
        "survey/<str:token>/",
        PublicSurveyView.as_view(),
        name="public-survey",
    ),

    path(
        "survey/<str:token>/answer/",
        PublicSurveyAnswerView.as_view(),
        name="public-survey-answer",
    ),

    path(
        "survey/<str:token>/submit/",
        PublicSurveySubmitView.as_view(),
        name="public-survey-submit",
    ),
]



