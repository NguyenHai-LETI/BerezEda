from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session

# Import model registry to ensure all relationships are properly configured
from apps.core.models import *  # noqa
from apps.core.utils import get_current_time
from apps.integrations.branchio import create_branchio_deeplink
from apps.integrations.mynaportal import (
    FRONTEND_REDIRECT_URL,
    IF001_01_PATH,
    IF001_01_URL,
    SERVICE_ID,
    SERVICE_PROVIDER_ID,
)
from apps.users.models import User

from .crud import (
    create_myna_authorizer,
    get_max_state,
    get_myna_authorizer_by_state,
    get_user_welfare_supports,
)
from .data_processor import is_welfare_support_active
from .models.user_welfare_support import UserWelfareSupport
from .myna_service import MynaPortalService


def _generate_next_state(db: Session) -> str:
    """
    Generate the next sequential state value.

    Args:
        db: Database session

    Returns:
        Formatted state string (8 digits)
    """
    max_state = get_max_state(db)
    next_state = max_state + 1
    return f"{next_state:08d}"


def _create_authorizer_record(
    db: Session, state: str, user_id: Optional[str] = None
) -> Any:
    """
    Create a new MynaAuthorizer database record.

    Args:
        db: Database session
        state: Generated state value
        user_id: Optional user ID to associate

    Returns:
        Created MynaAuthorizer instance
    """
    form_data = {"state": state, "status": "INIT"}

    if user_id:
        form_data["user_id"] = user_id

    return create_myna_authorizer(db, form_data)


def _build_oauth_params(state: str) -> Dict[str, str]:
    """
    Build OAuth authorization parameters.

    Args:
        state: State parameter for OAuth flow

    Returns:
        Dictionary of OAuth parameters
    """
    return {
        "response_type": "code",
        "client_id": f"{SERVICE_PROVIDER_ID}_{SERVICE_ID}",
        "redirect_uri": FRONTEND_REDIRECT_URL,
        "state": state,
        "login_type": "0",
    }


def _construct_authorization_url(params: Dict[str, str]) -> str:
    """
    Construct the complete authorization URL using string formatting.

    Args:
        params: OAuth parameters dictionary

    Returns:
        Complete authorization URL
    """
    response_type = params["response_type"]
    client_id = params["client_id"]
    redirect_uri = params["redirect_uri"]
    state = params["state"]
    login_type = params["login_type"]

    query_params = f"response_type={response_type}&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&login_type={login_type}"
    return f"{IF001_01_URL}{IF001_01_PATH}?{query_params}"


def generate_service_link_html(message: str, deeplink: str) -> str:
    """
    Generate HTML content for service linking page.

    Args:
        message: Message to display to user
        deeplink: Deeplink URL to app

    Returns:
        HTML content as string
    """
    import html

    escaped_message = html.escape(message)
    escaped_deeplink = html.escape(deeplink)

    return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
        <meta charset="UTF-8">
        <title>サービス連携</title>
        <style>
            .content-wrapper {{
            display: flex;
            flex-direction: column;
            padding: 20px;
            margin: 50px auto;
            text-align: center;
            }}

            h1 {{
            margin-bottom: 20px;
            font-size: 100px;
            color: #333;
            }}

            .message {{
            font-size: 46px;
            color: #555;
            margin-bottom: 30px;
            line-height: 1.5;
            }}

            .button {{
            padding: 15px;
            border-radius: 20px;
            border: 0px;
            background-color: #007bff;
            color: white;
            font-size: 60px;
            margin: 40px 0;
            text-decoration: none;
            display: inline-block;
            transition: background-color 0.3s;
            }}

            .button:hover {{
            background-color: #0056b3;
            }}

            .cancel-link {{
            font-size: 40px;
            margin: 0 auto;
            color: #323232;
            text-decoration: none;
            }}

            .cancel-link:hover {{
            text-decoration: underline;
            }}
        </style>
        </head>
        <body>
        <div class="content-wrapper">
            <h1>サービス連携</h1>
            <div class="message">{escaped_message}</div>
            <a href="{escaped_deeplink}" class="button">アプリに戻る</a>
            <a href="#" class="cancel-link" onclick="window.close(); return false;">閉じる</a>
        </div>
        </body>
        </html>
