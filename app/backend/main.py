from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import re
import logging, os
from decimal import Decimal
from . import db_handler, function_handler
from . import init_db 
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug environment variables
logger.info("Checking environment variables...")
mysql_url = os.environ.get("MYSQL_URL")
logger.info(f"MYSQL_URL: {'Available' if mysql_url else 'Not set'}")

# Also check individual MySQL variables
mysql_vars = {
    'RAILWAY_ENVIRONMENT': os.environ.get("RAILWAY_ENVIRONMENT"),
    'MYSQLHOST': os.environ.get("MYSQLHOST"),
    'MYSQLUSER': os.environ.get("MYSQLUSER"),
    'MYSQLDATABASE': os.environ.get("MYSQLDATABASE"),
    'MYSQLPORT': os.environ.get("MYSQLPORT")
}

for var, value in mysql_vars.items():
    # Note: for security we don't print MYSQLPASSWORD here; ensure it's set in env
    logger.info(f"{var}: {value}")

# Initialize database on startup (only in production)
if os.environ.get("RAILWAY_ENVIRONMENT"):
    logger.info("Railway environment detected. Initializing database...")
    
    # Check if we have either MYSQL_URL or individual variables
    has_mysql_url = bool(os.environ.get("MYSQL_URL"))
    required_vars = ['MYSQLHOST', 'MYSQLUSER', 'MYSQLPASSWORD', 'MYSQLDATABASE']
    has_individual_vars = all(os.environ.get(var) for var in required_vars)
    
    if not (has_mysql_url or has_individual_vars):
        logger.error("No MySQL connection information found!")
        logger.error("Please set MYSQL_URL variable in Railway or ensure MySQL service is connected")
    else:
        try:
            db_init_success = init_db.initialize_database()
            if db_init_success:
                logger.info("Database initialization completed successfully")
            else:
                logger.error("Database initialization failed")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
else:
    logger.info("Local environment detected. Skipping auto-initialization")

app = Flask(__name__)

# Enable CORS for all domains on all routes
CORS(app, origins=["*"], allow_headers=["*"], methods=["*"], supports_credentials=True)

# Frontend routes - serve static files
@app.route('/')
def serve_index():
    # Serve index.html file
    try:
        # Navigate up from backend/ to app/ then into frontend/
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_path, 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return "Frontend not found. Please ensure frontend files are in the 'frontend' directory.", 404

@app.route('/cart.html')
def serve_cart():
    # Serve cart.html file
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_path, 'cart.html')
    except Exception as e:
        logger.error(f"Error serving cart.html: {e}")
        return "Cart page not found.", 404

@app.route('/<path:filename>')
def serve_static(filename):
    # Serve static frontend files
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        
        # Check if file exists in frontend directory
        file_path = os.path.join(frontend_path, filename)
        if os.path.exists(file_path):
            return send_from_directory(frontend_path, filename)
        
        logger.warning(f"File not found: {filename}")
        return "File not found", 404
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {e}")
        return "Error serving file", 500

# API Routes
@app.route("/webhook", methods=["POST"])
def handle_requests():
    try:
        payload = request.get_json()
        if not payload:
            logger.error("Empty payload on webhook")
            return jsonify({"fulfillmentText": "Empty request payload."})

        intent = payload['queryResult']['intent']['displayName']
        parameters = payload['queryResult']['parameters']
        output_contexts = payload['queryResult'].get('outputContexts', [])
        
        # Log the incoming request for debugging
        logger.info(f"Received intent: '{intent}' with parameters: {parameters}")
        
        # Extract session ID from main session path
        session_path = payload.get('session', '')
        session_id = function_handler.extract_session_id(session_path)
        
        # Fallback to context if session path fails
        if not session_id and output_contexts:
            session_id = function_handler.extract_session_id(output_contexts[0].get('name', ''))
        
        if not session_id:
            logger.error("Failed to extract session ID from payload")
            return jsonify({"fulfillmentText": "Session ID could not be extracted."})

        logger.info(f"Processing intent '{intent}' for session '{session_id}'")

        intent_dict = {
            "track.order-context: ongoing-tracking": track_order,
            "track.order": track_order,
            "order.add": add_order,
            "order.remove": remove_order,
            "order.complete": complete_order,
            "order.cancel": cancel_order
        }
        
        if intent not in intent_dict:
            logger.warning(f"Intent '{intent}' not found in intent_dict. Available intents: {list(intent_dict.keys())}")
            return jsonify({"fulfillmentText": f"I don't understand that command. Available commands are: add order, remove items, complete order, track order, or cancel order."})
        
        # Call the intent handler
        return intent_dict[intent](parameters, session_id)
        
    except KeyError as e:
        logger.error(f"Missing key in payload: {e}")
        return jsonify({"fulfillmentText": "Invalid request format received."})
    except Exception as e:
        logger.error(f"Unexpected error in handle_requests: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An unexpected error occurred. Please try again."})

