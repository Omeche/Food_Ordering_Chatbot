import mysql.connector
from decimal import Decimal
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection 
def get_connection():
    # Get database connection with proper error handling
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="theo",
            database="theo_eat",
            auth_plugin="mysql_native_password",
            autocommit=False,  
            charset='utf8mb4',
            use_unicode=True
        )
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

# Order Status 
def get_order_status(order_id: int) -> Optional[str]:
    # Get the status of an order
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT status FROM order_tracking WHERE order_id = %s",
            (order_id,)
        )
        result = cursor.fetchone()
        return result["status"] if result else None
    except mysql.connector.Error as e:
        logger.error(f"Database error in get_order_status: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Session Management
def get_active_order(session_id: str, allowed_status=("Pending", "Placed")) -> Optional[int]:
    """
    Fetch the most recent order for a session with a status in allowed_status.
    Example: allowed_status=("Pending",) to only allow open cart.
    """
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT o.order_id 
            FROM orders o
            JOIN order_tracking ot ON o.order_id = ot.order_id
            WHERE o.session_id = %s 
              AND ot.status IN ({','.join(['%s'] * len(allowed_status))})
            ORDER BY o.created_at DESC
            LIMIT 1
        """, (session_id, *allowed_status))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def get_latest_order(session_id: str) -> Optional[int]:
    """
    Fetch the most recent order for a session, regardless of status.
    Used mainly for tracking.
    """
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.order_id
            FROM orders o
            ORDER BY o.created_at DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def create_order(session_id: str, status: str = "Pending") -> int:
    """
    Create a brand new order and tracking entry.
    """
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        cursor.execute("INSERT INTO orders (session_id) VALUES (%s)", (session_id,))
        order_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)",
            (order_id, status)
        )

        conn.commit()
        logger.info(f"Created new order {order_id} for session {session_id} with status {status}")
        return order_id
    except mysql.connector.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error in create_order: {e}")
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def _update_order_status(order_id: int, status: str):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE order_tracking SET status=%s WHERE order_id=%s",
            (status, order_id)
        )
        conn.commit()
        logger.info(f"Order {order_id} updated to {status}")
    except mysql.connector.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error updating order {order_id} to {status}: {e}")
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Food Item Utilities 
def get_food_item_by_name(item_name: str) -> Optional[tuple]:
    # Get food item by name 
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        item_name = item_name.strip().lower()
        
        # exact match
        cursor.execute("SELECT item_id, name, price FROM food_items WHERE LOWER(name) = %s", (item_name,))
        result = cursor.fetchone()
        if result:
            return result
        
        # partial match
        cursor.execute("SELECT item_id, name, price FROM food_items WHERE LOWER(name) LIKE %s", (f"%{item_name}%",))
        result = cursor.fetchone()
        return result
        
    except mysql.connector.Error as e:
        logger.error(f"Error getting food item: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#  Order Item Operations 
def update_order_item(cursor, order_id: int, item_id: int, qty: int, price: Decimal):
    # Update or insert a single order item
    total_price = price * Decimal(qty)
    
    # Check if item exists
    cursor.execute(
        "SELECT quantity FROM order_items WHERE order_id = %s AND item_id = %s",
        (order_id, item_id)
    )
    existing = cursor.fetchone()
    
    if existing:
        # Update existing item
        cursor.execute(
            "UPDATE order_items SET quantity = %s, total_price = %s WHERE order_id = %s AND item_id = %s",
            (qty, total_price, order_id, item_id)
        )
    else:
        # Insert new item
        cursor.execute(
            "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (%s, %s, %s, %s)",
            (order_id, item_id, qty, total_price)
        )

# Sync Full Order 
def save_order(order_id: int, food_items: Dict[str, int]) -> bool:
    # Sync order_items table to match exactly the passed food_items dict.
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        
        # Clear existing items to ensure clean state
        cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
        
        # Process new items
        valid_items_added = False
        for item_name, qty in food_items.items():
            if qty <= 0:  
                continue
                
            # Get food item details
            food_item = get_food_item_by_name(item_name)
            if not food_item:
                logger.warning(f"Food item '{item_name}' not found, skipping...")
                continue
                
            item_id, actual_name, price = food_item
            qty = int(qty)
            
            # Insert the item
            total_price = price * Decimal(qty)
            cursor.execute(
                "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (%s, %s, %s, %s)",
                (order_id, item_id, qty, total_price)
            )
            valid_items_added = True
        conn.commit()
        logger.info(f"Successfully saved order {order_id} with {len(food_items)} items")
        return True
        
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error in save_order: {e}")
        return False
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in save_order: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Fetch Items 
def fetch_order_items(order_id: int) -> List[Dict[str, Any]]:
    # Fetch all items in an order
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.name AS food_item, oi.quantity, oi.total_price
            FROM order_items oi
            JOIN food_items f ON oi.item_id = f.item_id
            WHERE oi.order_id = %s
            ORDER BY f.name
        """, (order_id,))
        
        results = cursor.fetchall()
        return results if results else []
        
    except mysql.connector.Error as e:
        logger.error(f"Error fetching order items: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Legacy Item Utilities 
def get_item_id(item_name: str) -> Optional[int]:
    #Get item ID by name
    food_item = get_food_item_by_name(item_name)
    return food_item[0] if food_item else None

def get_order_item(order_id: int, item_id: int) -> Optional[tuple]:
    # Get specific order item
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT quantity, total_price FROM order_items WHERE order_id = %s AND item_id = %s",
            (order_id, item_id)
        )
        return cursor.fetchone()
    except mysql.connector.Error as e:
        logger.error(f"Error getting order item: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_order_item(order_id: int, item_id: int) -> bool:
    # Delete specific order item
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM order_items WHERE order_id = %s AND item_id = %s",
            (order_id, item_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as e:
        logger.error(f"Error deleting order item: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#  Clear / Cancel Order
def clear_order(order_id: int) -> str:
    # Clear all items from order and mark as cancelled
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        
        # Clear order items
        cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
        items_deleted = cursor.rowcount
        
        # Update status
        cursor.execute("UPDATE order_tracking SET status = 'Cancelled' WHERE order_id = %s", (order_id,))
        status_updated = cursor.rowcount > 0

        conn.commit()
        
        if status_updated:
            return f"Order {order_id} cancelled successfully. {items_deleted} items removed."
        else:
            return f"Order {order_id} cleared but status update failed."
            
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error clearing order: {e}")
        return f"Error cancelling order {order_id}. Please try again."
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Mark Order Status 
def mark_order_pending(order_id: int) -> bool:
    # Mark order as pending
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO order_tracking (order_id, status) 
            VALUES (%s, 'Pending')
            ON DUPLICATE KEY UPDATE 
            status = 'Pending'
        """, (order_id,))
        
        conn.commit()
        return True
        
    except mysql.connector.Error as e:
        logger.error(f"Error marking order pending: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def mark_order_placed(order_id: int) -> bool:
    # Mark order as placed
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if record exists
        cursor.execute("SELECT order_id FROM order_tracking WHERE order_id = %s", (order_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing record
            cursor.execute("""
                UPDATE order_tracking 
                SET status = 'Placed' 
                WHERE order_id = %s
            """, (order_id,))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO order_tracking (order_id, status, created_at, updated_at) 
                VALUES (%s, 'Placed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (order_id,))
        
        conn.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Order {order_id} marked as placed")
        else:
            logger.warning(f"Failed to mark order {order_id} as placed")
        
        return True
        
    except mysql.connector.Error as e:
        logger.error(f"Error marking order placed: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Additional Utility Functions
def get_order_total(order_id: int) -> Decimal:
    # Calculate total price of an order
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(total_price) FROM order_items WHERE order_id = %s", (order_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else Decimal("0.00")
        
    except mysql.connector.Error as e:
        logger.error(f"Error calculating order total: {e}")
        return Decimal("0.00")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_food_items() -> List[Dict[str, Any]]:
    # Get all available food items
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT item_id, name, price FROM food_items ORDER BY name")
        return cursor.fetchall()
        
    except mysql.connector.Error as e:
        logger.error(f"Error getting food items: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def cleanup_old_orders(days: int = 7) -> int:
    # Clean up old cancelled/completed orders
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete orders older than specified days that are cancelled or placed
        cursor.execute("""
            DELETE o FROM orders o
            JOIN order_tracking ot ON o.order_id = ot.order_id
            WHERE ot.status IN ('Cancelled', 'Placed') 
            AND o.created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        
        conn.commit()
        deleted_count = cursor.rowcount
        logger.info(f"Cleaned up {deleted_count} old orders")
        return deleted_count
        
    except mysql.connector.Error as e:
        logger.error(f"Error cleaning up old orders: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def repair_database_consistency() -> Dict[str, int]:
    # Repair database consistency issues - run this if you encounter integrity errors
    conn = None
    cursor = None
    results = {
        'missing_tracking_fixed': 0,
        'orphaned_tracking_removed': 0,
        'empty_orders_removed': 0
    }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        
        # Add missing tracking records for orders
        cursor.execute("""
            INSERT IGNORE INTO order_tracking (order_id, status)
            SELECT o.order_id, 'Pending'
            FROM orders o
            LEFT JOIN order_tracking ot ON o.order_id = ot.order_id
            WHERE ot.order_id IS NULL
        """)
        results['missing_tracking_fixed'] = cursor.rowcount
        
        # Remove orphaned tracking records
        cursor.execute("""
            DELETE ot FROM order_tracking ot
            LEFT JOIN orders o ON ot.order_id = o.order_id
            WHERE o.order_id IS NULL
        """)
        results['orphaned_tracking_removed'] = cursor.rowcount
        
        # Remove orders with no items that are older than 1 hour and still pending
        cursor.execute("""
            DELETE o FROM orders o
            JOIN order_tracking ot ON o.order_id = ot.order_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE oi.order_id IS NULL 
            AND ot.status = 'Pending'
            AND o.created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        results['empty_orders_removed'] = cursor.rowcount
        
        conn.commit()
        logger.info(f"Database repair completed: {results}")
        return results
        
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error repairing database: {e}")
        return results
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()