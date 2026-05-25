import csv
import io
from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session

# Import from admin_sales_management for CSV export functionality
from apps.admin_sales_management import crud as admin_sales_crud
from apps.admin_sales_management.exceptions import (
    access_denied_to_locker_locations,
    access_denied_to_shops,
)
from apps.admin_sales_management.services import convert_jst_to_utc_range
from apps.core.constants import (
    ADMIN_REVENUE_PERCENTAGE,
    COMBO_STATUS_EXPIRED,
    COMBO_STATUS_SOLD,
    LOCKER_OWNER_REVENUE_PERCENTAGE,
    ORDER_STATUS_PICKED_UP,
    ORDER_STATUS_REFUNDED,
    REVENUE_COUNTABLE_ORDER_STATUSES,
)
from apps.lockers.crud import get_locker_units_by_list_locations
from apps.revenue_management import crud as revenue_crud
from apps.revenue_management import utils as revenue_utils
from apps.revenue_management.constants import (
    FIRST_HALF_LAST_YEAR,
    FIRST_HALF_THIS_YEAR,
    METRIC_CUSTOMER_COUNT,
    MONTHS_THIS_YEAR,
    QUARTERS_THIS_YEAR,
    SECOND_HALF_LAST_YEAR,
    SECOND_HALF_THIS_YEAR,
    SECOND_HALF_YEAR_BEFORE_LAST,
    SEGMENT_ONE_TIME,
    THIS_MONTH,
    THIS_QUARTER,
    THIS_WEEK,
    TIME_DURATION_FILTER,
    TODAY,
    USER_RETENTION_DURATION_FILTER,
    VALID_METRICS,
    VALID_SEGMENTS,
    WEEKS_THIS_MONTH,
)
from apps.revenue_management.crud import (
    calculate_revenue_by_month_all_locker_locations,
    get_accessible_locker_locations_by_role,
    get_lockers,
    get_orders_by_locker_units,
    get_orders_by_lockers_and_months,
    get_orders_by_shops_and_months,
    get_shop_ids_by_order_locations,
    get_shops,
    get_shops_with_pagination,
)
from apps.revenue_management.exceptions import (
    invalid_duration_exception,
    invalid_filter_params_exception,
    invalid_metric_exception,
    invalid_segment_exception,
    no_accessible_shops_exception,
)
from apps.revenue_management.schemas import (
    LockerRevenueData,
    LockerRevenueGraphData,
    LockerRevenueGraphDataResponse,
    LockerUnitData,
    MonthRevenueData,
    RevenueDashboardData,
    RevenueDashboardResponse,
    ShopRevenueDashboardData,
    ShopRevenueDashboardResponse,
    ShopRevenueData,
    ShopRevenueGraphData,
    ShopRevenueGraphDataResponse,
    UnitRevenueData,
    UserRetentionData,
    UserRetentionGraphResponse,
    UserStatisticData,
    UserStatisticGraphResponse,
)
from apps.users.models import User


def _get_jst_month(completed_at: datetime) -> int:
    """
    Convert UTC datetime to JST and extract the month.

    Args:
        completed_at: UTC datetime from order.completed_at

    Returns:
        Month number in JST timezone (1-12)
    """
    if completed_at is None:
        return None
    # Add 9 hours to convert UTC to JST
    jst_time = completed_at + timedelta(hours=9)
    return jst_time.month