# Add Order 
def add_order(parameters: dict, session_id: str):
    try:
        food_items = parameters.get('food-items', [])
        quantities = parameters.get('number', [])

        if not food_items:
            return jsonify({"fulfillmentText": "Please specify food items to add."})

        if not quantities:
            quantities = [1] * len(food_items)
        elif len(food_items) != len(quantities):
            return jsonify({"fulfillmentText": "Mismatched food items and quantities."})

        new_items = {}
        for name, qty in zip(food_items, quantities):
            name = str(name).strip().lower()
            try:
                qty_int = int(qty) if qty else 1
                if qty_int <= 0:
                    return jsonify({"fulfillmentText": f"Invalid quantity for {name}. Must be greater than 0."})
                new_items[name] = qty_int
            except (ValueError, TypeError):
                return jsonify({"fulfillmentText": f"Invalid quantity specified for {name}."})

        # Get existing pending order or create a new one
        order_id = db_handler.get_active_order(session_id, allowed_status=["Pending"])
        if not order_id:
            order_id = db_handler.create_order(session_id, status="Pending")
            
        # Fetch current items
        current_items = {it['food_item'].lower(): it['quantity'] for it in db_handler.fetch_order_items(order_id)}

        # Merge new items
        for item_name, qty in new_items.items():
            current_items[item_name] = current_items.get(item_name, 0) + qty

        # Save updated order
        success = db_handler.save_order(order_id, current_items)
        if not success:
            return jsonify({"fulfillmentText": "Error saving order. Please try again."})

        # Fetch updated items
        items_db = db_handler.fetch_order_items(order_id)
        lines, total = [], Decimal("0.00")
        for it in items_db:
            lines.append(f"{it['food_item']}({it['quantity']}) -- ₦{it['total_price']}")
            total += it['total_price']

        return jsonify({
            "fulfillmentText": (
                f"Order updated. Current items: {', '.join(lines)}. "
                f"Total: ₦{total}. \n"
                f"Your Order ID is {order_id}. You can track your order using this ID. \n"
                f"Would you like to add or remove more items?"
            )
        })
    except Exception as e:
        logger.error(f"Error in add_order: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An unexpected error occurred while adding items."})

# Parse Items 
def parse_items(user_input: str):
    if not user_input:
        return []
    
    user_input = user_input.lower().strip()
    
    if any(phrase in user_input for phrase in ["remove all", "clear all", "delete all", "cancel all"]):
        return [("all", None)]
    
    parts = re.split(r'\s+and\s+', user_input)
    
    items = []
    for part in parts:
        part = part.strip()
        pattern = r"(?:remove\s+|delete\s+)?(\d+)?\s*([a-zA-Z\s]+?)(?:\s*$)"
        match = re.search(pattern, part)
        if match:
            qty_str, name = match.groups()
            name = name.strip().lower()
            if not name or name in ["remove", "delete", "clear"]:
                continue
            if qty_str and qty_str.isdigit():
                quantity = int(qty_str)
            else:
                quantity = None  
            items.append((name, quantity))
    return items

# Alternative fallback function for complex removal commands
def parse_complex_removal(user_input: str, food_items: list, quantities: list):
    if not user_input:
        return list(zip(food_items, quantities)) if food_items else []
    
    user_input = user_input.lower().strip()
    parsed_items = parse_items(user_input)
    if parsed_items:
        return parsed_items
    
    items = []
    if food_items:
        if isinstance(food_items, str):
            food_items = [food_items]
        if isinstance(quantities, (int, float)):
            quantities = [quantities]
        elif not quantities:
            quantities = [None] * len(food_items)
        
        for i, item in enumerate(food_items):
            qty = quantities[i] if i < len(quantities) else None
            if qty is not None:
                try:
                    qty = int(float(qty)) if qty > 0 else None
                except (ValueError, TypeError):
                    qty = None
            items.append((item.lower().strip(), qty))
    return items

