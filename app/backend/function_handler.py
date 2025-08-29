import re
from typing import Optional, Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_session_id(session_path: str) -> Optional[str]:
    # Extract session ID from Dialogflow session path.

    if not session_path:
        return None
    
    try:
        # Primary pattern for standard session paths
        match = re.search(r"/sessions/([^/]+)", session_path)
        if match:
            session_id = match.group(1)
            logger.debug(f"Extracted session ID: {session_id}")
            return session_id
        
        # Fallback: try to extract any ID-like string at the end
        match = re.search(r"/([a-zA-Z0-9_-]+)(?:\?|$)", session_path)
        if match:
            session_id = match.group(1)
            logger.debug(f"Extracted fallback session ID: {session_id}")
            return session_id
        
        logger.warning(f"Could not extract session ID from: {session_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting session ID from '{session_path}': {e}")
        return None

def validate_session_id(session_id: str) -> bool:

    # Validate that session ID is in acceptable format
    if not session_id or len(session_id) < 3:
        return False
    
    # Allow alphanumeric, hyphens, underscores
    pattern = r"^[a-zA-Z0-9_-]+"
    return bool(re.match(pattern, session_id))

def normalize_food_name(food_name: str) -> str:
    # Normalize food item names for consistent matching

    if not food_name:
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = food_name.lower().strip()
    
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Handle common variations
    replacements = {
        'jollof': 'jollof rice',
        'beans': 'porridge beans',
        'egg': 'fried egg',
        'white': 'white rice',
    }
    
    for key, value in replacements.items():
        if key in normalized and value not in normalized:
            normalized = value
            break
    
    return normalized

def output_from_food_dict(food_dict: Dict[str, int]) -> str:
    # Convert dictionary of food items and quantities into a readable string.

    if not food_dict:
        return "No items in the order."
    
    try:
        parts = []
        for item, quantity in food_dict.items():
            if quantity > 0:  # Only include positive quantities
                quantity = int(quantity)
                item_formatted = item.title()  # Capitalize first letter of each word
                if quantity == 1:
                    parts.append(f"{item_formatted}")
                else:
                    parts.append(f"{quantity} x {item_formatted}")
        
        if not parts:
            return "No valid items in the order."
        
        return ", ".join(parts)
        
    except Exception as e:
        logger.error(f"Error formatting food dictionary: {e}")
        return "Error formatting order items."

def parse_dialogflow_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    # Parse and clean Dialogflow parameters for consistent handling

    cleaned_params = {}
    
    for key, value in parameters.items():
        if value is None:
            continue
            
        # Handle list parameters
        if isinstance(value, list):
            if value:  # Non-empty list
                cleaned_params[key] = [str(item).strip() for item in value if item]
            else:
                cleaned_params[key] = []
        
        # Handle string parameters
        elif isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value:
                cleaned_params[key] = cleaned_value
        
        # Handle numeric parameters
        elif isinstance(value, (int, float)):
            cleaned_params[key] = value
        
        # Handle other types as-is
        else:
            cleaned_params[key] = value
    
    return cleaned_params

def extract_food_items_and_quantities(parameters: Dict[str, Any]) -> List[tuple]:
    # Extract food items and quantities from various parameter formats

    items = []
    
    # Get food items
    food_items = parameters.get('food-items', [])
    if isinstance(food_items, str):
        food_items = [food_items]
    elif not isinstance(food_items, list):
        food_items = []
    
    # Get quantities
    quantities = parameters.get('number', [])
    if isinstance(quantities, (int, float)):
        quantities = [quantities]
    elif isinstance(quantities, str):
        try:
            quantities = [int(quantities)]
        except ValueError:
            quantities = []
    elif not isinstance(quantities, list):
        quantities = []
    
    # Match items with quantities
    for i, item in enumerate(food_items):
        if not item:
            continue
            
        item_normalized = normalize_food_name(str(item))
        if not item_normalized:
            continue
            
        # Get corresponding quantity or default to 1
        if i < len(quantities):
            try:
                qty = int(quantities[i])
                if qty <= 0:
                    qty = 1
            except (ValueError, TypeError):
                qty = 1
        else:
            qty = 1
        
        items.append((item_normalized, qty))
    
    return items

