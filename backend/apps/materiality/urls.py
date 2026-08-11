
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (MaterialityAssessmentViewSet,TopicCategoryListCreateView,MaterialTopicListCreateView,MaterialSubTopicListCreateView,)


app_name = 'materiality'
router = DefaultRouter()


router.register(r"assessments", MaterialityAssessmentViewSet,basename="materiality-assessment",)

urlpatterns = [
               path('', include(router.urls)),
               path("topics/categories/",TopicCategoryListCreateView.as_view(),name="topic-category-list-create",),
               path( "topics/", MaterialTopicListCreateView.as_view(),name="material-topic-list-create",),
               path("topics/subtopics/",MaterialSubTopicListCreateView.as_view(),name="material-subtopic-list-create",),
               ]