# Remove Order 
def remove_order(parameters: dict, session_id: str):
    try:
        order_id = db_handler.get_active_order(session_id, allowed_status=["Pending"])
        if not order_id:
            return jsonify({"fulfillmentText": "You have no pending order to modify."})
        
        current_status = db_handler.get_order_status(order_id)
        if current_status == "Placed":
            return jsonify({"fulfillmentText": "Order already placed. Cannot modify."})

        # Extract food items and quantities from parameters
        food_items = parameters.get('food-items', [])
        quantities = parameters.get('number', [])
        user_input = parameters.get('any', '') or parameters.get('text', '')
        
        # Normalize parameter types
        if isinstance(food_items, str):
            food_items = [food_items]
        if isinstance(quantities, (int, float)):
            quantities = [quantities]
        elif not quantities:
            quantities = []
        
        # Use complex parsing if raw user input is present, otherwise use structured params
        if user_input and "and" in user_input.lower():
            items_to_remove = parse_complex_removal(user_input, food_items, quantities)
        else:
            items_to_remove = list(zip(food_items, quantities)) if food_items else []
            items_to_remove = [(item, qty if qty is not None else None) for item, qty in items_to_remove]
        
        if not items_to_remove:
            return jsonify({"fulfillmentText": "Please specify what items to remove."})
        
        # Fetch current items
        current_items_raw = db_handler.fetch_order_items(order_id)
        if not current_items_raw:
            return jsonify({"fulfillmentText": "No items in your order to remove."})
        
        logger.info(f"BEFORE REMOVAL - Order {order_id} items: {current_items_raw}")
        logger.info(f"Items to remove: {items_to_remove}")

        current_items = {it['food_item'].lower(): it['quantity'] for it in current_items_raw}
        removed_items = []

        for item_name, qty_to_remove in items_to_remove:
            if not isinstance(item_name, str):
                continue
            item_name = item_name.strip().lower()
            
            if qty_to_remove is not None:
                try:
                    qty_to_remove = int(float(qty_to_remove))
                    if qty_to_remove <= 0:
                        continue
                except (ValueError, TypeError):
                    qty_to_remove = None
            
            matched_key = None
            for key in list(current_items.keys()):
                if item_name in key or key in item_name:
                    matched_key = key
                    break
            
            if matched_key:
                original_qty = current_items[matched_key]
                if qty_to_remove is None or qty_to_remove >= original_qty:
                    current_items.pop(matched_key)
                    removed_items.append(f"all {matched_key} ({original_qty})")
                else:
                    current_items[matched_key] = original_qty - qty_to_remove
                    removed_items.append(f"{qty_to_remove} {matched_key}")
            else:
                logger.warning(f"Item '{item_name}' not found in current order")

        logger.info(f"AFTER REMOVAL LOGIC - Order {order_id} items to save: {current_items}")
        logger.info(f"Items removed: {removed_items}")

        # Save updated order
        success = db_handler.save_order(order_id, current_items)
        if not success:
            return jsonify({"fulfillmentText": "Error updating order. Please try again."})
        
        # Verify what's in database after save
        items_after_save = db_handler.fetch_order_items(order_id)
        logger.info(f"AFTER SAVE - Order {order_id} items in DB: {items_after_save}")
        
        db_handler.mark_order_pending(order_id)

        if not removed_items:
            return jsonify({"fulfillmentText": "No matching items found to remove."})
        
        items_db = db_handler.fetch_order_items(order_id)
        if not items_db:
            return jsonify({"fulfillmentText": f"Removed {', '.join(removed_items)}. Your order is now empty."})

        lines, total = [], Decimal("0.00")
        for it in items_db:
            lines.append(f"{it['food_item']}({it['quantity']}) -- ₦{it['total_price']}")
            total += it['total_price']

        response_text = f"Removed {', '.join(removed_items)}. Updated order: {', '.join(lines)}. Total: ₦{total}"
        return jsonify({"fulfillmentText": response_text})
    except Exception as e:
        logger.error(f"Error in remove_order: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An unexpected error occurred while removing items."})

# Track Order 
def track_order(parameters: dict, session_id: str):
    try:
        num = parameters.get('number')
        
        if isinstance(num, list) and num:
            try:
                order_id = int(num[0])
            except (ValueError, TypeError):
                order_id = db_handler.get_latest_order(session_id)
        elif num:
            try:
                order_id = int(num if not isinstance(num, list) else num[0])
            except (ValueError, TypeError):
                return jsonify({"fulfillmentText": "Invalid order number."})
        else:
            order_id = db_handler.get_latest_order(session_id)

        if not order_id:
            return jsonify({"fulfillmentText": "You have no active orders to track."})

        status = db_handler.get_order_status(order_id)
        if not status:
            msg = f"Order {order_id} not found."
        else:
            items = db_handler.fetch_order_items(order_id)
            if items:
                total = sum(item['total_price'] for item in items)
                msg = f"Order {order_id} is {status}. Total: ₦{total} ({len(items)} items)"
            else:
                msg = f"Order {order_id} is {status} (empty)."
        return jsonify({"fulfillmentText": msg})
    except Exception as e:
        logger.error(f"Error in track_order: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An error occurred while tracking the order."})

