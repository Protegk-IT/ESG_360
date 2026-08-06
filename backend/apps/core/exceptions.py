from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:

        response.data = {
            "success": False,
            "message": get_error_message(response.data),
            "errors": response.data
        }

    return response



def get_error_message(errors):

    if isinstance(errors, dict):

        first_key = list(errors.keys())[0]

        return errors[first_key][0]

    return str(errors)