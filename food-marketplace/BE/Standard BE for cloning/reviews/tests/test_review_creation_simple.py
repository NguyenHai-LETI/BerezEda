"""
Test cases for successful review creation
Simple test cases without external dependencies
"""

import os
import sys
from datetime import datetime
from uuid import uuid4

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from sqlmodel import Session, create_engine

from apps.reviews.crud import create_review, get_review
from apps.reviews.models.reviews import Review
from apps.reviews.schemas import ReviewCreate

# Import all models to ensure they are registered with SQLModel metadata


def create_test_db_session():
    """Create a test database session"""
    # Use in-memory SQLite for testing with foreign keys disabled
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reviews.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
    )

    # Create only the Review table for testing (without foreign key constraints)
    from apps.reviews.models.reviews import Review

    Review.metadata.create_all(bind=engine)

    return Session(engine)


def test_create_basic_review_success():
    """Test creating a basic review with minimal required fields"""
    print("Testing basic review creation...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())

    try:
        # Arrange
        review_data = ReviewCreate(rating=5, comment="Great experience!")

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            comment=review_data.comment,
            user_id=sample_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.id == review.id, "Review ID should match"
        assert created_review.rating == 5, "Rating should be 5"
        assert created_review.comment == "Great experience!", "Comment should match"
        assert created_review.user_id == sample_user_id, "User ID should match"
        assert created_review.shop_id is None, "Shop ID should be None"
        assert created_review.combo_id is None, "Combo ID should be None"
        assert created_review.order_id is None, "Order ID should be None"
        assert created_review.created_at is not None, "Created at should not be None"
        assert created_review.updated_at is not None, "Updated at should not be None"

        print("✓ Basic review creation test passed")

    except Exception as e:
        print(f"✗ Basic review creation test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_review_with_shop_success():
    """Test creating a review with shop association"""
    print("Testing review creation with shop...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    sample_shop_id = str(uuid4())

    try:
        # Arrange
        review_data = ReviewCreate(
            rating=4, comment="Good shop experience", shop_id=sample_shop_id
        )

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            comment=review_data.comment,
            user_id=sample_user_id,
            shop_id=review_data.shop_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.rating == 4, "Rating should be 4"
        assert created_review.comment == "Good shop experience", "Comment should match"
        assert created_review.user_id == sample_user_id, "User ID should match"
        assert created_review.shop_id == sample_shop_id, "Shop ID should match"
        assert created_review.combo_id is None, "Combo ID should be None"
        assert created_review.order_id is None, "Order ID should be None"

        print("✓ Review creation with shop test passed")

    except Exception as e:
        print(f"✗ Review creation with shop test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_review_with_order_success():
    """Test creating a review with direct order association"""
    print("Testing review creation with order...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    sample_order_id = str(uuid4())

    try:
        # Arrange
        review_data = ReviewCreate(
            rating=5, comment="Excellent order experience", order_id=sample_order_id
        )

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            comment=review_data.comment,
            user_id=sample_user_id,
            order_id=review_data.order_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.rating == 5, "Rating should be 5"
        assert (
            created_review.comment == "Excellent order experience"
        ), "Comment should match"
        assert created_review.user_id == sample_user_id, "User ID should match"
        assert created_review.shop_id is None, "Shop ID should be None"
        assert created_review.combo_id is None, "Combo ID should be None"
        assert created_review.order_id == sample_order_id, "Order ID should match"

        print("✓ Review creation with order test passed")

    except Exception as e:
        print(f"✗ Review creation with order test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_complete_review_success():
    """Test creating a review with all possible associations"""
    print("Testing complete review creation...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    sample_shop_id = str(uuid4())
    sample_combo_id = str(uuid4())
    sample_order_id = str(uuid4())
    sample_locker_unit_id = str(uuid4())

    try:
        # Arrange
        review_data = ReviewCreate(
            rating=4,
            comment="Complete review with all associations",
            shop_id=sample_shop_id,
            combo_id=sample_combo_id,
            order_id=sample_order_id,
            locker_unit_id=sample_locker_unit_id,
        )

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            comment=review_data.comment,
            user_id=sample_user_id,
            shop_id=review_data.shop_id,
            combo_id=review_data.combo_id,
            order_id=review_data.order_id,
            locker_unit_id=review_data.locker_unit_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.rating == 4, "Rating should be 4"
        assert (
            created_review.comment == "Complete review with all associations"
        ), "Comment should match"
        assert created_review.user_id == sample_user_id, "User ID should match"
        assert created_review.shop_id == sample_shop_id, "Shop ID should match"
        assert created_review.combo_id == sample_combo_id, "Combo ID should match"
        assert created_review.order_id == sample_order_id, "Order ID should match"
        assert (
            created_review.locker_unit_id == sample_locker_unit_id
        ), "Locker Unit ID should match"

        print("✓ Complete review creation test passed")

    except Exception as e:
        print(f"✗ Complete review creation test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_review_without_comment_success():
    """Test creating a review without optional comment field"""
    print("Testing review creation without comment...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())

    try:
        # Arrange
        review_data = ReviewCreate(rating=5)

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            user_id=sample_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.rating == 5, "Rating should be 5"
        assert created_review.comment is None, "Comment should be None"
        assert created_review.user_id == sample_user_id, "User ID should match"

        print("✓ Review creation without comment test passed")

    except Exception as e:
        print(f"✗ Review creation without comment test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_review_with_different_ratings_success():
    """Test creating reviews with different valid rating values"""
    print("Testing review creation with different ratings...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())
    ratings_to_test = [1, 2, 3, 4, 5]

    try:
        for rating in ratings_to_test:
            # Arrange
            review_data = ReviewCreate(
                rating=rating, comment=f"Review with rating {rating}"
            )

            review = Review(
                id=str(uuid4()),
                rating=review_data.rating,
                comment=review_data.comment,
                user_id=sample_user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Act
            created_review = create_review(db_session, review)

            # Assert
            assert (
                created_review is not None
            ), f"Created review with rating {rating} should not be None"
            assert created_review.rating == rating, f"Rating should be {rating}"
            assert (
                created_review.comment == f"Review with rating {rating}"
            ), "Comment should match"
            assert created_review.user_id == sample_user_id, "User ID should match"

        print("✓ Review creation with different ratings test passed")

    except Exception as e:
        print(f"✗ Review creation with different ratings test failed: {e}")
        raise
    finally:
        db_session.close()


def test_get_created_review_success():
    """Test retrieving a created review by ID"""
    print("Testing review retrieval...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())

    try:
        # Arrange - Create a review first
        review_id = str(uuid4())
        review = Review(
            id=review_id,
            rating=4,
            comment="Test review for retrieval",
            user_id=sample_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        create_review(db_session, review)

        # Act
        retrieved_review = get_review(db_session, review_id)

        # Assert
        assert retrieved_review is not None, "Retrieved review should not be None"
        assert retrieved_review.id == review_id, "Review ID should match"
        assert retrieved_review.rating == 4, "Rating should be 4"
        assert (
            retrieved_review.comment == "Test review for retrieval"
        ), "Comment should match"
        assert retrieved_review.user_id == sample_user_id, "User ID should match"

        print("✓ Review retrieval test passed")

    except Exception as e:
        print(f"✗ Review retrieval test failed: {e}")
        raise
    finally:
        db_session.close()


def test_create_review_with_long_comment_success():
    """Test creating a review with a long comment"""
    print("Testing review creation with long comment...")

    # Setup
    db_session = create_test_db_session()
    sample_user_id = str(uuid4())

    try:
        # Arrange
        long_comment = (
            "This is a very long comment that exceeds typical short review length. "
            * 10
        )
        review_data = ReviewCreate(rating=4, comment=long_comment)

        review = Review(
            id=str(uuid4()),
            rating=review_data.rating,
            comment=review_data.comment,
            user_id=sample_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        created_review = create_review(db_session, review)

        # Assert
        assert created_review is not None, "Created review should not be None"
        assert created_review.rating == 4, "Rating should be 4"
        assert created_review.comment == long_comment, "Comment should match"
        assert (
            created_review.comment is not None and len(created_review.comment) > 500
        ), "Comment should be long"
        assert created_review.user_id == sample_user_id, "User ID should match"

        print("✓ Review creation with long comment test passed")

    except Exception as e:
        print(f"✗ Review creation with long comment test failed: {e}")
        raise
    finally:
        db_session.close()


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("Running Review Creation Success Tests")
    print("=" * 60)

    test_functions = [
        test_create_basic_review_success,
        test_create_review_with_shop_success,
        test_create_review_with_order_success,
        test_create_complete_review_success,
        test_create_review_without_comment_success,
        test_create_review_with_different_ratings_success,
        test_get_created_review_success,
        test_create_review_with_long_comment_success,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAILED: {test_func.__name__} - {e}")

    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("All tests passed! ✓")
        exit(0)
    else:
        print("Some tests failed! ✗")
        exit(1)
