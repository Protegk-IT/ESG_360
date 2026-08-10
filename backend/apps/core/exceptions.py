from rest_framework.views import exception_handler
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList


def get_error_message(errors):
    """Extract a useful human-readable message from DRF's error structures."""
    if isinstance(errors, (list, tuple, ReturnList)):
        return get_error_message(errors[0]) if errors else "Request failed."

    if isinstance(errors, (dict, ReturnDict)):
        if not errors:
            return "Request failed."
        return get_error_message(next(iter(errors.values())))

    return str(errors)


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:

        response.data = {
            "success": False,
            "message": get_error_message(response.data),
            "errors": response.data
        }

    return response
