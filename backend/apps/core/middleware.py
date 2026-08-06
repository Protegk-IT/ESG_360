from .thread_local import set_current_request


class CurrentRequestMiddleware:
    """
    Stores the current request so it can be accessed anywhere.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)

        response = self.get_response(request)

        set_current_request(None)

        return response