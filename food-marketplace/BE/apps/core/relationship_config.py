"""
Configure SQLModel relationships after all models are loaded.
This prevents circular import issues by deferring relationship resolution.
"""


def configure_model_relationships():
    """Configure relationships between models after all are imported."""
    from sqlalchemy.orm import configure_mappers

    try:
        # Import all model classes to ensure they're available
        import apps.auth.models  # noqa
        import apps.devices.models  # noqa
        import apps.favorites.models  # noqa
        import apps.lockers.models  # noqa
        import apps.mynaportal.models  # noqa
        import apps.notifications.models  # noqa
        import apps.orders.models  # noqa
        import apps.products.models  # noqa
        import apps.purchase.models  # noqa
        import apps.reviews.models  # noqa
        import apps.shops.models  # noqa
        import apps.users.models  # noqa

        # Force SQLAlchemy to resolve all relationships
        configure_mappers()

        return True
    except Exception as e:
        print(f"Error configuring relationships: {e}")
        return False
