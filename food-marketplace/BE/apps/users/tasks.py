from apps.core.celery_app import celery_app
from apps.core.config import RESET_CODE_EXPIRE_MINUTES
from apps.core.logging import logger
from apps.integrations.aws.ses import send_email_via_ses
from apps.integrations.firebase.user_service import FirebaseUserService
from apps.integrations.mail.email_service import (
    get_template_path,
    render_email_template,
)


@celery_app.task(name="users.send_reset_password_email")
def send_reset_password_email_task(user_id: str, user_email: str, reset_code: str):
    try:
        context = {
            "title_email": "パスワードリセットコード - Wakeatte",
            "user_email": user_email,
            "reset_code": reset_code,
            "expiry_minutes": RESET_CODE_EXPIRE_MINUTES,
        }

        template_path = get_template_path("email_reset_password_code.ja.html")
        email_content = render_email_template(str(template_path), context)

        if not email_content:
            logger.error(f"Failed to render email template for user {user_id}")
            return False

        success = send_email_via_ses(
            recipient_email=user_email,
            subject=context["title_email"],
            html_content=email_content,
        )

        if success:
            logger.info(f"Password reset code email sent to {user_email}")
        else:
            logger.error(f"Failed to send password reset code email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending password reset code email: {str(e)}")
        return False


@celery_app.task
def sync_user_to_firebase_task(user_data: dict):
    """Sync user data to Firebase asynchronously."""
    try:
        firebase_service = FirebaseUserService()
        result = firebase_service.sync_user_data_to_firebase(user_data)

        user_id = user_data.get("id", "unknown")
        if result:
            logger.info(f"Successfully synced user {user_id} to Firebase")
        else:
            logger.error(f"Failed to sync user {user_id} to Firebase")

        return result

    except Exception as e:
        user_id = user_data.get("id", "unknown")
        logger.error(f"Error in sync_user_to_firebase_task for user {user_id}: {e}")
        return False


@celery_app.task
def update_user_in_firebase_task(user_id: str, update_data: dict):
    """Update user in Firebase asynchronously."""
    try:
        firebase_service = FirebaseUserService()
        result = firebase_service.update_user_in_firebase(user_id, update_data)

        if result:
            logger.info(f"Successfully updated user {user_id} in Firebase")
        else:
            logger.error(f"Failed to update user {user_id} in Firebase")

        return result

    except Exception as e:
        logger.error(f"Error in update_user_in_firebase_task for user {user_id}: {e}")
        return False


@celery_app.task
def delete_user_from_firebase_task(user_id: str):
    """Delete user from Firebase asynchronously."""
    try:
        firebase_service = FirebaseUserService()
        result = firebase_service.delete_user_from_firebase(user_id)

        if result:
            logger.info(f"Successfully deleted user {user_id} from Firebase")
        else:
            logger.error(f"Failed to delete user {user_id} from Firebase")

        return result

    except Exception as e:
        logger.error(f"Error in delete_user_from_firebase_task for user {user_id}: {e}")
        return False
