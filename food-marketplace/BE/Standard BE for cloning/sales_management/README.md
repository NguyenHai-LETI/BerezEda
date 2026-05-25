# Sales Management Module Implementation

## Overview
This document outlines the complete implementation of the sales management module for the WakeAtte API, designed to support the Japanese UI specifications for shop owners to manage their product sales.

## Module Structure

### Files Created (Following Your Project Patterns)
- `apps/sales_management/__init__.py` - Module initialization
- `apps/sales_management/constants.py` - Status definitions and UI constants
- `apps/sales_management/utils.py` - Utility functions for formatting and calculations
- `apps/sales_management/schemas.py` - Pydantic schemas for API responses
- `apps/sales_management/services.py` - Business logic following your db-first pattern
- `apps/sales_management/routers.py` - FastAPI router following your function-based pattern

## Integration with Your Project

### 1. Add to Main Application (apps/core/main.py)
```python
# Add this import with your other router imports
from apps.sales_management.routers import router as sales_management_router

# Add this line with your other router includes
app.include_router(sales_management_router, prefix="/api/sales-management")
```

### 2. Your Project Patterns I Followed

**Permission System**: Uses your `ShopOwnerOrAdminUser` type annotation
```python
def get_sales_dashboard(
    user: ShopOwnerOrAdminUser,
    db: Session = Depends(get_session),
    # ...
):
```

**Service Pattern**: Following your `db` first, then `user`, then other params pattern
```python
def get_sales_dashboard_service(db: Session, user, month: Optional[str] = None):
    # Service logic here
```

**Response Format**: Using your `ListResponse` from `apps.core.schemas`
```python
@router.get("/unsold-items", response_model=ListResponse[schemas.SalesComboItem])
def get_unsold_items(...):
    items, total = services.get_unsold_items_service(db, user, ...)
    return ListResponse(limit=limit, offset=offset, total=total, data=items)
```

**Import Style**: Importing schemas and services as modules, not individual functions
```python
from . import schemas, services
# Then use: schemas.SalesComboItem, services.get_sales_dashboard_service
```

## API Endpoints

### Sales Dashboard
- **GET** `/api/sales-management/dashboard`
- **Query Params**: `month` (YYYY-MM format, optional)
- **Response**: `schemas.SalesDashboard`
- **Permission**: Shop Owner or Admin

### Unsold Items List
- **GET** `/api/sales-management/unsold-items`
- **Query Params**: `limit`, `offset`, `status[]`, `search`
- **Response**: `ListResponse[schemas.SalesComboItem]`
- **Permission**: Shop Owner or Admin

### Sold Items List  
- **GET** `/api/sales-management/sold-items`
- **Query Params**: `limit`, `offset`, `date_from`, `date_to`
- **Response**: `ListResponse[schemas.SalesComboItem]`
- **Permission**: Shop Owner or Admin

### Item Details
- **GET** `/api/sales-management/item/{combo_id}`
- **Response**: `schemas.SalesComboItem`
- **Permission**: Shop Owner or Admin

### Available Statuses
- **GET** `/api/sales-management/statuses`
- **Response**: Dictionary with available status options

### Analytics Summary
- **GET** `/api/sales-management/analytics/summary`
- **Query Params**: `days` (1-365, defaults to 30)
- **Response**: `schemas.SalesAnalytics`
- **Permission**: Shop Owner or Admin

## Japanese UI Features

### Status Display Mapping (constants.py)
```python
STATUS_DISPLAY_MAP = {
    "locker_reserved": "ロッカー配置待ち",
    "active": "販売中", 
    "sold": "売却済み",
    "cancelled": "キャンセル済み",
    "expired": "期限切れ"
}
```

### Color Coding System
- **Blue (#007AFF)**: Active sales
- **Green (#28A745)**: Successful sales  
- **Orange (#FFC107)**: Pending actions
- **Red (#DC3545)**: Cancelled/expired items
- **Gray (#6C757D)**: Inactive states

### Countdown Timer (utils.py)
```python
def calculate_placement_countdown(created_at: datetime) -> Tuple[int, str]:
    # Returns (seconds_remaining, "X時間Y分Z秒")
```

## Database Integration

### Using Your Existing Models
- `apps.products.models.Combo` - Main product data
- `apps.lockers.models.reservation.LockerReservation` - Locker assignments
- `apps.lockers.models.unit.LockerUnit` - Unit information
- `apps.lockers.models.location.LockerLocation` - Location data

### Following Your Permission Pattern
```python
# Get user's shop ID
shop_id = getattr(user, 'code_shop', None) or getattr(user, 'shop_id', None)
if not shop_id:
    raise HTTPException(status_code=403, detail="Shop access required")
```

## Service Layer Pattern

### Your Project's Service Pattern
```python
# Returns tuple for list functions (items, total)
def get_unsold_items_service(
    db: Session,        # Database first
    user,              # User second  
    limit: int = 20,   # Other params after
    offset: int = 0,
    # ...
) -> Tuple[List[schemas.SalesComboItem], int]:
    # Implementation
    return items, total

# Returns object for single item functions
def get_sales_dashboard_service(
    db: Session, 
    user, 
    month: Optional[str] = None
) -> schemas.SalesDashboard:
    # Implementation
    return dashboard_data
```

## Error Handling (Following Your Patterns)

### Graceful Degradation
```python
# Missing locker info defaults to safe values
return {
    "location_name": "Unknown Location",
    "unit_number": "Unknown Unit", 
    "location_id": None
}
```

### Input Validation
```python
# Status filter validation
if status:
    valid_statuses = set(UNSOLD_STATUSES)
    invalid_statuses = [s for s in status if s not in valid_statuses]
    if invalid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid statuses...")
```

## Example Usage

### Get Dashboard Data
```bash
curl -X GET "http://localhost:8000/api/sales-management/dashboard?month=2024-10" \
  -H "Authorization: Bearer {token}"
```

### List Unsold Items with Filters
```bash
curl -X GET "http://localhost:8000/api/sales-management/unsold-items?limit=20&status=active&search=product" \
  -H "Authorization: Bearer {token}"
```

### Get Analytics
```bash  
curl -X GET "http://localhost:8000/api/sales-management/analytics/summary?days=30" \
  -H "Authorization: Bearer {token}"
```

## Testing the Integration

### 1. Add Router to Main App
Edit `apps/core/main.py`:
```python
from apps.sales_management.routers import router as sales_management_router
app.include_router(sales_management_router, prefix="/api/sales-management")
```

### 2. Test Endpoints
Use your existing authentication system to test the endpoints with shop owner credentials.

### 3. Verify Japanese Text
Check that status displays show Japanese text correctly in your frontend.

## Key Differences from Generic Implementation

✅ **Permission System**: Uses your `ShopOwnerOrAdminUser` instead of generic auth  
✅ **Service Pattern**: `db` first, `user` second parameter order  
✅ **Response Format**: Uses your `ListResponse[T]` pattern  
✅ **Import Style**: Module imports (`from . import schemas, services`)  
✅ **Router Style**: Function-based routers, not class-based  
✅ **Database**: Uses your `get_session` dependency  
✅ **Error Handling**: Follows your HTTPException patterns  

This implementation now perfectly matches your project's architecture and coding patterns!