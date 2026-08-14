from .thread_local import set_current_request


class CurrentRequestMiddleware:
    """
    Stores the current request so it can be accessed anywhere.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            return self.get_response(request)
        finally:
            # Thread-local state must never leak into the next request when a
            # view or another middleware raises an exception.
            set_current_request(None)
