from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from apps.core.celery_app import celery_app
from apps.core.database import engine
from apps.core.logging import logger
from apps.integrations.firebase.shop_service import FirebaseShopService
from apps.shops import crud

SessionLocal = sessionmaker(bind=engine, class_=Session)


@celery_app.task
def sync_shop_to_firebase_task(shop_id: str):
    """Sync shop data to Firebase asynchronously."""
    try:
        with SessionLocal() as db:
            # Get shop with eager loading to avoid session issues
            shop = crud.get_shop(db, shop_id)
            if not shop:
                logger.error(f"Shop {shop_id} not found for Firebase sync")
                return False

            # Get analytics data
            from apps.shops.analytics import get_shop_analytics_for_firebase

            analytics = get_shop_analytics_for_firebase(db, shop_id)

            # Convert shop to dictionary while session is still active
            shop_data = {
                "id": str(shop.id),
                "code": shop.code,
                "name": shop.name,
                "avg_rating": float(shop.avg_rating) if shop.avg_rating else 0.0,
                "total_reviews": int(shop.total_reviews) if shop.total_reviews else 0,
                "is_active": shop.is_active,
                "created_at": shop.created_at.isoformat() if shop.created_at else None,
                "updated_at": shop.updated_at.isoformat() if shop.updated_at else None,
            }

            # Add analytics data
            shop_data.update(analytics)

        # Sync to Firebase using the extracted data
        firebase_service = FirebaseShopService()
        result = firebase_service.sync_shop_data_to_firebase(shop_data)

        if result:
            logger.info(
                f"Successfully synced shop {shop_id} to Firebase with analytics"
            )
        else:
            logger.error(f"Failed to sync shop {shop_id} to Firebase")

        return result

    except Exception as e:
        logger.error(f"Error in sync_shop_to_firebase_task for shop {shop_id}: {e}")
        return False


@celery_app.task
def delete_shop_from_firebase_task(shop_id: str):
    """Delete shop from Firebase asynchronously."""
    try:
        firebase_service = FirebaseShopService()
        result = firebase_service.delete_shop_from_firebase(shop_id)

        if result:
            logger.info(f"Successfully deleted shop {shop_id} from Firebase")
        else:
            logger.error(f"Failed to delete shop {shop_id} from Firebase")

        return result

    except Exception as e:
        logger.error(f"Error in delete_shop_from_firebase_task for shop {shop_id}: {e}")
        return False


@celery_app.task
def sync_shop_analytics_to_firebase_task(shop_id: str):
    """Sync only shop analytics to Firebase asynchronously."""
    try:
        with SessionLocal() as db:
            # Get analytics data
            from apps.shops.analytics import get_shop_analytics_for_firebase

            analytics = get_shop_analytics_for_firebase(db, shop_id)

        # Update only analytics fields in Firebase
        firebase_service = FirebaseShopService()
        result = firebase_service.update_shop_in_firebase(shop_id, analytics)

        if result:
            logger.info(f"Successfully synced analytics for shop {shop_id} to Firebase")
        else:
            logger.error(f"Failed to sync analytics for shop {shop_id} to Firebase")

        return result

    except Exception as e:
        logger.error(f"Error syncing analytics for shop {shop_id} to Firebase: {e}")
        return False


@celery_app.task
def update_shop_field_to_firebase_task(shop_id: str, update_data: dict):
    """Update specific shop fields in Firebase."""
    try:
        firebase_service = FirebaseShopService()
        result = firebase_service.update_shop_in_firebase(shop_id, update_data)

        if result:
            logger.info(
                f"Successfully updated shop {shop_id} fields: {list(update_data.keys())}"
            )
        else:
            logger.error(f"Failed to update shop {shop_id} fields to Firebase")

        return result

    except Exception as e:
        logger.error(f"Error updating shop {shop_id} fields to Firebase: {e}")
        return False
