from rest_framework.response import Response
from rest_framework import status


def success_response(
    data=None,
    message="Success",
    status_code=status.HTTP_200_OK
):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data
        },
        status=status_code
    )


def created_response(
    data=None,
    message="Created successfully"
):
    return success_response(
        data=data,
        message=message,
        status_code=status.HTTP_201_CREATED
    )


def no_content_response(
    message="Deleted successfully"
):
    """Return a standards-compliant successful response with no body.

    HTTP 204 responses cannot contain the message/data envelope. Keep the
    optional argument for backwards-compatible call sites, but use
    ``success_response`` with a 200 status when a client must receive a
    confirmation message.
    """
    return Response(status=status.HTTP_204_NO_CONTENT)