def get_revenue_dashboard_data(
    db: Session,
    user: User,
    duration: Optional[str] = None,
    location_ids: Optional[List[int]] = None,
    limit: int = 20,
    offset: int = 0,
):

    year, months, start_date, end_date = _get_time_from_duration(duration)

    all_locker_location, paginated_locker_locations, total_all_locations = (
        get_accessible_locker_locations_by_role(
            db=db,
            user=user,
            location_ids=location_ids,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
    )
    if not all_locker_location:
        return []
    all_locker_location_ids = [locker.id for locker in all_locker_location]
    locker_location_ids = [locker.id for locker in paginated_locker_locations]

    all_locker_units = get_locker_units_by_list_locations(db, all_locker_location_ids)
    all_locker_unit_ids = [unit.id for unit in all_locker_units]
    locker_units = get_locker_units_by_list_locations(db, locker_location_ids)
    locker_unit_ids = [unit.id for unit in locker_units]

    # calculate revenue by month of all locker location for response
    revenue_all_lockers = calculate_revenue_by_month_all_locker_locations(
        db, user, str(year), months, all_locker_unit_ids
    )

    # get all equivalent orders one time to calculate, avoid many queries
    orders = get_orders_by_locker_units(db, locker_unit_ids, user, year, months)

    group_units_by_locations = defaultdict(list)
    for unit in locker_units:
        group_units_by_locations[unit.location_id].append(unit.id)

    monthly_revenue_each_locker_unit_in_locker_locations = (
        _calculate_monthly_revenue_by_location(
            user, orders, group_units_by_locations, year, months
        )
    )

    data = _build_response_by_mapping_data(
        db,
        months,
        paginated_locker_locations,
        revenue_all_lockers,
        monthly_revenue_each_locker_unit_in_locker_locations,
    )

    return RevenueDashboardResponse(
        limit=limit, offset=offset, total=total_all_locations, data=data
    )


def get_accessible_locker_location_service(
    db: Session,
    user: User,
    locker_name: Optional[str] = None,
):
    all_locker_location, paginated_locker_locations, total_all_locations = (
        get_accessible_locker_locations_by_role(
            db=db, user=user, locker_name=locker_name
        )
    )
    return all_locker_location, total_all_locations


def get_accessible_shops_by_locations_service(
    db: Session, location_ids: List[str]
) -> List[Dict[str, str]]:
    """
    Get accessible shops by locker location IDs based on historical orders.

    Args:
        db: Database session
        location_ids: List of locker location IDs

    Returns:
        List of dicts with shop id and name: [{"id": "...", "name": "..."}, ...]
    """
    from apps.revenue_management import crud as revenue_crud

    if not location_ids:
        return []

    shop_ids = revenue_crud.get_shop_ids_by_order_locations(db, location_ids)
    if not shop_ids:
        return []

    # Get shop objects with names
    shops = revenue_crud.get_shops(db, shop_ids=shop_ids)

    # Return list of dicts with id and name
    return [{"id": shop.id, "name": shop.name or ""} for shop in shops]


def _get_time_range(year: int, half: str) -> Tuple[int, List[int], datetime, datetime]:
    """Return year, months, start_date, end_date for a given half-year."""
    months = {
        "first_half": [1, 2, 3, 4, 5, 6],
        "second_half": [7, 8, 9, 10, 11, 12],
    }

    if half == "first_half":
        start = datetime(year, 1, 1)
        end = datetime(year, 6, 30, 23, 59, 59)
    elif half == "second_half":
        start = datetime(year, 7, 1)
        end = datetime(year, 12, 31, 23, 59, 59)
    elif half == "quarters":
        start = datetime(year, 1, 1)
        end = datetime(year, 12, 31, 23, 59, 59)
        markers = [1, 2, 3, 4]  # quarters Q1..Q4
        return year, markers, start, end
    elif half == "months":
        start = datetime(year, 1, 1)
        end = datetime(year, 12, 31, 23, 59, 59)
        markers = list(range(1, 13))  # 1..12
        return year, markers, start, end
    else:
        raise ValueError(f"Invalid half: {half}")

    return year, months[half], start, end


def _get_time_from_duration(duration: str) -> Tuple[int, List[int], datetime, datetime]:
    """Return time metadata based on duration keyword."""
    if duration not in TIME_DURATION_FILTER:
        raise invalid_duration_exception()

    current_year = datetime.now().year

    mapping = {
        FIRST_HALF_THIS_YEAR: _get_time_range(current_year, "first_half"),
        SECOND_HALF_THIS_YEAR: _get_time_range(current_year, "second_half"),
        FIRST_HALF_LAST_YEAR: _get_time_range(current_year - 1, "first_half"),
        SECOND_HALF_LAST_YEAR: _get_time_range(current_year - 1, "second_half"),
        SECOND_HALF_YEAR_BEFORE_LAST: _get_time_range(current_year - 2, "second_half"),
        QUARTERS_THIS_YEAR: _get_time_range(current_year, "quarters"),
        MONTHS_THIS_YEAR: _get_time_range(current_year, "months"),
        WEEKS_THIS_MONTH: _get_weeks_this_month_range(),
        TODAY: _get_today_range(),
    }

    return mapping[duration]


def _get_weeks_this_month_range(
    now: datetime | None = None,
) -> Tuple[int, List[int], datetime, datetime]:
    """Return year, week_numbers, start_date, end_date for current month."""
    now = now or datetime.now()
    year = now.year
    month = now.month

    last_day = monthrange(year, month)[1]
    start = datetime(year, month, 1, 0, 0, 0)
    end = datetime(year, month, last_day, 23, 59, 59)

    # week buckets: 1..ceil(last_day/7) -> 4 or 5
    num_weeks = (last_day + 6) // 7
    weeks = list(range(1, num_weeks + 1))

    return year, weeks, start, end


def _get_today_range(now: datetime | None = None):
    now = now or datetime.now()
    start = datetime(now.year, now.month, now.day, 0, 0, 0)
    end = datetime(now.year, now.month, now.day, 23, 59, 59)
    markers = [1]  # single bucket
    return now.year, markers, start, end


def _get_this_quarter_range(
    now: datetime | None = None,
) -> Tuple[int, List[int], datetime, datetime]:
    """Return year, months, start_date, end_date for current quarter only."""
    now = now or datetime.now()
    year = now.year
    month = now.month

    # Determine current quarter (Q1: 1-3, Q2: 4-6, Q3: 7-9, Q4: 10-12)
    quarter = (month - 1) // 3
    start_month = quarter * 3 + 1
    end_month = start_month + 2

    # Get last day of end_month
    last_day = monthrange(year, end_month)[1]

    start = datetime(year, start_month, 1, 0, 0, 0)
    end = datetime(year, end_month, last_day, 23, 59, 59)

    months = [start_month, start_month + 1, end_month]

    return year, months, start, end


def _get_this_month_range(
    now: datetime | None = None,
) -> Tuple[int, List[int], datetime, datetime]:
    """Return year, months, start_date, end_date for current month only."""
    now = now or datetime.now()
    year = now.year
    month = now.month

    last_day = monthrange(year, month)[1]
    start = datetime(year, month, 1, 0, 0, 0)
    end = datetime(year, month, last_day, 23, 59, 59)

    return year, [month], start, end


def _get_this_week_range(
    now: datetime | None = None,
) -> Tuple[int, List[int], datetime, datetime]:
    """Return year, week_number, start_date, end_date for current week only."""
    now = now or datetime.now()
    year = now.year

    # Get current weekday (0 = Monday, 6 = Sunday)
    weekday = now.weekday()

    # Calculate start of week (Monday)
    start = datetime(now.year, now.month, now.day, 0, 0, 0) - timedelta(days=weekday)

    # Calculate end of week (Sunday)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    # Use week number as marker
    week_number = now.isocalendar()[1]

    return year, [week_number], start, end


def _get_time_from_duration_user_retention(
    duration: str,
) -> Tuple[int, List[int], datetime, datetime]:
    """
    Return time metadata based on duration keyword for user retention API.
    This function handles THIS_QUARTER, THIS_MONTH, THIS_WEEK, and TODAY differently.
    """
    if duration not in USER_RETENTION_DURATION_FILTER:
        raise invalid_duration_exception()

    current_year = datetime.now().year

    mapping = {
        FIRST_HALF_THIS_YEAR: _get_time_range(current_year, "first_half"),
        SECOND_HALF_THIS_YEAR: _get_time_range(current_year, "second_half"),
        THIS_QUARTER: _get_this_quarter_range(),
        THIS_MONTH: _get_this_month_range(),
        THIS_WEEK: _get_this_week_range(),
        TODAY: _get_today_range(),
    }

    return mapping[duration]


def _build_response_by_mapping_data(
    db: Session,
    months: List[int],
    paginated_locker_locations: list,
    revenue_all_lockers: List[Tuple[str, float]],
    monthly_revenue_each_locker_unit: Dict[str, Dict[str, Dict[str, float]]],
) -> RevenueDashboardData:
    """
    Transform mapping results into RevenueDashboardData format.
    """

    def format_number(value: float) -> str:
        try:
            val = float(value)
            if val.is_integer():
                return f"{val:,.0f}"
            return f"{val:,.2f}"
        except Exception:
            return str(value)

    # Pre-compute month strings and revenue lookup
    month_strings = [f"{month:02d}" for month in months]
    revenue_lookup = {month: revenue for month, revenue in revenue_all_lockers}
    total_revenue = sum(
        revenue for month, revenue in revenue_all_lockers if month != "all_months"
    )

    # Create month_revenue_all_locker using list comprehension
    month_revenue_all_locker = [
        MonthRevenueData(
            month=month_str,
            sum_final_price=format_number(revenue_lookup.get(month_str, 0.0)),
        )
        for month_str in month_strings
    ] + [
        MonthRevenueData(
            month="all_months", sum_final_price=format_number(total_revenue)
        )
    ]

    # Batch query all units for all locations at once
    location_ids = [loc.id for loc in paginated_locker_locations]
    all_units = get_locker_units_by_list_locations(db, location_ids)

    # Group units by location_id
    units_by_location = defaultdict(list)
    for unit in all_units:
        units_by_location[unit.location_id].append(unit)

    # Pre-compute revenue cache per location
    location_revenue_cache = {}
    for location_id, units_data in monthly_revenue_each_locker_unit.items():
        location_monthly_revenue = {}
        for unit_id, unit_monthly_data in units_data.items():
            for month, revenue in unit_monthly_data.items():
                location_monthly_revenue[month] = (
                    location_monthly_revenue.get(month, 0.0) + revenue
                )
        location_revenue_cache[location_id] = location_monthly_revenue

    # Helper to create monthly revenue with "all_months" first
    def _create_monthly_revenue_data(
        revenue_data: Dict[str, float],
    ) -> List[MonthRevenueData]:
        total = sum(revenue_data.get(month_str, 0.0) for month_str in month_strings)
        monthly_data = [
            MonthRevenueData(month="all_months", sum_final_price=format_number(total))
        ] + [
            MonthRevenueData(
                month=month_str,
                sum_final_price=format_number(revenue_data.get(month_str, 0.0)),
            )
            for month_str in month_strings
        ]
        return monthly_data

    # Helper to create unit revenue with "all_months" first
    def _create_unit_revenue_data(
        unit_revenue_data: Dict[str, float],
    ) -> List[UnitRevenueData]:
        total = sum(
            unit_revenue_data.get(month_str, 0.0) for month_str in month_strings
        )
        unit_data = [
            UnitRevenueData(month="all_months", sum_final_price=format_number(total))
        ] + [
            UnitRevenueData(
                month=month_str,
                sum_final_price=format_number(unit_revenue_data.get(month_str, 0.0)),
            )
            for month_str in month_strings
        ]
        return unit_data

    # Build full response
    lockers = []
    for locker_location in paginated_locker_locations:
        location_id = locker_location.id
        units = units_by_location.get(location_id, [])
        location_revenue_data = monthly_revenue_each_locker_unit.get(location_id, {})
        location_monthly_revenue = location_revenue_cache.get(location_id, {})

        month_revenue = _create_monthly_revenue_data(location_monthly_revenue)

        units_data = [
            LockerUnitData(
                unit_id=unit.id,
                unit_number=unit.unit_number,
                monthly_revenue=_create_unit_revenue_data(
                    location_revenue_data.get(unit.id, {})
                ),
            )
            for unit in units
        ]

        lockers.append(
            LockerRevenueData(
                locker_location_id=location_id,
                name=locker_location.name,
                code=locker_location.code,
                monthly_revenue=month_revenue,
                units=units_data,
            )
        )

    return RevenueDashboardData(
        monthly_revenue_all_locker=month_revenue_all_locker,
        lockers=lockers,
    )


def _calculate_monthly_revenue_by_location(
    user: User,
    orders: List[Any],
    location_group: Dict[str, List[str]],
    year: int,
    months: List[int],
) -> Dict[str, Dict[str, Dict[str, float]]]:

    picked_status = ORDER_STATUS_PICKED_UP
    locker_owner_status = {
        ORDER_STATUS_PICKED_UP
    }
    excluded_status = ORDER_STATUS_REFUNDED

    # Precompute mapping locker_unit_id -> location_id
    locker_to_location: Dict[str, str] = {}
    for loc_id, lockers in location_group.items():
        for lid in lockers:
            if lid is None:
                continue
            locker_to_location[lid.strip()] = loc_id

    # Prepare result skeleton with zeros
    month_keys = [f"{m:02d}" for m in months]
    result: Dict[str, Dict[str, Dict[str, float]]] = {}
    for loc_id, lockers in location_group.items():
        result[loc_id] = {}
        for lid in lockers:
            lid = lid.strip()
            result[loc_id][lid] = {mk: 0.0 for mk in month_keys}

    def _extract_order(obj: Any):
        # support rows like (Order(),) or Order instance
        if isinstance(obj, (list, tuple)) and len(obj) > 0:
            cand = obj[0]
        else:
            cand = obj
        return cand

    for row in orders:

        o = _extract_order(row)
        completed_at = getattr(o, "completed_at", None)
        status = getattr(o, "status", None)
        locker_unit_id = getattr(o, "locker_unit_id", None)

        if not isinstance(completed_at, datetime):
            continue

        if status == excluded_status:
            continue

        # Convert UTC to JST before extracting year and month
        completed_at_jst = completed_at + timedelta(hours=9)
        if completed_at_jst.year != year:
            continue

        month = completed_at_jst.month
        if month not in months:
            continue
        month_key = f"{month:02d}"

        locker_unit_id = locker_unit_id.strip()
        loc_id = locker_to_location.get(locker_unit_id)
        if not loc_id:
            continue

        if user.permissions == "owner_locker":
            if status not in locker_owner_status:
                continue
            multiplier = LOCKER_OWNER_REVENUE_PERCENTAGE
        else:
            if status != picked_status:
                continue
            multiplier = ADMIN_REVENUE_PERCENTAGE

        final_price = getattr(o, "final_price", 0.0) or 0.0
        value = final_price * multiplier

        result[loc_id][locker_unit_id][month_key] += value
    return result


def get_shop_revenue_dashboard_data(
    db: Session,
    duration: Optional[str] = None,
    shop_ids: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
):

    year, months, _start_date, _end_date = _get_time_from_duration(duration)

    all_shops, paginated_shops, total_all_shops = get_shops_with_pagination(
        db=db, shop_ids=shop_ids, end_date=_end_date, limit=limit, offset=offset
    )

    if not all_shops:
        return []

    month_keys = [f"{m:02d}" for m in months]
    all_shop_ids = [s.id for s in all_shops]
    orders = get_orders_by_shops_and_months(db, all_shop_ids, year, months)

    # Aggregate revenue per shop per month
    per_shop: Dict[str, Dict[str, float]] = {
        sid: {mk: 0.0 for mk in month_keys} for sid in all_shop_ids
    }
    for row in orders:
        order = row[0] if isinstance(row, (list, tuple)) else row
        if not getattr(order, "completed_at", None):
            continue
        # Convert UTC to JST before extracting month
        jst_month = _get_jst_month(order.completed_at)
        mk = f"{jst_month:02d}"
        sid = getattr(order, "shop_id", None)
        if not sid:
            continue
        per_shop[sid][mk] = per_shop[sid].get(mk, 0.0) + float(
            getattr(order, "final_price", 0.0) or 0.0
        )

    def fmt(val: float) -> str:
        if float(val).is_integer():
            return f"{float(val):,.0f}"
        return f"{float(val):,.2f}"

    # Build monthly_revenue_all_shop as sum across selected set: if shop_ids provided, use only them, else all_shops
    selected_shop_ids = [s for s in (shop_ids or all_shop_ids) if s in per_shop]
    totals_by_month: Dict[str, float] = {mk: 0.0 for mk in month_keys}
    for sid in selected_shop_ids:
        for mk in month_keys:
            totals_by_month[mk] += per_shop.get(sid, {}).get(mk, 0.0)
    total_all = sum(totals_by_month.values())

    monthly_revenue_all_shop = [
        MonthRevenueData(month=mk, sum_final_price=fmt(totals_by_month.get(mk, 0.0)))
        for mk in month_keys
    ] + [MonthRevenueData(month="all_months", sum_final_price=fmt(total_all))]

    # Build shops list (paginated)
    shops_list: List[ShopRevenueData] = []
    for shop in paginated_shops:
        per_month = per_shop.get(shop.id, {})
        total_shop = sum(per_month.get(mk, 0.0) for mk in month_keys)
        monthly = [
            MonthRevenueData(month="all_months", sum_final_price=fmt(total_shop))
        ] + [
            MonthRevenueData(month=mk, sum_final_price=fmt(per_month.get(mk, 0.0)))
            for mk in month_keys
        ]
        shops_list.append(
            ShopRevenueData(
                shop_id=shop.id,
                shop_name=shop.name or "",
                monthly_revenue=monthly,
            )
        )

    data = ShopRevenueDashboardData(
        limit=limit,
        offset=offset,
        total=total_all_shops,
        monthly_revenue_all_shop=monthly_revenue_all_shop,
        shops=shops_list,
    )
    return ShopRevenueDashboardResponse(
        limit=limit, offset=offset, total=total_all_shops, data=data
    )


def get_revenue_graph_by_shop_data(
    db: Session,
    duration: str,
    shop_ids: List[str],
):
    year, markers, _start_date, _end_date = _get_time_from_duration(duration)
    shops = get_shops(db=db, shop_ids=shop_ids, end_date=_end_date)

    if duration == QUARTERS_THIS_YEAR:
        duration_data = [f"{q}Q" for q in markers]
    elif duration == WEEKS_THIS_MONTH:
        duration_data = [f"{w}週" for w in markers]
    elif duration == TODAY:
        # duration_data = ["今日"]
        today = datetime.now()
        duration_data = [f"{today.year}年{today.month}月{today.day}日"]
    else:
        duration_data = [f"{m}月" for m in markers]

    if not shops:
        return ShopRevenueGraphDataResponse(
            legend=[],
            xaxis=duration_data,
            series=[],
        )

    shop_name: List[str] = []
    revenue: List[ShopRevenueGraphData] = []

    for shop in shops:
        shop_name.append(shop.name)
        revenue.append(
            ShopRevenueGraphData(
                name=shop.name,
                data=[0.0] * len(duration_data),
            )
        )

    if duration in (FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, MONTHS_THIS_YEAR):
        months = markers  # half-year: [1..6]/[7..12], months: [1..12]
        _fill_revenue_graph_half_year_this_year_by_shop(
            db=db,
            shops=shops,
            year=year,
            months=months,
            revenue=revenue,
        )
    elif duration == QUARTERS_THIS_YEAR:
        _fill_revenue_graph_quarters_this_year_by_shop(
            db=db,
            shops=shops,
            year=year,
            revenue=revenue,
        )
    elif duration == WEEKS_THIS_MONTH:
        _fill_revenue_graph_weeks_this_month_by_shop(
            db=db,
            shops=shops,
            year=year,
            start_date=_start_date,
            end_date=_end_date,
            revenue=revenue,
        )
    elif duration == TODAY:
        _fill_revenue_graph_today_by_shop(
            db=db,
            shops=shops,
            year=year,
            start_date=_start_date,
            end_date=_end_date,
            revenue=revenue,
        )

    return ShopRevenueGraphDataResponse(
        legend=shop_name,
        xaxis=duration_data,
        series=revenue,
    )


def _fill_revenue_graph_half_year_this_year_by_shop(
    db: Session,
    shops,
    year: int,
    months: List[int],
    revenue,  # List[ShopRevenueGraphData]
):
    shop_index_map: Dict[str, int] = {shop.id: idx for idx, shop in enumerate(shops)}
    month_to_index = {m: i for i, m in enumerate(months)}

    orders = get_orders_by_shops_and_months(
        db, list(shop_index_map.keys()), year, months
    )

    for row in orders:
        order = row[0] if isinstance(row, (list, tuple)) else row

        if not order.completed_at:
            continue

        shop_idx = shop_index_map.get(order.shop_id)
        if shop_idx is None:
            continue

        # Convert UTC to JST before extracting month
        jst_month = _get_jst_month(order.completed_at)
        month_idx = month_to_index.get(jst_month)
        if month_idx is None:
            continue

        revenue[shop_idx].data[month_idx] += float(order.final_price or 0.0)


def _fill_revenue_graph_quarters_this_year_by_shop(
    db: Session,
    shops,
    year: int,
    revenue,  # List[ShopRevenueGraphData], data length = 4
):
    """
    Fill revenue for QUARTERS_THIS_YEAR.
    Bucket rule (JP business standard):
      Q1: 1-3, Q2: 4-6, Q3: 7-9, Q4: 10-12
    """
    if not shops:
        return

    shop_index_map: Dict[str, int] = {shop.id: idx for idx, shop in enumerate(shops)}
    shop_ids = list(shop_index_map.keys())

    months = list(range(1, 13))  # need full year months to compute quarters
    orders = get_orders_by_shops_and_months(db, shop_ids, year, months)

    for row in orders:
        order = row[0] if isinstance(row, (list, tuple)) else row

        if not order.completed_at:
            continue

        shop_idx = shop_index_map.get(order.shop_id)
        if shop_idx is None:
            continue

        # Convert UTC to JST before extracting month
        m = _get_jst_month(order.completed_at)  # 1..12
        quarter_idx = (m - 1) // 3  # 0..3

        revenue[shop_idx].data[quarter_idx] += float(order.final_price or 0.0)


def _fill_revenue_graph_weeks_this_month_by_shop(
    db: Session,
    shops,
    year: int,
    start_date,
    end_date,
    revenue,  # List[ShopRevenueGraphData], data length = 4 or 5
):
    """
    Fill revenue for WEEKS_THIS_MONTH (今月の週).
    Week buckets:
      1週: day 1-7
      2週: day 8-14
      3週: day 15-21
      4週: day 22-28
      5週: day 29-end (if exists)
    """
    if not shops:
        return

    shop_index_map: Dict[str, int] = {shop.id: idx for idx, shop in enumerate(shops)}
    shop_ids = list(shop_index_map.keys())

    # Current month is derived from start_date (it is 1st day of current month by your _get_weeks_this_month_range)
    month = start_date.month

    # Query orders in this month via existing helper
    orders = get_orders_by_shops_and_months(db, shop_ids, year, [month])

    num_weeks = len(revenue[0].data) if revenue else 0  # 4 or 5

    for row in orders:
        order = row[0] if isinstance(row, (list, tuple)) else row

        if not order.completed_at:
            continue

        # Ensure it is within this month range (extra safety)
        if order.completed_at < start_date or order.completed_at > end_date:
            continue

        shop_idx = shop_index_map.get(order.shop_id)
        if shop_idx is None:
            continue

        # Convert UTC to JST before extracting day
        completed_at_jst = order.completed_at + timedelta(hours=9)
        day = completed_at_jst.day  # 1..31
        week_idx = (day - 1) // 7  # 0..4

        if 0 <= week_idx < num_weeks:
            revenue[shop_idx].data[week_idx] += float(order.final_price or 0.0)


def _fill_revenue_graph_today_by_shop(
    db: Session,
    shops,
    year: int,
    start_date,
    end_date,
    revenue,  # List[ShopRevenueGraphData], data length = 1
):
    """
    Fill revenue for TODAY (今日).
    Single bucket at index 0.
    """
    if not shops:
        return

    shop_index_map: Dict[str, int] = {shop.id: idx for idx, shop in enumerate(shops)}
    shop_ids = list(shop_index_map.keys())

    month = start_date.month  # today is within this month

    orders = get_orders_by_shops_and_months(db, shop_ids, year, [month])

    for row in orders:
        order = row[0] if isinstance(row, (list, tuple)) else row

        if not order.completed_at:
            continue

        # Ensure it is today (extra safety)
        if order.completed_at < start_date or order.completed_at > end_date:
            continue

        shop_idx = shop_index_map.get(order.shop_id)
        if shop_idx is None:
            continue

        # Single bucket
        revenue[shop_idx].data[0] += float(order.final_price or 0.0)


def get_revenue_graph_by_locker_data(
    db: Session,
    user: User,
    duration: str,
    locker_ids: List[str],
):
    # Calculate revenue multiplier based on user role
    if user.role == "owner_locker":
        revenue_multiplier = LOCKER_OWNER_REVENUE_PERCENTAGE
    else:  # admin or owner_shop
        revenue_multiplier = ADMIN_REVENUE_PERCENTAGE

    year, markers, _start_date, _end_date = _get_time_from_duration(duration)
    lockers = get_lockers(db=db, locker_ids=locker_ids, end_date=_end_date)
    if duration == QUARTERS_THIS_YEAR:
        duration_data = [f"{q}Q" for q in markers]
    elif duration == WEEKS_THIS_MONTH:
        duration_data = [f"{w}週" for w in markers]
    elif duration == TODAY:
        # duration_data = ["今日"]
        today = datetime.now()
        duration_data = [f"{today.year}年{today.month}月{today.day}日"]
    else:
        duration_data = [f"{m}月" for m in markers]

    if not lockers:
        return LockerRevenueGraphDataResponse(
            legend=[],
            xaxis=duration_data,
            series=[],
        )

    locker_name: List[str] = []
    revenue: List[LockerRevenueGraphData] = []

    for locker in lockers:
        locker_name.append(locker.name)
        revenue.append(
            LockerRevenueGraphData(
                name=locker.name,
                data=[0.0] * len(duration_data),
            )
        )

    if duration in (FIRST_HALF_THIS_YEAR, SECOND_HALF_THIS_YEAR, MONTHS_THIS_YEAR):
        months = markers
        _fill_revenue_graph_half_year_this_year_by_locker(
            db=db,
            lockers=lockers,
            year=year,
            months=months,
            revenue=revenue,
            revenue_multiplier=revenue_multiplier,
        )
    elif duration == QUARTERS_THIS_YEAR:
        _fill_revenue_graph_quarters_this_year_by_locker(
            db=db,
            lockers=lockers,
            year=year,
            revenue=revenue,
            revenue_multiplier=revenue_multiplier,
        )
    elif duration == WEEKS_THIS_MONTH:
        _fill_revenue_graph_weeks_this_month_by_locker(
            db=db,
            lockers=lockers,
            year=year,
            start_date=_start_date,
            end_date=_end_date,
            revenue=revenue,
            revenue_multiplier=revenue_multiplier,
        )
    elif duration == TODAY:
        _fill_revenue_graph_today_by_locker(
            db=db,
            lockers=lockers,
            year=year,
            start_date=_start_date,
            end_date=_end_date,
            revenue=revenue,
            revenue_multiplier=revenue_multiplier,
        )

    return LockerRevenueGraphDataResponse(
        legend=locker_name,
        xaxis=duration_data,
        series=revenue,
    )


def _fill_revenue_graph_half_year_this_year_by_locker(
    db: Session,
    lockers,
    year: int,
    months: List[int],
    revenue,
    revenue_multiplier: float,
):
    locker_index_map: Dict[str, int] = {lk.id: idx for idx, lk in enumerate(lockers)}
    month_to_index = {m: i for i, m in enumerate(months)}

    rows = get_orders_by_lockers_and_months(
        db, list(locker_index_map.keys()), year, months
    )

    for order, location_id in rows:
        locker_idx = locker_index_map.get(location_id)
        if locker_idx is None:
            continue

        # Convert UTC to JST before extracting month
        jst_month = _get_jst_month(order.completed_at)
        month_idx = month_to_index.get(jst_month)
        if month_idx is None:
            continue

        revenue[locker_idx].data[month_idx] += (
            float(order.final_price or 0.0) * revenue_multiplier
        )


def _fill_revenue_graph_quarters_this_year_by_locker(
    db: Session,
    lockers,
    year: int,
    revenue,
    revenue_multiplier: float,
):
    locker_index_map: Dict[str, int] = {lk.id: idx for idx, lk in enumerate(lockers)}

    # quarters need months 1..12
    months = list(range(1, 13))

    rows = get_orders_by_lockers_and_months(
        db, list(locker_index_map.keys()), year, months
    )

    for order, location_id in rows:
        locker_idx = locker_index_map.get(location_id)
        if locker_idx is None:
            continue

        # Convert UTC to JST before extracting month
        jst_month = _get_jst_month(order.completed_at)
        quarter_idx = (jst_month - 1) // 3  # 0..3

        revenue[locker_idx].data[quarter_idx] += (
            float(order.final_price or 0.0) * revenue_multiplier
        )


def _fill_revenue_graph_weeks_this_month_by_locker(
    db: Session,
    lockers,
    year: int,
    start_date,
    end_date,
    revenue,
    revenue_multiplier: float,
):
    locker_index_map: Dict[str, int] = {lk.id: idx for idx, lk in enumerate(lockers)}

    months = [start_date.month]

    rows = get_orders_by_lockers_and_months(
        db, list(locker_index_map.keys()), year, months
    )

    num_weeks = len(revenue[0].data) if revenue else 0  # 4 or 5

    for order, location_id in rows:
        locker_idx = locker_index_map.get(location_id)
        if locker_idx is None:
            continue

        if order.completed_at < start_date or order.completed_at > end_date:
            continue

        # Convert UTC to JST before extracting day
        completed_at_jst = order.completed_at + timedelta(hours=9)
        day = completed_at_jst.day
        week_idx = (day - 1) // 7

        if 0 <= week_idx < num_weeks:
            revenue[locker_idx].data[week_idx] += (
                float(order.final_price or 0.0) * revenue_multiplier
            )


def _fill_revenue_graph_today_by_locker(
    db: Session,
    lockers,
    year: int,
    start_date,
    end_date,
    revenue,  # List[LockerRevenueGraphData], data length = 1
    revenue_multiplier: float,
):
    locker_index_map: Dict[str, int] = {lk.id: idx for idx, lk in enumerate(lockers)}

    months = [start_date.month]

    rows = get_orders_by_lockers_and_months(
        db, list(locker_index_map.keys()), year, months
    )

    for order, location_id in rows:
        locker_idx = locker_index_map.get(location_id)
        if locker_idx is None:
            continue

        if order.completed_at < start_date or order.completed_at > end_date:
            continue

        revenue[locker_idx].data[0] += (
            float(order.final_price or 0.0) * revenue_multiplier
        )


def _calculate_statistics_by_age_group(
    orders_with_users,
    entity_stats: Dict,
    age_groups: List[str],
    metric: str,
    revenue_multiplier: float = 1.0,
):
    """
    Calculate statistics (count or revenue) by age group.

    Args:
        orders_with_users: List of (order, user, entity_id) tuples
        entity_stats: Dict to store statistics {entity_id: {age_group: data}}
        age_groups: List of age group labels
        metric: CUSTOMER_COUNT or REVENUE
        revenue_multiplier: Multiplier for revenue calculation (default: 1.0)
    """

    for order, user, entity_id in orders_with_users:
        if entity_id not in entity_stats:
            continue

        age = _calculate_age(user.birthday) if user and user.birthday else None
        age_group = _get_age_group(age)

        if age_group not in entity_stats[entity_id]:
            continue

        if metric == METRIC_CUSTOMER_COUNT:
            if user:
                entity_stats[entity_id][age_group].add(user.id)
        else:  # REVENUE
            entity_stats[entity_id][age_group] += (
                float(order.final_price or 0.0) * revenue_multiplier
            )


def _build_statistics_response(
    entities,
    entity_stats: Dict,
    age_groups: List[str],
    metric: str,
):
    """Build response with statistics data."""

    legend = []
    series = []

    for entity in entities:
        legend.append(entity.name)
        if metric == METRIC_CUSTOMER_COUNT:
            data = [len(entity_stats[entity.id][ag]) for ag in age_groups]
        else:  # REVENUE
            data = [entity_stats[entity.id][ag] for ag in age_groups]
        series.append(UserStatisticData(name=entity.name, data=data))

    return legend, series


def get_user_statistics_graph_data(
    db: Session,
    user: User,
    duration: str,
    metric: str,
    locker_ids: Optional[List[str]] = None,
    shop_ids: Optional[List[str]] = None,
):
    """
    Get user age group statistics for lockers or shops.

    Args:
        db: Database session
        user: User making the request
        duration: Time duration filter (THIS_QUARTER, THIS_MONTH, THIS_WEEK, TODAY, etc.)
        metric: CUSTOMER_COUNT or REVENUE
        locker_ids: Optional list of locker IDs
        shop_ids: Optional list of shop IDs

    Returns:
        UserStatisticGraphResponse with age group statistics
    """
    # Validate
    if metric not in VALID_METRICS:
        raise invalid_metric_exception()

    if (locker_ids and shop_ids) or (not locker_ids and not shop_ids):
        raise invalid_filter_params_exception()

    # Calculate revenue multiplier based on user role
    if user.role == "owner_locker":
        revenue_multiplier = LOCKER_OWNER_REVENUE_PERCENTAGE
    else:  # admin or owner_shop
        revenue_multiplier = ADMIN_REVENUE_PERCENTAGE

    # Get time range and age groups using user retention specific duration handler
    year, markers, start_date, end_date = _get_time_from_duration_user_retention(
        duration
    )
    age_groups = ["20歳未満", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"]

    # Get entities (lockers or shops)
    if locker_ids:
        entities = get_lockers(db=db, locker_ids=locker_ids, end_date=end_date)
        if not entities:
            return UserStatisticGraphResponse(legend=[], xaxis=age_groups, series=[])

        orders_with_users = revenue_crud.get_orders_with_users_by_lockers(
            db, locker_ids, start_date, end_date
        )
    else:  # shop_ids
        entities = get_shops(db=db, shop_ids=shop_ids, end_date=end_date)
        if not entities:
            return UserStatisticGraphResponse(legend=[], xaxis=age_groups, series=[])

        orders_with_users = revenue_crud.get_orders_with_users_by_shops(
            db, shop_ids, start_date, end_date
        )

    # Initialize statistics structure
    if metric == METRIC_CUSTOMER_COUNT:
        entity_stats = {
            entity.id: {ag: set() for ag in age_groups} for entity in entities
        }
    else:  # REVENUE
        entity_stats = {
            entity.id: {ag: 0.0 for ag in age_groups} for entity in entities
        }

    # Calculate statistics
    _calculate_statistics_by_age_group(
        orders_with_users, entity_stats, age_groups, metric, revenue_multiplier
    )

    # Build response
    legend, series = _build_statistics_response(
        entities, entity_stats, age_groups, metric
    )

    return UserStatisticGraphResponse(
        legend=legend,
        xaxis=age_groups,
        series=series,
    )


def _calculate_age(birthday: datetime) -> Optional[int]:
    """Calculate age from birthday."""
    if not birthday:
        return None
    today = datetime.now()
    age = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        age -= 1
    return age


def _get_age_group(age: Optional[int]) -> str:
    """Get age group label from age."""
    if age is None:
        return "不明"
    if age < 20:
        return "20歳未満"
    elif age < 30:
        return "20-29歳"
    elif age < 40:
        return "30-39歳"
    elif age < 50:
        return "40-49歳"
    elif age < 60:
        return "50-59歳"
    else:
        return "60歳以上"


def get_user_retention_graph_data(
    db: Session,
    duration: str,
    segment: str,
    shop_ids: List[str],
):
    """
    Get user retention statistics for shops.

    Args:
        db: Database session
        duration: Time duration filter (THIS_QUARTER, THIS_MONTH, THIS_WEEK, TODAY, etc.)
        segment: ONE_TIME or RETURNING
        shop_ids: List of shop IDs

    Returns:
        UserRetentionGraphResponse with retention rates
    """
    # Validate segment
    if segment not in VALID_SEGMENTS:
        raise invalid_segment_exception()

    # Get time range using user retention specific duration handler
    year, markers, start_date, end_date = _get_time_from_duration_user_retention(
        duration
    )

    # Get shops
    shops = get_shops(db=db, shop_ids=shop_ids, end_date=end_date)
    if not shops:
        return UserRetentionGraphResponse(legend=[], series=[])

    # Get orders for all shops
    orders = revenue_crud.get_orders_by_shops_with_date_range(
        db, shop_ids, start_date, end_date
    )

    # Group orders by shop and user
    shop_user_orders = defaultdict(lambda: defaultdict(int))
    for order in orders:
        if order.user_id and order.shop_id:
            shop_user_orders[order.shop_id][order.user_id] += 1

    # Calculate retention rates
    legend = []
    series = []

    for shop in shops:
        shop_id = shop.id
        user_order_counts = shop_user_orders.get(shop_id, {})

        if not user_order_counts:
            # No orders for this shop
            legend.append(shop.name)
            series.append(UserRetentionData(name=shop.name, data=[0.0]))
            continue

        total_customers = len(user_order_counts)

        if segment == SEGMENT_ONE_TIME:
            # Count users with exactly 1 order
            one_time_customers = sum(
                1 for count in user_order_counts.values() if count == 1
            )
            retention_rate = (
                (one_time_customers / total_customers * 100)
                if total_customers > 0
                else 0.0
            )
        else:  # SEGMENT_RETURNING
            # Count users with 2 or more orders
            returning_customers = sum(
                1 for count in user_order_counts.values() if count >= 2
            )
            retention_rate = (
                (returning_customers / total_customers * 100)
                if total_customers > 0
                else 0.0
            )

        legend.append(shop.name)
        series.append(
            UserRetentionData(name=shop.name, data=[round(retention_rate, 2)])
        )

    return UserRetentionGraphResponse(
        legend=legend,
        series=series,
    )


def _build_combined_structure(
    assoc_structure: Dict[str, List[str]],
    combos_data: Dict,
    locker_ids: Optional[List[str]],
    shop_ids: List[str],
) -> Dict[str, List[str]]:
    """Build and filter locker-shop structure from associations and combos."""
    structure = defaultdict(set)

    # 1. Add current associations from ShopLockerAssociation
    for lid, sids in assoc_structure.items():
        if not locker_ids or lid in locker_ids:
            for sid in sids:
                if sid in shop_ids:
                    structure[lid].add(sid)

    # 2. Add from historical combos (covers deleted associations)
    for data in combos_data.values():
        locker_location = data.get("locker_location")
        shop = data.get("shop")
        if locker_location and shop:
            lid = locker_location.id
            sid = shop.id
            # Note: combos_data is already filtered by get_combos_with_filters
            # but we re-check for consistency with input params
            if (not locker_ids or lid in locker_ids) and sid in shop_ids:
                structure[lid].add(sid)

    return {lid: sorted(list(sids)) for lid, sids in structure.items() if sids}


def _initialize_metrics_structure(
    locker_shop_structure: Dict[str, List[str]],
    locker_name_map: Dict[str, str],
    shop_name_map: Dict[str, str],
) -> Dict[str, Dict[str, Dict]]:
    """Initialize metrics structure with zeros."""
    grouped = {}
    for locker_id, shop_ids in locker_shop_structure.items():
        grouped[locker_id] = {}
        for shop_id in shop_ids:
            grouped[locker_id][shop_id] = {
                "locker_id": locker_id,
                "locker_name": locker_name_map.get(locker_id, ""),
                "shop_id": shop_id,
                "shop_name": shop_name_map.get(shop_id, ""),
                "total_sold": 0,
                "sold_donated": 0,
                "sold_non_donated": 0,
                "unsold": 0,
                "total_revenue": 0.0,
            }
    return grouped


def _populate_metrics_from_combos(
    grouped_by_locker: Dict[str, Dict[str, Dict]],
    combos_data: Dict,
    combos: List,
    orders: Dict,
    revenue_multiplier: float = 1.0,
) -> None:
    """Populate metrics from combo data (modifies grouped_by_locker in place)."""
    for combo in combos:
        data = combos_data.get(combo.id)
        if not data:
            continue

        locker_location = data.get("locker_location")
        shop = data.get("shop")

        if not locker_location:
            continue

        locker_id = locker_location.id
        shop_id = shop.id if shop else None

        # Skip if not in our structure
        if (
            locker_id not in grouped_by_locker
            or shop_id not in grouped_by_locker[locker_id]
        ):
            continue

        order = orders.get(combo.id)

        # Update metrics
        if combo.status == COMBO_STATUS_SOLD and order:
            final_price = order.final_price or 0.0
            grouped_by_locker[locker_id][shop_id]["total_sold"] += 1
            grouped_by_locker[locker_id][shop_id]["total_revenue"] += (
                final_price * revenue_multiplier
            )
            if final_price == 0:
                grouped_by_locker[locker_id][shop_id]["sold_donated"] += 1
            else:
                grouped_by_locker[locker_id][shop_id]["sold_non_donated"] += 1
        elif combo.status == COMBO_STATUS_EXPIRED:
            grouped_by_locker[locker_id][shop_id]["unsold"] += 1


def _convert_to_sorted_rows(
    grouped_by_locker: Dict[str, Dict[str, Dict]],
    locker_name_map: Dict[str, str],
    shop_name_map: Dict[str, str],
) -> List[Dict]:
    """Convert grouped data to sorted flat list."""
    rows = []
    sorted_lockers = sorted(
        grouped_by_locker.items(), key=lambda x: locker_name_map.get(x[0], "")
    )

    for locker_id, shops_data in sorted_lockers:
        sorted_shops = sorted(
            shops_data.items(), key=lambda x: shop_name_map.get(x[0], "")
        )

        for shop_id, metrics in sorted_shops:
            rows.append(
                {
                    "locker_name": metrics["locker_name"],
                    "shop_name": metrics["shop_name"],
                    "total_sold": metrics["total_sold"],
                    "sold_donated": metrics["sold_donated"],
                    "sold_non_donated": metrics["sold_non_donated"],
                    "unsold": metrics["unsold"],
                    "total_revenue": metrics["total_revenue"],
                }
            )

    return rows


def generate_csv_export_service(
    db: Session,
    user: User,
    shop_ids: Optional[List[str]] = None,
    locker_location_ids: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[str, str]:
    """
    Generate CSV export data grouped by locker_location and shop.

    Args:
        db: Database session
        user: User making the request
        shop_ids: Optional list of shop IDs to filter
        locker_location_ids: Optional list of locker location IDs to filter
        start_date: Optional start date (JST)
        end_date: Optional end date (JST)

    Returns:
        Tuple of (csv_content, filename)
    """
    from apps.revenue_management import crud as revenue_crud
    from apps.revenue_management import validators

    # 1. Validate inputs
    validators.validate_date_range(start_date, end_date)

    # 2. Get and validate access control
    accessible_location_ids, invalid_lockers = revenue_crud.get_accessible_locker_ids(
        db, user, locker_location_ids
    )
    if invalid_lockers:
        raise access_denied_to_locker_locations(invalid_lockers)

    filtered_shop_ids, invalid_shops = _get_accessible_shop_ids(
        db, accessible_location_ids, shop_ids
    )
    if invalid_shops:
        raise access_denied_to_shops(invalid_shops)

    if not filtered_shop_ids:
        raise no_accessible_shops_exception()

    # 3. Convert JST dates to UTC and get combo data
    start_date_utc, end_date_utc = None, None
    if start_date and end_date:
        start_date_utc, end_date_utc = convert_jst_to_utc_range(start_date, end_date)

    combos_data = admin_sales_crud.get_combos_with_filters(
        db=db,
        filtered_shop_ids=filtered_shop_ids,
        accessible_location_ids=accessible_location_ids,
        search_text=None,
        start_date_utc=start_date_utc,
        end_date_utc=end_date_utc,
        product_status=None,
    )

    # 4. Build and filter locker-shop structure
    # Initial structure from current associations
    assoc_structure = revenue_crud.get_locker_shop_structure(db)
    locker_shop_structure = _build_combined_structure(
        assoc_structure,
        combos_data,
        accessible_location_ids,
        filtered_shop_ids,
    )

    # 5. Get names for lockers and shops
    locker_ids = list(locker_shop_structure.keys())
    all_shop_ids = list(
        set([sid for shops in locker_shop_structure.values() for sid in shops])
    )

    locker_name_map, shop_name_map = revenue_crud.get_locker_and_shop_names(
        db, locker_ids, all_shop_ids
    )

    # 6. Initialize and populate metrics
    grouped_by_locker = _initialize_metrics_structure(
        locker_shop_structure, locker_name_map, shop_name_map
    )

    # Calculate revenue multiplier based on user role
    if user.role == "owner_locker":
        revenue_multiplier = LOCKER_OWNER_REVENUE_PERCENTAGE
    else:  # admin or owner_shop
        revenue_multiplier = ADMIN_REVENUE_PERCENTAGE

    combo_ids = list(combos_data.keys())
    combos = admin_sales_crud.get_combos_by_ids(db, combo_ids)
    orders = admin_sales_crud.get_orders_by_combo_ids(
        db, combo_ids, status=ORDER_STATUS_PICKED_UP
    )

    _populate_metrics_from_combos(
        grouped_by_locker, combos_data, combos, orders, revenue_multiplier
    )

    # 7. Convert to sorted rows
    rows = _convert_to_sorted_rows(grouped_by_locker, locker_name_map, shop_name_map)

    # 8. Calculate totals
    totals = {
        "total_sold": sum(r["total_sold"] for r in rows),
        "sold_donated": sum(r["sold_donated"] for r in rows),
        "sold_non_donated": sum(r["sold_non_donated"] for r in rows),
        "unsold": sum(r["unsold"] for r in rows),
        "total_revenue": sum(r["total_revenue"] for r in rows),
    }

    # 9. Generate CSV content
    csv_content = _generate_csv_content(rows, totals, start_date, end_date)
    filename = revenue_utils.generate_csv_filename(start_date, end_date)

    # Add UTF-8 BOM for Excel compatibility with Japanese characters
    csv_content_with_bom = "\ufeff" + csv_content

    return csv_content_with_bom, filename


def _get_accessible_shop_ids(
    db: Session,
    accessible_location_ids: List[str],
    shop_ids: Optional[List[str]] = None,
) -> Tuple[List[str], set]:
    """
    Get accessible shop IDs from shop_locker_associations.

    Args:
        db: Database session
        shop_ids: Optional list of shop IDs to filter

    Returns:
        List of filtered shop IDs
    """
    accessible_shop_ids = set(
        get_shop_ids_by_order_locations(db, accessible_location_ids)
    )

    if shop_ids:
        # Return intersection of requested and accessible
        filtered_shop_ids = [sid for sid in shop_ids if sid in accessible_shop_ids]
        # Check for invalid shop_ids
        invalid = set(shop_ids) - accessible_shop_ids
        return filtered_shop_ids, invalid

    return list(accessible_shop_ids), set()


def _generate_csv_content(
    rows: List[Dict],
    totals: Dict,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> str:
    """Generate CSV content with proper formatting."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Format date range
    date_range_str = ""
    if start_date and end_date:
        start_str = revenue_utils.format_japanese_date(start_date)
        end_str = revenue_utils.format_japanese_date(end_date)
        date_range_str = f"{start_str} ～ {end_str}"

    # Header row 1: Date range
    writer.writerow(["統計期間", date_range_str, "", "", "", ""])
    writer.writerow(["", "", "", "", "", ""])  # Empty row

    # Header row 2: Column names
    writer.writerow(
        [
            "ロッカー名",
            "店舗名",
            "販売済商品数",
            "寄付商品数",
            "非寄付商品数",
            "総売上 (円)",
        ]
    )

    # Data rows
    for row in rows:
        writer.writerow(
            [
                row["locker_name"],
                row["shop_name"],
                str(row["total_sold"]),
                str(row["sold_donated"]),
                str(row["sold_non_donated"]),
                revenue_utils.format_currency(row["total_revenue"]),
            ]
        )

    # Total row
    writer.writerow(
        [
            "合計",
            "",
            str(totals["total_sold"]),
            str(totals["sold_donated"]),
            str(totals["sold_non_donated"]),
            revenue_utils.format_currency(totals["total_revenue"]),
        ]
    )

    return output.getvalue()
