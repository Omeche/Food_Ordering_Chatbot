# Database Repair Script for Theo Eat Bot

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db_handler
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Main repair function
    print("=" * 50)
    print("THEO EAT DATABASE REPAIR TOOL")
    print("=" * 50)
    
    try:
        # Test database connection 
        print("1. Testing database connection...")
        conn = db_handler.get_connection()
        conn.close()
        print("   ✓ Database connection successful")
        
        # Run repair function
        print("\n2. Repairing database inconsistencies...")
        results = db_handler.repair_database_consistency()
        
        print(f"   Fixed {results['missing_tracking_fixed']} missing tracking records")
        print(f"   Removed {results['orphaned_tracking_removed']} orphaned tracking records")
        print(f"   Cleaned up {results['empty_orders_removed']} empty old orders")
        
        # Show current database state
        print("\n3. Current database state:")
        show_database_state()
        
        print("\n" + "=" * 50)
        print("DATABASE REPAIR COMPLETED SUCCESSFULLY!")
        print("Your bot should now work without integrity errors.")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n Error during repair: {e}")
        logger.error(f"Repair failed: {e}")
        return 1
    
    return 0

def show_database_state():
    # Show current state of the database
    try:
        conn = db_handler.get_connection()
        cursor = conn.cursor()
        
        # Count orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        # Count tracking records
        cursor.execute("SELECT COUNT(*) FROM order_tracking")
        tracking_count = cursor.fetchone()[0]
        
        # Count order items
        cursor.execute("SELECT COUNT(*) FROM order_items")
        items_count = cursor.fetchone()[0]
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM order_tracking 
            GROUP BY status 
            ORDER BY status
        """)
        status_counts = cursor.fetchall()
        
        print(f"  Total Orders: {order_count}")
        print(f"  Total Tracking Records: {tracking_count}")
        print(f"  Total Order Items: {items_count}")
        print("   Orders by Status:")
        for status, count in status_counts:
            print(f"     - {status}: {count}")
            
        # Check for inconsistencies
        cursor.execute("""
            SELECT COUNT(*) FROM orders o
            LEFT JOIN order_tracking ot ON o.order_id = ot.order_id
            WHERE ot.order_id IS NULL
        """)
        missing_tracking = cursor.fetchone()[0]
        
        if missing_tracking > 0:
            print(f"    WARNING: {missing_tracking} orders missing tracking records")
        else:
            print("    All orders have tracking records")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"    Error showing database state: {e}")

def reset_all_pending_orders():
    # Reset all orders to pending status
    try:
        conn = db_handler.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE order_tracking SET status = 'Pending' WHERE status NOT IN ('Placed', 'Delivered')")
        conn.commit()
        
        affected_rows = cursor.rowcount
        print(f"   ✓ Reset {affected_rows} orders to Pending status")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"    Error resetting orders: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-pending":
        print("Resetting all non-completed orders to Pending...")
        reset_all_pending_orders()
    else:
        exit_code = main()
        sys.exit(exit_code)