def format_currency(amount) -> str:
    # Format currency amount consistently

    try:
        from decimal import Decimal
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        # Format to 2 decimal places
        return f"₦{amount:.2f}"
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return f"₦{amount}"

def create_order_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Create a formatted order summary from order items

    try:
        from decimal import Decimal
        
        if not items:
            return {
                'items_text': 'No items in order',
                'total': Decimal('0.00'),
                'count': 0,
                'formatted_total': '₦0.00'
            }
        
        lines = []
        total = Decimal('0.00')
        
        for item in items:
            food_item = item.get('food_item', 'Unknown Item')
            quantity = item.get('quantity', 0)
            total_price = item.get('total_price', Decimal('0.00'))
            
            if isinstance(total_price, str):
                total_price = Decimal(total_price)
            
            lines.append(f"{food_item} ({quantity}) = {format_currency(total_price)}")
            total += total_price
        
        return {
            'items_text': ', '.join(lines),
            'total': total,
            'count': len(items),
            'formatted_total': format_currency(total)
        }
        
    except Exception as e:
        logger.error(f"Error creating order summary: {e}")
        return {
            'items_text': 'Error formatting order',
            'total': Decimal('0.00'),
            'count': 0,
            'formatted_total': '₦0.00'
        }

def validate_quantity(qty_input) -> int:
    # Validate and normalize quantity input

    try:
        if qty_input is None:
            return 1
            
        if isinstance(qty_input, str):
            qty_input = qty_input.strip()
            if not qty_input:
                return 1
        
        qty = int(float(qty_input))  # Handle decimal strings
        
        # Validate range
        if qty < 1:
            return 1
        elif qty > 100:  # Reasonable maximum
            return 100
        
        return qty
        
    except (ValueError, TypeError):
        logger.warning(f"Invalid quantity input: {qty_input}, defaulting to 1")
        return 1

def extract_order_id_from_text(text: str) -> Optional[int]:
    # Extract order ID from user text input

    if not text:
        return None
    
    try:
        patterns = [
            r'order\s*#?(\d+)',
            r'#(\d+)',
            r'\b(\d+)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                order_id = int(match.group(1))
                if 1 <= order_id <= 999999: 
                    return order_id
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting order ID from text '{text}': {e}")
        return None

def clean_user_input(user_input: str) -> str:
    # Clean and normalize user input text

    if not user_input:
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', user_input.strip())
    
    # Remove common filler words that might interfere with parsing
    filler_words = ['please', 'can you', 'i want', 'i would like', 'give me', 'add']
    for word in filler_words:
        cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra spaces again
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

# Example usage and testing
if __name__ == "__main__":
    # Test session ID extraction
    test_sessions = [
        "projects/my-project/agent/sessions/1234567890",
        "projects/my-project/agent/environments/draft/users/-/sessions/abc-123",
        "projects/my-project/locations/us-central1/agent/sessions/session_xyz"
    ]
    
    print("Testing session ID extraction:")
    for session in test_sessions:
        session_id = extract_session_id(session)
        print(f"  {session} -> {session_id}")
    
    # Test food dictionary formatting
    print(f"\nTesting food dictionary formatting:")
    example_order = {"jollof rice": 2, "fried egg": 1, "plantain": 3}
    print(f"  {example_order} -> {output_from_food_dict(example_order)}")
    
    # Test parameter parsing
    print(f"\nTesting parameter parsing:")
    test_params = {
        'food-items': ['Jollof Rice', 'Fish'],
        'number': [2, 1],
        'any': '  remove 2 jollof rice  ',
        'empty-list': [],
        'null-value': None
    }
    cleaned = parse_dialogflow_parameters(test_params)
    print(f"  Cleaned parameters: {cleaned}")
    
    # Test food items extraction
    items = extract_food_items_and_quantities(cleaned)
    print(f"  Extracted items: {items}")