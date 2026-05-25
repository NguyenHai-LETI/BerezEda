from typing import Any, Dict

from apps.core.logging import logger
from apps.integrations.aws.client import get_ses_client


def send_email_via_ses(
    recipient_email: str,
    subject: str,
    html_content: str,
    sender_email: str = "noreply@wakeatte.net",
) -> bool:
    """
    Send email using AWS SES.

    Args:
        recipient_email: Email address to send to
        subject: Email subject line
        html_content: HTML content of the email
        sender_email: Sender email address

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        ses_client = get_ses_client()

        response = ses_client.send_email(
            Source=sender_email,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_content, "Charset": "UTF-8"}},
            },
        )

        logger.info(
            f"Email sent successfully to {recipient_email}. MessageId: {response['MessageId']}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False


def send_staff_creation_email(
    user_email: str, context: Dict[str, Any], email_content: str
) -> bool:
    """Send staff creation email - wrapper for backward compatibility."""
    return send_email_via_ses(
        recipient_email=user_email,
        subject=context.get("title_email", "Account Created"),
        html_content=email_content,
    )