# Complete Order 
def complete_order(parameters: dict, session_id: str):
    try:
        order_id = db_handler.get_active_order(session_id, allowed_status=["Pending"])
        if not order_id:
            return jsonify({"fulfillmentText": "No pending order to complete."})

        items = db_handler.fetch_order_items(order_id)
        if not items:
            return jsonify({"fulfillmentText": "No items in order. Please add items first."})

        current_status = db_handler.get_order_status(order_id)
        if current_status == "Placed":
            lines, total = [], Decimal("0.00")
            for it in items:
                lines.append(f"{it['food_item']}({it['quantity']}) ==> ₦{it['total_price']}")
                total += it['total_price']
            return jsonify({"fulfillmentText": f"Order {order_id} is already placed!\n{chr(10).join(lines)}\nTotal: ₦{total}"})

        lines, total = [], Decimal("0.00")
        for it in items:
            lines.append(f"{it['food_item']}({it['quantity']}) -- ₦{it['total_price']}")
            total += it['total_price']
        
        success = db_handler.mark_order_placed(order_id)
        if not success:
            logger.error(f"Failed to mark order {order_id} as placed for session {session_id}")
            return jsonify({"fulfillmentText": f"Error placing order {order_id}. Please contact support or try again."})

        logger.info(f"Order {order_id} successfully placed for session {session_id}")
        return jsonify({
            "fulfillmentText": f" Order {order_id} placed successfully!\n\n{chr(10).join(lines)}\n\nTotal: ₦{total}\n\nThank you for your order! You can navigate to 'my cart' section to view your order summary."
        })
    except Exception as e:
        logger.error(f"Unexpected error in complete_order: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An unexpected error occurred. Please try again or contact support."})

# Cancel Order 
def cancel_order(parameters: dict, session_id: str):
    try:
        num = parameters.get('number')
        if isinstance(num, list):
            num = num[0] if num else None

        if num:
            try:
                order_id = int(num if not isinstance(num, list) else num[0])
            except (ValueError, TypeError):
                return jsonify({"fulfillmentText": "Invalid order number."})
        else:
            order_id = db_handler.get_active_order(session_id, allowed_status=["Pending", "Placed"])

        if not order_id:
            return jsonify({"fulfillmentText": "No active order to cancel."})

        status = db_handler.get_order_status(order_id)
        if not status:
            return jsonify({"fulfillmentText": f"Order {order_id} not found."})

        if status == "Cancelled":
            return jsonify({"fulfillmentText": f"Order {order_id} is already cancelled."})

        message = db_handler.clear_order(order_id)
        return jsonify({"fulfillmentText": message})
    except Exception as e:
        logger.error(f"Error in cancel_order: {e}", exc_info=True)
        return jsonify({"fulfillmentText": "An unexpected error occurred while cancelling the order."})

@app.route('/api/order/<session_id>', methods=['GET'])
def get_order(session_id):
    try:
        # Get the active order for this session
        order_id = db_handler.get_active_order(session_id, allowed_status=["Pending", "Placed"])
        
        if not order_id:
            return jsonify({'items': [], 'total': 0})

        # Get order items from database
        items = db_handler.fetch_order_items(order_id)

        # Build a JSON-friendly response (convert Decimals to floats, include unit price)
        items_out = []
        grand_total = Decimal("0.00")
        for item in items:
            qty = item.get('quantity', 0)
            total_price_dec = item.get('total_price', Decimal("0.00"))
            try:
                unit_price_dec = (total_price_dec / qty) if qty else Decimal("0.00")
            except Exception:
                unit_price_dec = Decimal("0.00")

            items_out.append({
                'food_item': item.get('food_item'),
                'quantity': qty,
                'unit_price': float(unit_price_dec),
                'total_price': float(total_price_dec)
            })
            grand_total += total_price_dec

        return jsonify({
            'order_id': order_id,
            'items': items_out,
            'total': float(grand_total)
        })
    except Exception as e:
        logger.error(f"Error fetching order for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