"""


def log_callback_params(params: Dict[str, Any]) -> None:
    """
    Log callback parameters to CSV file for audit purposes.

    Args:
        params: Parameters to log
    """
    import csv
    import os

    from apps.integrations.mynaportal import CSV_LOG_FILE

    # Add timestamp
    params_with_timestamp = params.copy()
    params_with_timestamp["timestamp"] = get_current_time().isoformat()

    # Write to CSV
    file_exists = os.path.isfile(CSV_LOG_FILE)
    with open(CSV_LOG_FILE, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=params_with_timestamp.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(params_with_timestamp)


async def process_mynumber_callback(
    db: Session, state: Optional[str], code: Optional[str]
) -> tuple[str, str]:
    """
    Process MyNumber callback from MynaPortal.

    This function replicates the Django logic from old_api.py:
    1. Logs callback parameters
    2. Validates state and code parameters
    3. Processes MyNumber data through MynaGoJpApi
    4. Updates user status on successful linking
    5. Returns appropriate message and deeplink

    Args:
        db: Database session
        state: State parameter from callback
        code: Authorization code from callback

    Returns:
        Tuple of (message, deeplink)
    """
    # Default message for connection failure
    message = "マイナポータルシステムに接続できません。"

    # Log all parameters
    all_params = {"state": state, "code": code}
    log_callback_params(all_params)

    check_process = True

    # Check for access denied or certificate expired
    if code == "access_denied" or state == "Certificate expired":
        message = (
            "マイナポータルとの連携は、カードの有効期限切れによりキャンセルされました。"
        )
        check_process = False

    if check_process and state is not None:
        my_number = get_myna_authorizer_by_state(db, state)

        if my_number is None:
            # TODO: Temporary hack for testing
            code = "0000001"
            state = "00000001"
            message = "指定されたstateに対応するマイナンバーが見つかりませんでした。"
            my_number = get_myna_authorizer_by_state(db, "00000001")

            if my_number and my_number.user_id:
                user = db.get(User, my_number.user_id)
                if user:
                    user.qrcode_verified_at = datetime.now(timezone.utc)
                    user.my_portal = "linked"
                    db.add(user)
                    db.commit()

        if my_number and my_number.user_id and code is not None:
            try:
                user = db.get(User, my_number.user_id)
                if user:
                    service = MynaPortalService(code, state, db)
                    mynumber_response = await service.execute_full_workflow(user)

                    if mynumber_response is None or mynumber_response is False:
                        message = "マイナポータルの認証に失敗しました。もう一度お試しください。"
                    elif isinstance(mynumber_response, dict):
                        if mynumber_response.get("message") == "":
                            message = "ご本人は生活困窮者の支援対象外です。"
                        elif "生活保護情報" in str(
                            mynumber_response.get("message", "")
                        ):
                            message = "対象外：生活保護情報"
                        else:
                            message = f"マイナンバー連携が正常に完了しました。{mynumber_response.get('message', '')}"

                            # Update user status based on active welfare supports
                            user.qrcode_verified_at = datetime.now(timezone.utc)

                            # Check if user has any active welfare support
                            if has_active_welfare_support(db, user.id):
                                user.my_portal = "linked"
                            else:
                                user.my_portal = "not linked"

                            db.add(user)
                            db.commit()
                else:
                    message = "ユーザーデータが見つかりません。"

            except Exception as e:
                message = f"マイナポータルの処理中にエラーが発生しました: {str(e)}"
        else:
            message = "認証データが見つかりません。"
    elif check_process:
        message = "認証パラメータが不正です。"

    # Create deeplink with message using Branch.io
    deeplink_data = {"data": {"message": message, "type": "mynumber"}}
    deeplink = create_branchio_deeplink(deeplink_data)

    return message, deeplink


def get_active_user_welfare_supports(
    db: Session, user_id: str, current_date: Optional[date] = None
) -> List[UserWelfareSupport]:
    """
    Get active (currently valid) welfare supports for a user.

    Args:
        db: Database session
        user_id: User ID
        current_date: Reference date (defaults to today)

    Returns:
        List of active UserWelfareSupport instances
    """
    if current_date is None:
        current_date = date.today()

    supports = get_user_welfare_supports(db, user_id)
    active_supports: List[UserWelfareSupport] = []

    for support in supports:
        if is_welfare_support_active(
            support.start_date, support.end_date, current_date
        ):
            active_supports.append(support)

    return active_supports


def has_active_welfare_support(
    db: Session, user_id: str, current_date: Optional[date] = None
) -> bool:
    """
    Check if user has any active welfare support.

    Args:
        db: Database session
        user_id: User ID
        current_date: Reference date (defaults to today)

    Returns:
        True if user has at least one active support
    """
    active_supports = get_active_user_welfare_supports(db, user_id, current_date)
    return len(active_supports) > 0


def generate_authorize_link(db: Session, user_id: Optional[str] = None) -> str:
    """
    Generate authorization link for MynaPortal.

    This function orchestrates the complete authorization link generation process:
    1. Generates a unique state value
    2. Creates a database record for tracking
    3. Builds OAuth parameters
    4. Constructs the final authorization URL

    Args:
        db: Database session
        user_id: Optional user ID to associate with the authorizer

    Returns:
        Authorization link URL
    """
    # Step 1: Generate unique state
    state = _generate_next_state(db)

    # Step 2: Create tracking record
    _create_authorizer_record(db, state, user_id)

    # Step 3: Build OAuth parameters
    oauth_params = _build_oauth_params(state)

    # Step 4: Construct final URL
    return _construct_authorization_url(oauth_params)
