#!/usr/bin/env python3
"""
Simple test runner for get_month_to_date_revenue function
This script provides practical examples of how to test the analytics function
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_function_with_mock_database():
    """
    Demonstrates how to test the function with a mocked database session
    This is useful for unit testing without requiring a real database
    """
    print("🧪 Testing get_month_to_date_revenue with mock database...")

    # Import the function
    from apps.shops.analytics import get_month_to_date_revenue

    # Create mock database session
    mock_db = Mock()
    mock_result = Mock()

    # Test Case 1: Normal revenue calculation
    print("\n1. Testing normal revenue calculation...")
    mock_result.scalar.return_value = 1234.56
    mock_db.execute.return_value = mock_result

    revenue = get_month_to_date_revenue(mock_db, "test-shop-123")
    assert revenue == 1234.56
    print(f"   ✅ Revenue calculated correctly: ${revenue}")

    # Verify that execute was called (the function ran our query)
    assert mock_db.execute.called
    print("   ✅ Database query was executed")

    # Test Case 2: Zero revenue
    print("\n2. Testing zero revenue...")
    mock_result.scalar.return_value = 0
    revenue_zero = get_month_to_date_revenue(mock_db, "empty-shop")
    assert revenue_zero == 0.0
    print(f"   ✅ Zero revenue handled correctly: ${revenue_zero}")

    # Test Case 3: Null revenue (database returns None)
    print("\n3. Testing null revenue handling...")
    mock_result.scalar.return_value = None
    revenue_null = get_month_to_date_revenue(mock_db, "null-shop")
    assert revenue_null == 0.0
    print(f"   ✅ Null revenue converted to zero: ${revenue_null}")


def demonstrate_query_inspection():
    """
    Shows what SQL query the function generates and what conditions it uses
    """
    print("\n🔍 Inspecting the SQL query logic...")

    from apps.core.utils import get_current_time_utc
    from apps.orders.constants import ORDER_STATUS_CONFIRMED

    # Show the time range calculation
    now = get_current_time_utc()
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    print(f"\n📅 Date Range Calculation:")
    print(f"   Current time: {now}")
    print(f"   Month start:  {month_start}")
    print(f"   Days so far:  {(now - month_start).days}")

    print(f"\n🔧 SQL Query Conditions:")
    print(f"   ✓ Order.shop_id == 'your_shop_id'")
    print(f"   ✓ Order.status == '{ORDER_STATUS_CONFIRMED}'")
    print(f"   ✓ Order.completed_at >= {month_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   ✓ Order.completed_at <= {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    print(
        f"\n📊 The query sums up Order.final_price for orders matching these conditions"
    )


def show_manual_testing_example():
    """
    Provides copy-paste code for manual testing with real database
    """
    print("\n📋 Manual Testing Example Code:")
    print("=" * 50)

    manual_code = """
# Copy and paste this code to test with your actual database:

from apps.core.database import get_db_session  # Adjust import as needed
from apps.shops.analytics import get_month_to_date_revenue

# Get database session
db = next(get_db_session())

# Test with a real shop ID from your database
shop_id = "your-actual-shop-id-here"  # Replace with real shop ID

try:
    revenue = get_month_to_date_revenue(db, shop_id)
    print(f"Month-to-date revenue for shop {shop_id}: ${revenue}")
    
    # Test with non-existent shop
    fake_revenue = get_month_to_date_revenue(db, "fake-shop-id")
    print(f"Revenue for non-existent shop: ${fake_revenue}")  # Should be 0.0
    
except Exception as e:
    print(f"Error during testing: {e}")
finally:
    db.close()
"""

    print(manual_code)


def show_validation_queries():
    """
    Shows SQL queries you can run directly to validate the function results
    """
    print("\n🗄️  Database Validation Queries:")
    print("=" * 50)

    validation_sql = """
-- Run these SQL queries to manually verify the function results:

-- 1. Check total revenue for a shop this month
SELECT 
    shop_id,
    SUM(final_price) as total_revenue,
    COUNT(*) as order_count
FROM orders 
WHERE shop_id = 'your-shop-id-here'  -- Replace with actual shop ID
  AND status = 'confirmed'
  AND completed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
  AND completed_at <= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
GROUP BY shop_id;

-- 2. See all confirmed orders for the shop this month
SELECT 
    id,
    final_price,
    status,
    completed_at
FROM orders 
WHERE shop_id = 'your-shop-id-here'
  AND status = 'confirmed' 
  AND completed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
ORDER BY completed_at DESC;

-- 3. Compare with all orders (including non-confirmed)
SELECT 
    status,
    COUNT(*) as count,
    SUM(final_price) as total_price
FROM orders 
WHERE shop_id = 'your-shop-id-here'
  AND completed_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
GROUP BY status;
"""

    print(validation_sql)


def create_test_data_example():
    """
    Shows how to create test data for thorough testing
    """
    print("\n🏗️  Creating Test Data Example:")
    print("=" * 50)

    test_data_code = """
# Example code to create test data for comprehensive testing:

from apps.orders.models.orders import Order
from datetime import datetime, timezone, timedelta
import uuid

# Get your database session
db = next(get_db_session())

# Test shop ID
test_shop_id = str(uuid.uuid4())
now = datetime.now(timezone.utc)
month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

try:
    # Create test orders with different scenarios
    test_orders = [
        # Current month confirmed orders (should be counted)
        Order(shop_id=test_shop_id, final_price=100.50, status="confirmed", 
              completed_at=now - timedelta(days=1)),
        Order(shop_id=test_shop_id, final_price=75.25, status="confirmed", 
              completed_at=month_start + timedelta(hours=1)),
        
        # Non-confirmed orders (should be excluded)
        Order(shop_id=test_shop_id, final_price=200.00, status="cancelled", 
              completed_at=now),
        Order(shop_id=test_shop_id, final_price=50.00, status="pending", 
              completed_at=now),
        
        # Previous month order (should be excluded) 
        Order(shop_id=test_shop_id, final_price=300.00, status="confirmed", 
              completed_at=month_start - timedelta(days=1)),
    ]
    
    # Add all test orders
    for order in test_orders:
        db.add(order)
    db.commit()
    
    # Test the function
    revenue = get_month_to_date_revenue(db, test_shop_id)
    print(f"Expected revenue: $175.75 (100.50 + 75.25)")
    print(f"Actual revenue: ${revenue}")
    
    # Clean up test data
    db.query(Order).filter(Order.shop_id == test_shop_id).delete()
    db.commit()
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
"""

    print(test_data_code)


def main():
    """
    Main function that runs all test demonstrations
    """
    print("🚀 Analytics Function Testing Guide")
    print("=" * 50)

    # Run the mock test
    test_function_with_mock_database()

    # Show query details
    demonstrate_query_inspection()

    # Show manual testing code
    show_manual_testing_example()

    # Show validation queries
    show_validation_queries()

    # Show test data creation
    create_test_data_example()

    print("\n✨ Testing Guide Complete!")
    print("\nRecommended testing approach:")
    print("1. ✅ Start with mock tests (demonstrated above)")
    print("2. 🗄️  Use manual testing code with real database")
    print("3. 🔍 Validate results with SQL queries")
    print("4. 🏗️  Create comprehensive test data")
    print("5. 🧪 Set up automated integration tests")


if __name__ == "__main__":
    main()
