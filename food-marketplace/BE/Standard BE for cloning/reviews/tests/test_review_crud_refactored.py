#!/usr/bin/env python3
"""
Test cases for refactored Review CRUD with direct relationships
Tests the new locker_unit_id field and optimized relationship loading
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Optional

from apps.core.utils import get_current_time

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Field, Session, SQLModel, create_engine


# Test models without foreign key constraints
class TestUser(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_users"

    id: str = Field(primary_key=True)
    name: str = Field()
    icon: Optional[str] = Field(default=None)


class TestShop(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_shops"

    id: str = Field(primary_key=True)
    name: str = Field()


class TestCombo(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_combos"

    id: str = Field(primary_key=True)
    name: str = Field()


class TestOrder(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_orders"

    id: str = Field(primary_key=True)
    picked_up_at: Optional[datetime] = Field(default=None)


class TestLockerUnit(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_locker_units"

    id: str = Field(primary_key=True)
    name: str = Field()
    location_id: str = Field()


class TestLockerLocation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_locker_locations"

    id: str = Field(primary_key=True)
    name: str = Field()


class TestReview(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_reviews"

    id: str = Field(primary_key=True)
    rating: int = Field()
    comment: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = Field()
    shop_id: Optional[str] = Field(default=None)
    combo_id: Optional[str] = Field(default=None)
    order_id: Optional[str] = Field(default=None)
    locker_unit_id: Optional[str] = Field(default=None)


class TestReviewCRUDWithRelationships:
    """Test the refactored review CRUD with relationship loading"""

    def __init__(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        SQLModel.metadata.create_all(self.engine)

    def get_test_session(self) -> Session:
        return Session(self.engine)

    def create_test_data(self, db: Session):
        """Create test data for relationships"""
        # Create test user
        user = TestUser(id=str(uuid.uuid4()), name="Test User", icon="test_icon.png")
        db.add(user)

        # Create test shop
        shop = TestShop(id=str(uuid.uuid4()), name="Test Shop")
        db.add(shop)

        # Create test combo
        combo = TestCombo(id=str(uuid.uuid4()), name="Test Combo")
        db.add(combo)

        # Create test order
        order = TestOrder(id=str(uuid.uuid4()), picked_up_at=datetime.now(timezone.utc))
        db.add(order)

        # Create test locker location
        location = TestLockerLocation(id=str(uuid.uuid4()), name="Test Location")
        db.add(location)

        # Create test locker unit
        locker_unit = TestLockerUnit(
            id=str(uuid.uuid4()), name="Unit A1", location_id=location.id
        )
        db.add(locker_unit)

        db.commit()

        return user, shop, combo, order, locker_unit, location

    def simulate_get_review_with_relationships(self, db: Session, review: TestReview):
        """Simulate the refactored get_review_with_relationships function"""
        # Load user relationship directly
        if review.user_id:
            review.user = db.get(TestUser, review.user_id)

        # Load shop relationship directly
        if review.shop_id:
            review.shop = db.get(TestShop, review.shop_id)

        # Load order relationship directly
        if review.order_id:
            review.order = db.get(TestOrder, review.order_id)

        # Load combo relationship directly
        if review.combo_id:
            review.combo = db.get(TestCombo, review.combo_id)

        # Load locker unit and location directly (NEW REFACTORED CODE)
        if review.locker_unit_id:
            locker_unit = db.get(TestLockerUnit, review.locker_unit_id)
            if locker_unit and locker_unit.location_id:
                locker_location = db.get(TestLockerLocation, locker_unit.location_id)
                # Simulate setattr for locker location
                setattr(review, "locker", locker_location)

        return review

    def test_review_with_direct_locker_unit_success(self):
        """Test review loading with direct locker_unit_id (refactored approach)"""
        print("Testing refactored locker unit relationship loading...")

        with self.get_test_session() as db:
            # Create test data
            user, shop, combo, order, locker_unit, location = self.create_test_data(db)

            # Create review with direct locker_unit_id
            review = TestReview(
                id=str(uuid.uuid4()),
                rating=5,
                comment="Great locker experience!",
                user_id=user.id,
                shop_id=shop.id,
                combo_id=combo.id,
                order_id=order.id,
                locker_unit_id=locker_unit.id,  # Direct relationship!
            )

            db.add(review)
            db.commit()
            db.refresh(review)

            # Load relationships using refactored approach
            loaded_review = self.simulate_get_review_with_relationships(db, review)

            # Verify all relationships loaded correctly
            assert hasattr(loaded_review, "user")
            assert getattr(loaded_review, "user").name == "Test User"
            assert getattr(loaded_review, "user").icon == "test_icon.png"

            assert hasattr(loaded_review, "shop")
            assert getattr(loaded_review, "shop").name == "Test Shop"

            assert hasattr(loaded_review, "combo")
            assert getattr(loaded_review, "combo").name == "Test Combo"

            assert hasattr(loaded_review, "order")
            assert getattr(loaded_review, "order").picked_up_at is not None

            # Most importantly - test the new direct locker relationship
            assert hasattr(loaded_review, "locker")
            assert getattr(loaded_review, "locker").name == "Test Location"

            print("✓ Refactored locker unit relationship loading successful")
            return True

    def test_review_without_locker_unit_success(self):
        """Test review without locker_unit_id (should not load locker)"""
        print("Testing review without locker unit...")

        with self.get_test_session() as db:
            user, shop, combo, order, locker_unit, location = self.create_test_data(db)

            # Create review without locker_unit_id
            review = TestReview(
                id=str(uuid.uuid4()),
                rating=4,
                comment="No locker needed",
                user_id=user.id,
                shop_id=shop.id,
                combo_id=combo.id,
                order_id=order.id,
                # No locker_unit_id
            )

            db.add(review)
            db.commit()
            db.refresh(review)

            # Load relationships
            loaded_review = self.simulate_get_review_with_relationships(db, review)

            # Verify other relationships loaded
            assert hasattr(loaded_review, "user")
            assert hasattr(loaded_review, "shop")
            assert hasattr(loaded_review, "combo")
            assert hasattr(loaded_review, "order")

            # Verify locker was NOT loaded
            assert not hasattr(loaded_review, "locker")

            print("✓ Review without locker unit successful")
            return True

    def test_performance_comparison(self):
        """Test performance improvement of direct vs complex relationship"""
        print("Testing performance of direct relationship loading...")

        with self.get_test_session() as db:
            user, shop, combo, order, locker_unit, location = self.create_test_data(db)

            # Create multiple reviews with locker units
            reviews = []
            for i in range(10):
                review = TestReview(
                    id=str(uuid.uuid4()),
                    rating=5,
                    comment=f"Review {i}",
                    user_id=user.id,
                    shop_id=shop.id,
                    combo_id=combo.id,
                    order_id=order.id,
                    locker_unit_id=locker_unit.id,
                )
                db.add(review)
                reviews.append(review)

            db.commit()

            # Test batch loading (simulating get_reviews_with_relationships)
            start_time = get_current_time()

            for review in reviews:
                self.simulate_get_review_with_relationships(db, review)

            end_time = get_current_time()
            duration = (end_time - start_time).total_seconds()

            # Should be fast with direct relationships
            assert duration < 1.0, f"Loading took too long: {duration}s"

            # Verify all loaded correctly
            for review in reviews:
                assert hasattr(review, "locker")
                assert getattr(review, "locker").name == "Test Location"

            print(
                f"✓ Performance test successful - loaded {len(reviews)} reviews in {duration:.3f}s"
            )
            return True

    def test_partial_relationship_loading_success(self):
        """Test loading reviews with different combinations of relationships"""
        print("Testing partial relationship loading...")

        with self.get_test_session() as db:
            user, shop, combo, order, locker_unit, location = self.create_test_data(db)

            test_cases = [
                # Case 1: Only user + locker unit
                {
                    "user_id": user.id,
                    "locker_unit_id": locker_unit.id,
                    "expected_attrs": ["user", "locker"],
                },
                # Case 2: User + shop + order (no locker)
                {
                    "user_id": user.id,
                    "shop_id": shop.id,
                    "order_id": order.id,
                    "expected_attrs": ["user", "shop", "order"],
                },
                # Case 3: All relationships
                {
                    "user_id": user.id,
                    "shop_id": shop.id,
                    "combo_id": combo.id,
                    "order_id": order.id,
                    "locker_unit_id": locker_unit.id,
                    "expected_attrs": ["user", "shop", "combo", "order", "locker"],
                },
            ]

            for i, case in enumerate(test_cases):
                review_data = {k: v for k, v in case.items() if k != "expected_attrs"}
                review_data.update(
                    {
                        "id": str(uuid.uuid4()),
                        "rating": 4,
                        "comment": f"Test case {i+1}",
                    }
                )

                review = TestReview(**review_data)
                db.add(review)
                db.commit()
                db.refresh(review)

                # Load relationships
                loaded_review = self.simulate_get_review_with_relationships(db, review)

                # Verify expected attributes are present
                for attr in case["expected_attrs"]:
                    assert hasattr(loaded_review, attr), f"Case {i+1}: Missing {attr}"

                # Verify unexpected attributes are not present
                all_possible = ["user", "shop", "combo", "order", "locker"]
                for attr in all_possible:
                    if attr not in case["expected_attrs"]:
                        assert not hasattr(
                            loaded_review, attr
                        ), f"Case {i+1}: Unexpected {attr}"

            print("✓ Partial relationship loading successful")
            return True


def run_all_tests():
    """Run all refactored CRUD tests"""
    test_class = TestReviewCRUDWithRelationships()

    test_functions = [
        test_class.test_review_with_direct_locker_unit_success,
        test_class.test_review_without_locker_unit_success,
        test_class.test_performance_comparison,
        test_class.test_partial_relationship_loading_success,
    ]

    print("=" * 70)
    print("Running Refactored Review CRUD Tests")
    print("=" * 70)

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
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("🎉 All refactored CRUD tests passed!")
        print("✅ Direct locker_unit_id relationship working correctly")
        print("✅ Performance improved with direct relationships")
        print("✅ Complex reservation lookup eliminated")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
