class fincode_error(Exception):

    def __init__(self, error_status: str, error_code: str, error_message: str):
        self.error_status = error_status
        self.error_code = error_code
        self.error_message = error_message
