import random
import string
from pathlib import Path
from typing import Any, Dict

from apps.core.logging import logger
from apps.integrations.aws.ses import send_email_via_ses


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_template_path(template_name: str) -> Path:
    """Get the full path to an email template."""
    return get_project_root() / "integrations" / "mail" / "templates" / template_name


def generate_random_password(length: int = 12) -> str:
    """Generate a random password with mixed case letters, numbers, and symbols."""
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*"

    # Ensure at least one character from each category
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(symbols),
    ]

    # Fill remaining length with random characters from all categories
    all_chars = lowercase + uppercase + digits + symbols
    for _ in range(length - 4):
        password.append(random.choice(all_chars))

    # Shuffle to randomize positions
    random.shuffle(password)
    return "".join(password)


def render_email_template(template_path: str, context: Dict[str, Any]) -> str:
    """Render HTML email template with context variables."""
    try:
        template_file = Path(template_path)
        if not template_file.exists():
            logger.error(f"Email template not found: {template_path}")
            return ""

        template_content = template_file.read_text(encoding="utf-8")

        # Simple template variable replacement
        for key, value in context.items():
            placeholder = f"{{{{ {key} }}}}"
            template_content = template_content.replace(placeholder, str(value))

        return template_content

    except Exception as e:
        logger.error(f"Error rendering email template: {str(e)}")
        return ""


def send_staff_creation_email(
    user_email: str, user_data: Dict[str, Any], password: str
) -> bool:
    """
    Send staff creation email with login credentials.

    Args:
        user_email: Recipient email address
        user_data: User information (store_id, name, etc.)
        password: Generated password

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        context = {
            "title_email": "wakeatte全国版アカウント作成完了",
            "email": user_email,
            "password": password,
            "web_url": "https://cippo.wakeatte.net/",
            "appstore_url": "https://apps.apple.com/us/app/wakeatte/id6752841773",  # Update later
            "googleplay_url": "https://play.google.com/store/apps/details?id=info.wake.wakeatte",  # Update later
        }

        # Render email template
        if user_data["role"] == "owner_locker":
            template_path = get_template_path("email_create_owner_locker.ja.html")
        elif user_data["role"] == "owner_shop":
            # send to shop owner, staff shop
            context["store_id"] = user_data.get("code_shop", "N/A")
            template_path = get_template_path("email_create_shop_users.ja.html")

        email_content = render_email_template(str(template_path), context)

        if not email_content:
            return False

        return send_email_via_ses(
            recipient_email=user_email,
            subject=context["title_email"],
            html_content=email_content,
        )

    except Exception as e:
        logger.error(f"Error sending staff creation email: {str(e)}")
        return False
