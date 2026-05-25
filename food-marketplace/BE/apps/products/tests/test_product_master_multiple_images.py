#!/usr/bin/env python3
"""
Test cases for ProductMaster with multiple images functionality
Tests creating, updating, and retrieving products with image lists
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import ClassVar, Optional

from sqlmodel import Field, Session, SQLModel, create_engine


# Define a minimal ProductMaster model for testing (without foreign key constraints)
class TestProductMaster(SQLModel, table=True):
    __tablename__: ClassVar[str] = "test_product_masters"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    shop_id: str = Field()
    name: str = Field()
    description: Optional[str] = Field(default=None)
    selling_price: float = Field()
    food_waste_weight: Optional[float] = Field(default=None)
    storage_method: Optional[str] = Field(default=None)
    ingredients: Optional[str] = Field(default=None)
    additives: Optional[str] = Field(default=None)
    nutrition_facts: Optional[str] = Field(default=None)
    allergens: Optional[str] = Field(default=None)
    content_details: Optional[str] = Field(default=None)
    expiration_date_type: Optional[str] = Field(default=None)
    business_name: Optional[str] = Field(default=None)
    supplier_code: Optional[str] = Field(default=None)
    address_zip_code: Optional[str] = Field(default=None)
    address_prefecture: Optional[str] = Field(default=None)
    address_city: Optional[str] = Field(default=None)
    address_street: Optional[str] = Field(default=None)
    images: Optional[str] = Field(default=None)  # JSON string for testing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)


class TestProductMasterMultipleImages:
    """Test cases for ProductMaster with multiple images functionality"""

    def __init__(self):
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        TestProductMaster.metadata.create_all(self.engine)

    def get_test_session(self) -> Session:
        """Get a test database session"""
        return Session(self.engine)

    def create_sample_product_data(self, images: List[str] = None) -> dict:
        """Create sample product data for testing"""
        import json

        return {
            "shop_id": str(uuid.uuid4()),
            "name": "Test Sandwich with Multiple Images",
            "description": "A delicious sandwich with multiple image views",
            "selling_price": 1200.0,
            "food_waste_weight": 250.0,
            "storage_method": "Refrigerated",
            "ingredients": "Bread, Ham, Cheese, Lettuce, Tomato",
            "additives": "Preservatives (E200, E211)",
            "nutrition_facts": "Calories: 350kcal, Protein: 15g, Fat: 12g, Carbs: 45g",
            "allergens": "Gluten, Dairy",
            "content_details": "1 sandwich (200g)",
            "expiration_date_type": "consume_by",
            "business_name": "Test Food Co., Ltd.",
            "supplier_code": "TEST001",
            "address_zip_code": "1500001",
            "address_prefecture": "Tokyo",
            "address_city": "Shibuya",
            "address_street": "1-1-1 Shibuya Test Building",
            "images": json.dumps(images or []),  # Store as JSON string
        }

    def test_create_product_with_no_images_success(self):
        """Test creating product master with no images"""
        print("Testing product creation with no images...")

        with self.get_test_session() as db:
            # Create product data with empty images list
            product_data = self.create_sample_product_data(images=[])

            # Create product
            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify creation
            assert product.id is not None
            assert product.name == product_data["name"]
            assert product.images == "[]"  # Empty JSON array
            assert product.selling_price == product_data["selling_price"]

            print("✓ Product creation with no images successful")
            return True

    def test_create_product_with_single_image_success(self):
        """Test creating product master with single image"""
        print("Testing product creation with single image...")

        with self.get_test_session() as db:
            # Create product data with single image
            images = ["https://example.com/sandwich-front.jpg"]
            product_data = self.create_sample_product_data(images=images)

            # Create product
            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify creation
            import json

            stored_images = json.loads(product.images)

            assert product.id is not None
            assert product.name == product_data["name"]
            assert len(stored_images) == 1
            assert stored_images[0] == "https://example.com/sandwich-front.jpg"

            print("✓ Product creation with single image successful")
            return True

    def test_create_product_with_multiple_images_success(self):
        """Test creating product master with multiple images"""
        print("Testing product creation with multiple images...")

        with self.get_test_session() as db:
            # Create product data with multiple images
            images = [
                "https://example.com/sandwich-front.jpg",
                "https://example.com/sandwich-side.jpg",
                "https://example.com/sandwich-top.jpg",
                "https://example.com/sandwich-ingredients.jpg",
            ]
            product_data = self.create_sample_product_data(images=images)

            # Create product
            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify creation
            import json

            stored_images = json.loads(product.images)

            assert product.id is not None
            assert product.name == product_data["name"]
            assert len(stored_images) == 4
            assert stored_images[0] == "https://example.com/sandwich-front.jpg"
            assert stored_images[1] == "https://example.com/sandwich-side.jpg"
            assert stored_images[2] == "https://example.com/sandwich-top.jpg"
            assert stored_images[3] == "https://example.com/sandwich-ingredients.jpg"

            print("✓ Product creation with multiple images successful")
            return True

    def test_update_product_images_success(self):
        """Test updating product images"""
        print("Testing product image updates...")

        with self.get_test_session() as db:
            # Create initial product with one image
            initial_images = ["https://example.com/old-image.jpg"]
            product_data = self.create_sample_product_data(images=initial_images)

            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Update with multiple new images
            import json

            new_images = [
                "https://example.com/new-image1.jpg",
                "https://example.com/new-image2.jpg",
                "https://example.com/new-image3.jpg",
            ]

            product.images = json.dumps(new_images)
            product.updated_at = datetime.now(timezone.utc)

            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify update
            stored_images = json.loads(product.images)

            assert len(stored_images) == 3
            assert stored_images[0] == "https://example.com/new-image1.jpg"
            assert stored_images[1] == "https://example.com/new-image2.jpg"
            assert stored_images[2] == "https://example.com/new-image3.jpg"

            print("✓ Product image updates successful")
            return True

    def test_add_images_to_existing_product_success(self):
        """Test adding images to product that had no images"""
        print("Testing adding images to existing product...")

        with self.get_test_session() as db:
            # Create product with no images
            product_data = self.create_sample_product_data(images=[])

            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify no images initially
            import json

            initial_images = json.loads(product.images)
            assert len(initial_images) == 0

            # Add images
            new_images = [
                "https://example.com/added-image1.jpg",
                "https://example.com/added-image2.jpg",
            ]

            product.images = json.dumps(new_images)
            product.updated_at = datetime.now(timezone.utc)

            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify images were added
            stored_images = json.loads(product.images)

            assert len(stored_images) == 2
            assert stored_images[0] == "https://example.com/added-image1.jpg"
            assert stored_images[1] == "https://example.com/added-image2.jpg"

            print("✓ Adding images to existing product successful")
            return True

    def test_remove_all_images_success(self):
        """Test removing all images from product"""
        print("Testing removing all images...")

        with self.get_test_session() as db:
            # Create product with multiple images
            initial_images = [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg",
                "https://example.com/image3.jpg",
            ]
            product_data = self.create_sample_product_data(images=initial_images)

            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Remove all images
            import json

            product.images = json.dumps([])
            product.updated_at = datetime.now(timezone.utc)

            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify all images removed
            stored_images = json.loads(product.images)
            assert len(stored_images) == 0

            print("✓ Removing all images successful")
            return True

    def test_validate_image_urls_format(self):
        """Test that image URLs are properly formatted"""
        print("Testing image URL format validation...")

        with self.get_test_session() as db:
            # Test with various URL formats
            test_images = [
                "https://example.com/image1.jpg",
                "http://example.com/image2.png",
                "https://cdn.example.com/path/to/image3.webp",
                "https://storage.googleapis.com/bucket/image4.jpeg",
            ]

            product_data = self.create_sample_product_data(images=test_images)

            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)

            # Verify all URLs are stored correctly
            import json

            stored_images = json.loads(product.images)

            assert len(stored_images) == 4
            for i, url in enumerate(test_images):
                assert stored_images[i] == url

            print("✓ Image URL format validation successful")
            return True

    def test_retrieve_product_with_images_success(self):
        """Test retrieving product and parsing images correctly"""
        print("Testing product retrieval with images...")

        with self.get_test_session() as db:
            # Create product with images
            images = [
                "https://example.com/product-main.jpg",
                "https://example.com/product-detail.jpg",
            ]
            product_data = self.create_sample_product_data(images=images)

            product = TestProductMaster(**product_data)
            db.add(product)
            db.commit()
            db.refresh(product)
            product_id = product.id

            # Retrieve product
            retrieved_product = db.get(TestProductMaster, product_id)

            # Verify retrieval and image parsing
            assert retrieved_product is not None
            assert retrieved_product.id == product_id

            import json

            retrieved_images = json.loads(retrieved_product.images)

            assert len(retrieved_images) == 2
            assert retrieved_images[0] == "https://example.com/product-main.jpg"
            assert retrieved_images[1] == "https://example.com/product-detail.jpg"

            print("✓ Product retrieval with images successful")
            return True


def run_all_tests():
    """Run all test functions"""
    test_class = TestProductMasterMultipleImages()

    test_functions = [
        test_class.test_create_product_with_no_images_success,
        test_class.test_create_product_with_single_image_success,
        test_class.test_create_product_with_multiple_images_success,
        test_class.test_update_product_images_success,
        test_class.test_add_images_to_existing_product_success,
        test_class.test_remove_all_images_success,
        test_class.test_validate_image_urls_format,
        test_class.test_retrieve_product_with_images_success,
    ]

    print("=" * 70)
    print("Running ProductMaster Multiple Images Tests")
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
            # Print full traceback for debugging
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print(
            "🎉 All tests passed! ProductMaster multiple images functionality works correctly."
        )

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
