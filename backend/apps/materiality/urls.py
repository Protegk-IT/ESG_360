from django.urls import path

from .views import (
    TopicCategoryListCreateView,
    MaterialTopicListCreateView,
    MaterialSubTopicListCreateView,
)


urlpatterns = [
    path(
        "topics/categories/",
        TopicCategoryListCreateView.as_view(),
        name="topic-category-list-create",
    ),

    path(
        "topics/",
        MaterialTopicListCreateView.as_view(),
        name="material-topic-list-create",
    ),

    path(
        "topics/subtopics/",
        MaterialSubTopicListCreateView.as_view(),
        name="material-subtopic-list-create",
    ),
]