IF001_01_URL = "https://app-test.api.myna.go.jp/online-authorization-web"
IF001_01_PATH = "/oauth/authorize"
IF001_03_URL = (
    "https://sp-test.api.myna.go.jp/online-authorization-web"  # get access token
)
IF001_04_URL = "https://sp-test.api.myna.go.jp/online-resource-web"  # submit data
IF001_06_URL = "https://sp-test.api.myna.go.jp/online-resource-web"

BACKEND_REDIRECT_URL = "https://staging-wake.wakeatte.net/mynumber"
FRONTEND_REDIRECT_URL = "https://staging-wake.wakeatte.net/mynumber"
SERVICE_PROVIDER_ID = "SP00000086"
SERVICE_ID = "AA0003"

MY_NUMBER = "mynumber"

# API Configuration
TELEGRAM_TYPES = {
    "REQUEST": "IFA0301-R01",
    "RESULT": "IFA0303-R01",
    "RESPONSE": "IFA0302-S01",
}

# Status values
STATUS_VALUES = {
    "WAIT_RESULT": "WAIT_RESULT",
    "REGISTER": "REGISTER",
    "ERROR": "ERROR",
    "TIMEOUT": "TIMEOUT",
}

# Date formats and defaults
INQUIRY_DATE = "20260101"

# Polling configuration
MAX_POLLING_ATTEMPTS = 36
POLLING_INTERVAL_SECONDS = 10
FAKE_STATUS_DELAY_SECONDS = 15

# CSV logging
CSV_LOG_FILE = "result_log.csv"

# Supported welfare information types
WELFARE_INFO_TYPES = {
    "LIVELIHOOD_PROTECTION": "生活保護情報",
    "SINGLE_PARENT_SUPPORT": "母子家庭自立支援給付金支給情報",
    "MOTHER_CHILD_FACILITY": "母子生活支援施設保護情報",
    "CHILD_SUPPORT": "児童扶養手当の支給情報",
}

# Date field mappings for different welfare types
DATE_FIELD_MAPPINGS = {
    "生活保護情報": {
        "start_field": "支給開始年月日",
        "end_field": "支給終了年月日",
    },
    "母子家庭自立支援給付金支給情報": {
        "start_field": "支給開始年月日",
        "end_field": "支給終了年月日",
        "nested_path": ["支給期間情報"],
    },
    "母子生活支援施設保護情報": {
        "start_field": "保護開始年月日",
        "end_field": "保護終了年月日",
    },
    "児童扶養手当の支給情報": {
        "start_field": "支給開始年月",
        "end_field": "支給終了年月",
        "nested_path": ["支給情報"],
    },
}

# Location key for data extraction
LOCATION_KEY = "神奈川県川崎市"
