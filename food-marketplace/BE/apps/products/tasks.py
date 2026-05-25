from apps.core.celery_app import celery_app
from apps.core.logging import logger


@celery_app.task
def sync_combo_to_firebase_task(combo_id: str):
    """Celery task to sync combo to Firebase - only newest per shop."""
    try:
        # Import inside the task to avoid circular import issues
        import apps.devices.models
        import apps.favorites.models
        import apps.lockers.models
        import apps.mynaportal.models  # MynaAuthorizer models
        import apps.orders.models  # Order models
        import apps.products.models
        import apps.purchase.models  # Purchase models
        import apps.reviews.models  # Review models
        from apps.core.database import get_session
        from apps.integrations.firebase.combo_service import FirebaseComboService
        from apps.products.crud import get_combo_by_id

        # Get combo from database
        db = next(get_session())
        try:
            combo = get_combo_by_id(db, combo_id)
            if not combo:
                logger.warning(f"Combo {combo_id} not found for Firebase sync")
                return {"status": "warning", "message": f"Combo {combo_id} not found"}

            # Sync to Firebase (will only sync if this is the newest combo for the shop)
            firebase_service = FirebaseComboService()
            success = firebase_service.sync_combo(combo)

            if success:
                logger.info(
                    f"Successfully processed combo {combo_id} for Firebase sync"
                )
                return {
                    "status": "success",
                    "message": f"Combo {combo_id} processed for Firebase sync",
                }
            else:
                logger.error(f"Failed to sync combo {combo_id} to Firebase")
                return {
                    "status": "error",
                    "message": f"Failed to sync combo {combo_id} to Firebase",
                }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in sync_combo_to_firebase_task for combo {combo_id}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def delete_shop_combo_from_firebase_task(shop_id: str):
    """Celery task to delete shop combo record from Firebase."""
    try:
        # Import inside the task to avoid circular import issues
        import apps.devices.models
        import apps.favorites.models
        import apps.lockers.models
        import apps.mynaportal.models  # MynaAuthorizer models
        import apps.orders.models  # Order models
        import apps.products.models
        import apps.purchase.models  # Purchase models
        import apps.reviews.models  # Review models
        from apps.integrations.firebase.combo_service import FirebaseComboService

        firebase_service = FirebaseComboService()
        success = firebase_service.delete_combo_for_shop(shop_id)

        if success:
            logger.info(
                f"Successfully deleted combo record for shop {shop_id} from Firebase"
            )
            return {
                "status": "success",
                "message": f"Combo record for shop {shop_id} deleted from Firebase",
            }
        else:
            logger.error(
                f"Failed to delete combo record for shop {shop_id} from Firebase"
            )
            return {
                "status": "error",
                "message": f"Failed to delete combo record for shop {shop_id} from Firebase",
            }

    except Exception as e:
        logger.error(
            f"Error in delete_shop_combo_from_firebase_task for shop {shop_id}: {e}"
        )
        return {"status": "error", "message": str(e)}


@celery_app.task
def sync_shop_latest_combo_to_firebase_task(shop_id: str):
    """Celery task to sync the latest combo for a shop to Firebase."""
    try:
        # Import inside the task to avoid circular import issues
        import apps.devices.models
        import apps.favorites.models
        import apps.lockers.models
        import apps.mynaportal.models  # MynaAuthorizer models
        import apps.orders.models  # Order models
        import apps.products.models
        import apps.purchase.models  # Purchase models
        import apps.reviews.models  # Review models
        from apps.integrations.firebase.combo_service import FirebaseComboService

        firebase_service = FirebaseComboService()
        success = firebase_service.sync_shop_latest_combo(shop_id)

        if success:
            logger.info(
                f"Successfully synced latest combo for shop {shop_id} to Firebase"
            )
            return {
                "status": "success",
                "message": f"Latest combo for shop {shop_id} synced to Firebase",
            }
        else:
            logger.error(f"Failed to sync latest combo for shop {shop_id} to Firebase")
            return {
                "status": "error",
                "message": f"Failed to sync latest combo for shop {shop_id}",
            }

    except Exception as e:
        logger.error(
            f"Error in sync_shop_latest_combo_to_firebase_task for shop {shop_id}: {e}"
        )
        return {"status": "error", "message": str(e)}
