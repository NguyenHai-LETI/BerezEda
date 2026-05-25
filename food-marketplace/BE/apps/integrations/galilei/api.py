from .service import galilei_service

# Use service for configuration
API_AUTHEN = galilei_service.get_auth_url()


def get_locker_detail_url(full_unit_number: str, from_date: str, to_date: str) -> str:
    """Get locker detail API URL with dynamic date parameters"""
    return galilei_service.get_locker_detail_url(full_unit_number, from_date, to_date)


# Backward compatibility
API_LOCKER_DETAIL = "Use get_locker_detail_url(from_date, to_date) instead"
