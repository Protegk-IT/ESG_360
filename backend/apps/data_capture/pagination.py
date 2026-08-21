from rest_framework.pagination import PageNumberPagination


class DataCapturePagination(PageNumberPagination):
    """Bounded pagination for operational request and evidence collections."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def payload(self, serializer):
        return {
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": serializer.data,
        }
