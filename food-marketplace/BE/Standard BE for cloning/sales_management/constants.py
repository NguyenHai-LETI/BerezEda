"""
Sales Management Constants

Status display mappings, time formats, and UI configuration for the sales management screen.
"""

# Status display mappings for Japanese UI
STATUS_DISPLAY_MAPPING = {
    "selling": "販売中",
    # "combo_status_price_reduced": "販売中",
    "free": "寄附実施中",
    "sold": "受け取り待ち中",
    "picked_up": "受け取り完了",
    "selling_expired": "販売時間終了",
    "deleted": "キャンセル",
    "preparation_to_locker": "預け入れ時間残り",
    "ready_for_pickup": "受け取り待ち中",
    "donation_ready_for_pickup": "受け取り待ち中  寄付",
}

# Time format constants
COUNTDOWN_TIME_FORMAT = "%H:%M:%S"
DATETIME_DISPLAY_FORMAT = "%Y/%m/%d/%H:%M"
