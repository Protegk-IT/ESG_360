from threading import local

_thread_locals = local()


def set_current_request(request):
    _thread_locals.request = request


def get_current_request():
    return getattr(_thread_locals, "request", None)