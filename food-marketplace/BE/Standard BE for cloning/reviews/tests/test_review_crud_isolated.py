#!/usr/bin/env python3
"""
Isolated test cases for review CRUD operations
Tests the core review functionality without complex relationships
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import ClassVar, Optional

from sqlmodel import Field, Session, SQLModel, create_engine


# Define a minimal Review model for testing (without foreign key constraints)
class TestReview(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_reviews"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    rating: int = Field(default=0)
    comment: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = Field()
    shop_id: Optional[str] = Field(default=None)
    combo_id: Optional[str] = Field(default=None)
    order_id: Optional[str] = Field(default=None)
    locker_unit_id: Optional[str] = Field(default=None)


def create_test_database():
    """Create a temporary in-memory database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestReview.metadata.create_all(engine)
    return engine


def test_create_basic_review_success():
    """Test creating a basic review with minimum required fields"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review data
        review = TestReview(
            rating=5, comment="Great service!", user_id=str(uuid.uuid4())
        )

        # Save review
        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.id is not None
        assert review.rating == 5
        assert review.comment == "Great service!"
        assert review.user_id is not None
        assert review.shop_id is None
        assert review.combo_id is None
        assert review.order_id is None
        assert review.created_at is not None
        assert review.updated_at is not None

        print("✓ Basic review creation successful")


def test_create_review_with_all_fields_success():
    """Test creating a review with all fields populated"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review with all fields
        review = TestReview(
            rating=4,
            comment="Good experience with all details",
            user_id=str(uuid.uuid4()),
            shop_id=str(uuid.uuid4()),
            combo_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            locker_unit_id=str(uuid.uuid4()),
        )

        # Save review
        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.id is not None
        assert review.rating == 4
        assert review.comment == "Good experience with all details"
        assert review.user_id is not None
        assert review.shop_id is not None
        assert review.combo_id is not None
        assert review.order_id is not None
        assert review.locker_unit_id is not None

        print("✓ Complete review creation successful")


def test_create_review_without_comment_success():
    """Test creating a review without optional comment"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review without comment
        review = TestReview(
            rating=3, user_id=str(uuid.uuid4()), shop_id=str(uuid.uuid4())
        )

        # Save review
        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.rating == 3
        assert review.comment is None
        assert review.shop_id is not None

        print("✓ Review without comment creation successful")


def test_create_multiple_reviews_success():
    """Test creating multiple reviews with different ratings"""
    engine = create_test_database()

    with Session(engine) as db:
        ratings = [1, 2, 3, 4, 5]
        user_id = str(uuid.uuid4())

        for rating in ratings:
            review = TestReview(
                rating=rating, comment=f"Rating {rating} stars", user_id=user_id
            )

            db.add(review)
            db.commit()
            db.refresh(review)

            assert review.rating == rating
            assert review.comment == f"Rating {rating} stars"

        print("✓ Multiple reviews creation successful")


def test_retrieve_created_review_success():
    """Test retrieving a created review"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create and save review
        review = TestReview(
            rating=5, comment="Test retrieval", user_id=str(uuid.uuid4())
        )

        db.add(review)
        db.commit()
        db.refresh(review)
        review_id = review.id

        # Retrieve the review
        retrieved_review = db.get(TestReview, review_id)

        # Assertions
        assert retrieved_review is not None
        assert retrieved_review.id == review_id
        assert retrieved_review.rating == 5
        assert retrieved_review.comment == "Test retrieval"

        print("✓ Review retrieval successful")


