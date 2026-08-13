from django.conf import settings
from django.core.mail import send_mail


def send_survey_invitation(invitation):
    stakeholder = invitation.stakeholder
    survey = invitation.survey

    survey_url = (
        f"{settings.FRONTEND_URL}/survey/"
        f"{invitation.token}/"
    )

    subject = f"Invitation to complete {survey.title}"

    message = (
        f"Hello {stakeholder.name},\n\n"
        f"You have been invited to complete "
        f"the materiality survey.\n\n"
        f"Please use the following link:\n"
        f"{survey_url}\n\n"
        f"Thank you."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[stakeholder.email],
        fail_silently=False,
    )