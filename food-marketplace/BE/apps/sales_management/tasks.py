from datetime import datetime, timedelta, timezone

from apps.core.celery_app import celery_app
from apps.core.database import get_session
from apps.sales_management import crud


@celery_app.task(name="sales_management.cleanup_old_reservations")
def cleanup_old_reservations(days_old: int = 7, batch_size: int = 500):
    """
    Clean up old locker reservations that are no longer needed.
    This helps maintain database performance.
    """
    db = next(get_session())
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        # Clean up old reservations
        deleted_count = crud.cleanup_old_reservations(db, cutoff_date, batch_size)

        db.commit()
        return {
            "deleted_reservations": deleted_count,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(name="sales_management.generate_daily_sales_report")
def generate_daily_sales_report(target_date: str | None = None):
    """
    Generate daily sales report for analytics.
    If target_date is not provided, uses yesterday's date.
    """
    db = next(get_session())
    try:
        if target_date:
            report_date = datetime.fromisoformat(target_date).date()
        else:
            report_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        # Generate report data
        report_data = crud.generate_sales_report_data(db, report_date)

        return {
            "report_date": report_date.isoformat(),
            "total_sales": report_data.get("total_sales", 0),
            "total_revenue": report_data.get("total_revenue", 0),
            "total_donations": report_data.get("total_donations", 0),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise e
    finally:
        db.close()
