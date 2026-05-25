"""
Test to verify that review creation sends notification to shop
This test helps identify if notifications are being sent when they shouldn't be
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from sqlmodel import Session, create_engine

from apps.reviews.models.reviews import Review
from apps.reviews.schemas import ReviewCreate
from apps.reviews.services import create_review_service


def create_test_db_session():
    """Create a test database session"""
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_review_notification.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
    )

    # Create tables
    from apps.reviews.models.reviews import Review

    Review.metadata.create_all(bind=engine)

    return Session(engine)


def test_review_notification_is_sent():
    """Test that notification IS being sent when review is created (current behavior)"""
    print("\n" + "=" * 80)
    print("Testing: Review notification SHOULD be sent (current behavior)")
    print("=" * 80)

    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    sample_shop_id = str(uuid4())
    sample_combo_id = str(uuid4())

    try:
        # Mock the Celery task and shop crud function
        with patch(
            "apps.reviews.services.send_user_review.delay"
        ) as mock_send_notification, patch(
            "apps.shops.crud.get_shop_with_users"
        ) as mock_get_shop:

            # Setup mock shop with users
            mock_shop = MagicMock()
            mock_user1 = MagicMock()
            mock_user1.id = str(uuid4())
            mock_user2 = MagicMock()
            mock_user2.id = str(uuid4())

            mock_shop.get_all_shop_users.return_value = [mock_user1, mock_user2]
            mock_get_shop.return_value = mock_shop

            # Mock crud functions
            with patch(
                "apps.reviews.services.crud.create_review"
            ) as mock_create, patch(
                "apps.reviews.services.crud.get_review_with_relationships"
            ) as mock_get:

                # Create a review object to return
                review = Review(
                    id=str(uuid4()),
                    rating=5,
                    comment="Great service!",
                    user_id=sample_user_id,
                    shop_id=sample_shop_id,
                    combo_id=sample_combo_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                mock_create.return_value = review
                mock_get.return_value = review

                # Create review
                review_data = ReviewCreate(
                    rating=5,
                    comment="Great service!",
                    shop_id=sample_shop_id,
                    combo_id=sample_combo_id,
                )

                create_review_service(review_data, sample_user_id, db_session)

                # Verify notification was called
                print(f"\n📊 Test Results:")
                print(f"   ✓ Review created successfully")
                print(f"   ✓ get_shop_with_users was called: {mock_get_shop.called}")
                print(
                    f"   ✓ send_user_review (notification) was called: {mock_send_notification.called}"
                )

                if mock_send_notification.called:
                    call_args = mock_send_notification.call_args
                    print(f"\n📤 Notification Details:")
                    print(f"   Combo ID: {call_args[1]['combo_id']}")
                    print(f"   User IDs: {call_args[1]['user_ids']}")
                    print(f"   Review ID: {call_args[1]['new_review_id']}")
                    print(f"   Number of recipients: {len(call_args[1]['user_ids'])}")

                # Assert that notification WAS sent
                assert (
                    mock_send_notification.called
                ), "❌ ISSUE: Notification was NOT sent!"
                assert mock_get_shop.called, "❌ Shop users were NOT fetched!"

                print(f"\n✅ CONFIRMED: Notifications ARE being sent to shop users")
                print(
                    f"   This is the current behavior - review notifications are active"
                )

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise
    finally:
        db_session.close()
        print("=" * 80 + "\n")


def test_review_without_shop_no_notification():
    """Test that notification is NOT sent when review has no shop_id"""
    print("\n" + "=" * 80)
    print("Testing: No notification when review has no shop_id")
    print("=" * 80)

    db_session = create_test_db_session()
    sample_user_id = str(uuid4())

    try:
        with patch(
            "apps.reviews.services.send_user_review"
        ) as mock_send_notification, patch(
            "apps.reviews.services.get_shop_with_users"
        ) as mock_get_shop:

            # Mock crud functions
            with patch(
                "apps.reviews.services.crud.create_review"
            ) as mock_create, patch(
                "apps.reviews.services.crud.get_review_with_relationships"
            ) as mock_get:

                # Create a review WITHOUT shop_id
                review = Review(
                    id=str(uuid4()),
                    rating=5,
                    comment="Great service!",
                    user_id=sample_user_id,
                    shop_id=None,  # No shop_id
                    combo_id=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                mock_create.return_value = review
                mock_get.return_value = review

                # Create review without shop
                review_data = ReviewCreate(rating=5, comment="Great service!")

                create_review_service(review_data, sample_user_id, db_session)

                # Verify notification was NOT called
                print(f"\n📊 Test Results:")
                print(f"   ✓ Review created successfully")
                print(f"   ✓ Review has no shop_id: {review.shop_id is None}")
                print(f"   ✓ get_shop_with_users was called: {mock_get_shop.called}")
                print(
                    f"   ✓ send_user_review (notification) was called: {mock_send_notification.called}"
                )

                # Assert that notification was NOT sent
                assert (
                    not mock_send_notification.called
                ), "❌ Notification should NOT be sent when shop_id is missing!"
                assert (
                    not mock_get_shop.called
                ), "❌ Shop should NOT be fetched when shop_id is missing!"

                print(f"\n✅ CONFIRMED: No notification sent when shop_id is None")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise
    finally:
        db_session.close()
        print("=" * 80 + "\n")


def test_review_without_combo_no_notification():
    """Test that notification is NOT sent when review has no combo_id"""
    print("\n" + "=" * 80)
    print("Testing: No notification when review has no combo_id")
    print("=" * 80)

    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    sample_shop_id = str(uuid4())

    try:
        with patch(
            "apps.reviews.services.send_user_review.delay"
        ) as mock_send_notification, patch(
            "apps.shops.crud.get_shop_with_users"
        ) as mock_get_shop:

            # Mock crud functions
            with patch(
                "apps.reviews.services.crud.create_review"
            ) as mock_create, patch(
                "apps.reviews.services.crud.get_review_with_relationships"
            ) as mock_get:

                # Create a review with shop_id but WITHOUT combo_id
                review = Review(
                    id=str(uuid4()),
                    rating=5,
                    comment="Great service!",
                    user_id=sample_user_id,
                    shop_id=sample_shop_id,
                    combo_id=None,  # No combo_id
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                mock_create.return_value = review
                mock_get.return_value = review

                # Create review with shop but no combo
                review_data = ReviewCreate(
                    rating=5, comment="Great service!", shop_id=sample_shop_id
                )

                create_review_service(review_data, sample_user_id, db_session)

                # Verify notification was NOT called
                print(f"\n📊 Test Results:")
                print(f"   ✓ Review created successfully")
                print(f"   ✓ Review has shop_id: {review.shop_id is not None}")
                print(f"   ✓ Review has no combo_id: {review.combo_id is None}")
                print(f"   ✓ get_shop_with_users was called: {mock_get_shop.called}")
                print(
                    f"   ✓ send_user_review (notification) was called: {mock_send_notification.called}"
                )

                # Assert that notification was NOT sent
                assert (
                    not mock_send_notification.called
                ), "❌ Notification should NOT be sent when combo_id is missing!"

                print(f"\n✅ CONFIRMED: No notification sent when combo_id is None")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise
    finally:
        db_session.close()
        print("=" * 80 + "\n")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "=" * 80)
    print("🧪 REVIEW NOTIFICATION TEST SUITE")
    print("=" * 80)
    print("Purpose: Verify when review notifications are sent to shops")
    print("=" * 80)

    test_functions = [
        test_review_notification_is_sent,
        test_review_without_shop_no_notification,
        test_review_without_combo_no_notification,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ FAILED: {test_func.__name__}")
            print(f"   Error: {e}\n")

    print("\n" + "=" * 80)
    print(f"📊 FINAL RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        print("\n📌 CURRENT BEHAVIOR:")
        print("   • Notifications ARE sent when review has both shop_id and combo_id")
        print("   • Notifications are NOT sent when shop_id or combo_id is missing")
        print("\n💡 TO DISABLE ALL REVIEW NOTIFICATIONS:")
        print("   Comment out the notification code in apps/reviews/services.py")
        print("   Lines ~48-60 in create_review_service()")
    else:
        print("\n❌ SOME TESTS FAILED!")

    print("=" * 80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