def test_update_review_success():
    """Test updating an existing review"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review
        review = TestReview(
            rating=3, comment="Initial comment", user_id=str(uuid.uuid4())
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        # Update review
        review.rating = 5
        review.comment = "Updated comment"
        review.updated_at = datetime.now(timezone.utc)

        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.rating == 5
        assert review.comment == "Updated comment"

        print("✓ Review update successful")


def test_create_review_with_long_comment_success():
    """Test creating a review with a long comment"""
    engine = create_test_database()

    with Session(engine) as db:
        long_comment = "This is a very long comment. " * 50  # 1500+ characters

        review = TestReview(rating=4, comment=long_comment, user_id=str(uuid.uuid4()))

        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.rating == 4
        assert review.comment == long_comment
        assert review.comment is not None and len(review.comment) > 1000

        print("✓ Review with long comment creation successful")


def test_review_timestamps_success():
    """Test that review timestamps are properly set"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review
        before_creation = datetime.now(timezone.utc)

        review = TestReview(
            rating=5, comment="Timestamp test", user_id=str(uuid.uuid4())
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        after_creation = datetime.now(timezone.utc)

        # Convert timestamps to UTC if they're naive
        created_at = review.created_at
        updated_at = review.updated_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        # Assertions
        assert review.created_at is not None
        assert review.updated_at is not None
        assert before_creation <= created_at <= after_creation
        assert before_creation <= updated_at <= after_creation

        print("✓ Review timestamps validation successful")


def test_create_review_with_locker_unit_success():
    """Test creating a review with locker unit association"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review with locker unit
        review = TestReview(
            rating=4,
            comment="Great locker experience!",
            user_id=str(uuid.uuid4()),
            shop_id=str(uuid.uuid4()),
            combo_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            locker_unit_id=str(uuid.uuid4()),
        )

        # Save review
        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.id is not None
        assert review.rating == 4
        assert review.comment == "Great locker experience!"
        assert review.locker_unit_id is not None
        assert review.shop_id is not None
        assert review.combo_id is not None
        assert review.order_id is not None

        print("✓ Review with locker unit creation successful")


def test_create_review_all_relationships_success():
    """Test creating a review with all relationship fields"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create review with all relationships
        user_id = str(uuid.uuid4())
        shop_id = str(uuid.uuid4())
        combo_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        locker_unit_id = str(uuid.uuid4())

        review = TestReview(
            rating=5,
            comment="Perfect experience with all details!",
            user_id=user_id,
            shop_id=shop_id,
            combo_id=combo_id,
            order_id=order_id,
            locker_unit_id=locker_unit_id,
        )

        # Save review
        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.rating == 5
        assert review.comment == "Perfect experience with all details!"
        assert review.user_id == user_id
        assert review.shop_id == shop_id
        assert review.combo_id == combo_id
        assert review.order_id == order_id
        assert review.locker_unit_id == locker_unit_id

        print("✓ Review with all relationships creation successful")


def test_update_review_locker_unit_success():
    """Test updating a review's locker unit"""
    engine = create_test_database()

    with Session(engine) as db:
        # Create initial review
        review = TestReview(
            rating=3,
            comment="Initial review",
            user_id=str(uuid.uuid4()),
            shop_id=str(uuid.uuid4()),
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        # Verify no locker unit initially
        assert review.locker_unit_id is None

        # Update with locker unit
        new_locker_unit_id = str(uuid.uuid4())
        review.locker_unit_id = new_locker_unit_id
        review.rating = 5
        review.comment = "Updated with locker info!"
        review.updated_at = datetime.now(timezone.utc)

        db.add(review)
        db.commit()
        db.refresh(review)

        # Assertions
        assert review.locker_unit_id == new_locker_unit_id
        assert review.rating == 5
        assert review.comment == "Updated with locker info!"

        print("✓ Review locker unit update successful")


def test_create_review_partial_relationships_success():
    """Test creating reviews with different combinations of relationships"""
    engine = create_test_database()

    with Session(engine) as db:
        test_cases = [
            # Case 1: User + Shop + Locker Unit (no combo/order)
            {
                "rating": 4,
                "comment": "Shop and locker only",
                "user_id": str(uuid.uuid4()),
                "shop_id": str(uuid.uuid4()),
                "locker_unit_id": str(uuid.uuid4()),
                "expected_fields": ["user_id", "shop_id", "locker_unit_id"],
            },
            # Case 2: User + Combo + Order (no shop/locker)
            {
                "rating": 3,
                "comment": "Combo and order only",
                "user_id": str(uuid.uuid4()),
                "combo_id": str(uuid.uuid4()),
                "order_id": str(uuid.uuid4()),
                "expected_fields": ["user_id", "combo_id", "order_id"],
            },
            # Case 3: User + Locker Unit only
            {
                "rating": 5,
                "comment": "Just locker unit",
                "user_id": str(uuid.uuid4()),
                "locker_unit_id": str(uuid.uuid4()),
                "expected_fields": ["user_id", "locker_unit_id"],
            },
        ]

        for i, case in enumerate(test_cases):
            # Create review with specific fields
            review_data = {
                k: v for k, v in case.items() if k not in ["expected_fields"]
            }
            review = TestReview(**review_data)

            db.add(review)
            db.commit()
            db.refresh(review)

            # Verify expected fields are set
            for field in case["expected_fields"]:
                assert (
                    getattr(review, field) is not None
                ), f"Case {i+1}: {field} should not be None"

            # Verify optional fields are None when not set
            optional_fields = ["shop_id", "combo_id", "order_id", "locker_unit_id"]
            for field in optional_fields:
                if field not in case["expected_fields"]:
                    assert (
                        getattr(review, field) is None
                    ), f"Case {i+1}: {field} should be None"

        print("✓ Review partial relationships creation successful")


def run_all_tests():
    """Run all test functions"""
    test_functions = [
        test_create_basic_review_success,
        test_create_review_with_all_fields_success,
        test_create_review_without_comment_success,
        test_create_multiple_reviews_success,
        test_retrieve_created_review_success,
        test_update_review_success,
        test_create_review_with_long_comment_success,
        test_review_timestamps_success,
        test_create_review_with_locker_unit_success,
        test_create_review_all_relationships_success,
        test_update_review_locker_unit_success,
        test_create_review_partial_relationships_success,
    ]

    print("=" * 60)
    print("Running Isolated Review CRUD Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            print(
                f"Testing {test_func.__name__.replace('test_', '').replace('_', ' ')}..."
            )
            test_func()
            passed += 1
        except Exception as e:
            print(f"FAILED: {test_func.__name__} - {str(e)}")
            failed += 1
            # Print full traceback for debugging
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
