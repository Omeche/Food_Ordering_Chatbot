CREATE DATABASE IF NOT EXISTS theo_eat
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE theo_eat;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS order_tracking;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS food_items;

-- Drop existing functions and procedures if they exist
DROP FUNCTION IF EXISTS get_price_for_item;
DROP FUNCTION IF EXISTS get_total_order_price;
DROP PROCEDURE IF EXISTS insert_order_item;

-- Create food_items table
CREATE TABLE food_items (
    item_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id),
    INDEX idx_food_name (name),
    INDEX idx_food_available (available)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insert menu items 
INSERT INTO food_items (name, price) VALUES
('Jollof Rice', 800.00),
('Porridge Beans', 700.00),
('Plantain', 400.00),
('Fish', 1200.00),
('Beef', 1500.00),
('Fried Egg', 300.00),
('White Rice', 700.00)


-- Create orders table 
CREATE TABLE orders (
    order_id INT NOT NULL AUTO_INCREMENT,
    session_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create order_tracking table\
CREATE TABLE order_tracking (
    order_id INT NOT NULL,
    status ENUM('Pending', 'Placed', 'Preparing', 'Ready', 'Delivered', 'Cancelled') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create order_items table 
CREATE TABLE order_items (
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, item_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES food_items(item_id) ON DELETE RESTRICT,
    CHECK (quantity > 0),
    CHECK (unit_price >= 0),
    CHECK (total_price >= 0),
    INDEX idx_order_items_order_id (order_id),
    INDEX idx_order_items_item_id (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create a view for easy order summaries
CREATE VIEW order_summary AS
SELECT 
    o.order_id,
    o.session_id,
    ot.status,
    COUNT(oi.item_id) as item_count,
    COALESCE(SUM(oi.total_price), 0) as total_amount,
    o.created_at,
    o.updated_at
FROM orders o
LEFT JOIN order_tracking ot ON o.order_id = ot.order_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id, o.session_id, ot.status, o.created_at, o.updated_at;

-- Create a view for detailed order information
CREATE VIEW order_details AS
SELECT 
    o.order_id,
    o.session_id,
    ot.status,
    f.name as food_item,
    oi.quantity,
    oi.unit_price,
    oi.total_price,
    o.created_at as order_created,
    oi.updated_at as item_updated
FROM orders o
JOIN order_tracking ot ON o.order_id = ot.order_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN food_items f ON oi.item_id = f.item_id
ORDER BY o.order_id, f.name;

-- Get price by food item name 
DELIMITER $$
CREATE FUNCTION get_price_for_item(p_item_name VARCHAR(255)) 
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_price DECIMAL(10,2) DEFAULT 0.00;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_price = 0.00;
    
    SELECT price INTO v_price 
    FROM food_items 
    WHERE LOWER(name) = LOWER(TRIM(p_item_name)) 
    AND available = TRUE
    LIMIT 1;
    
    RETURN v_price;
END$$
DELIMITER ;

-- Get total price of an order
DELIMITER $$
CREATE FUNCTION get_total_order_price(p_order_id INT) 
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total DECIMAL(10,2) DEFAULT 0.00;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_total = 0.00;
    
    SELECT COALESCE(SUM(total_price), 0.00) INTO v_total 
    FROM order_items 
    WHERE order_id = p_order_id;
    
    RETURN v_total;
END$$
DELIMITER ;

-- Insert or update order item
DELIMITER $$
CREATE PROCEDURE insert_order_item(
    IN p_food_item VARCHAR(255),
    IN p_quantity INT,
    IN p_order_id INT
)
BEGIN
    DECLARE v_item_id INT DEFAULT 0;
    DECLARE v_price DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_total_price DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_error_msg VARCHAR(255) DEFAULT '';
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    -- Validate inputs
    IF p_quantity <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Quantity must be greater than 0';
    END IF;
    
    IF p_order_id <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid order ID';
    END IF;
    
    -- Start transaction
    START TRANSACTION;
    
    -- Get item details
    SELECT item_id, price INTO v_item_id, v_price
    FROM food_items
    WHERE LOWER(name) = LOWER(TRIM(p_food_item))
    AND available = TRUE
    LIMIT 1;

    -- Check if food item exists
    IF v_item_id = 0 OR v_item_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Food item not found or not available';
    END IF;
    
    -- Calculate total price
    SET v_total_price = v_price * p_quantity;

    -- Insert or update order item
    INSERT INTO order_items(order_id, item_id, quantity, unit_price, total_price)
    VALUES (p_order_id, v_item_id, p_quantity, v_price, v_total_price)
    ON DUPLICATE KEY UPDATE
        quantity = VALUES(quantity),
        unit_price = VALUES(unit_price),
        total_price = VALUES(total_price),
        updated_at = CURRENT_TIMESTAMP;
    
    -- Update order tracking timestamp
    UPDATE order_tracking 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = p_order_id;
    
    COMMIT;
END$$
DELIMITER ;

-- Remove order item
DELIMITER $$
CREATE PROCEDURE remove_order_item(
    IN p_order_id INT,
    IN p_food_item VARCHAR(255),
    IN p_quantity INT
)
BEGIN
    DECLARE v_item_id INT DEFAULT 0;
    DECLARE v_current_qty INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- Get item ID
    SELECT item_id INTO v_item_id
    FROM food_items
    WHERE LOWER(name) = LOWER(TRIM(p_food_item))
    LIMIT 1;
    
    IF v_item_id = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Food item not found';
    END IF;
    
    -- Get current quantity
    SELECT quantity INTO v_current_qty
    FROM order_items
    WHERE order_id = p_order_id AND item_id = v_item_id;
    
    IF v_current_qty IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Item not found in order';
    END IF;
    
    -- Remove or update quantity
    IF p_quantity >= v_current_qty THEN
        -- Remove item completely
        DELETE FROM order_items 
        WHERE order_id = p_order_id AND item_id = v_item_id;
    ELSE
        -- Reduce quantity
        UPDATE order_items 
        SET 
            quantity = quantity - p_quantity,
            total_price = unit_price * (quantity - p_quantity),
            updated_at = CURRENT_TIMESTAMP
        WHERE order_id = p_order_id AND item_id = v_item_id;
    END IF;
    
    -- Update order tracking timestamp
    UPDATE order_tracking 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = p_order_id;
    
    COMMIT;
END$$
DELIMITER ;

-- Clear entire order
DELIMITER $$
CREATE PROCEDURE clear_order(
    IN p_order_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- Remove all items from order
    DELETE FROM order_items WHERE order_id = p_order_id;
    
    -- Update status to cancelled
    UPDATE order_tracking 
    SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP 
    WHERE order_id = p_order_id;
    
    COMMIT;
END$$
DELIMITER ;

-- Get or create order for session
DELIMITER $$
CREATE PROCEDURE get_or_create_order(
    IN p_session_id VARCHAR(255),
    OUT p_order_id INT
)
BEGIN
    DECLARE v_existing_order INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    -- Look for existing pending order
    SELECT o.order_id INTO v_existing_order
    FROM orders o
    JOIN order_tracking ot ON o.order_id = ot.order_id
    WHERE o.session_id = p_session_id 
    AND ot.status IN ('Pending')
    ORDER BY o.created_at DESC
    LIMIT 1;
    
    IF v_existing_order > 0 THEN
        SET p_order_id = v_existing_order;
    ELSE
        -- Create new order
        START TRANSACTION;
        
        INSERT INTO orders (session_id) VALUES (p_session_id);
        SET p_order_id = LAST_INSERT_ID();
        
        INSERT INTO order_tracking (order_id, status) 
        VALUES (p_order_id, 'Pending');
        
        COMMIT;
    END IF;
END$$
DELIMITER ;

-- Create indexes for better performance
CREATE INDEX idx_orders_session_created ON orders(session_id, created_at);
CREATE INDEX idx_order_tracking_status_updated ON order_tracking(status, updated_at);
CREATE INDEX idx_order_items_total_price ON order_items(total_price);

-- Create trigger to automatically update total_price when unit_price or quantity changes
DELIMITER $$
CREATE TRIGGER tr_order_items_update_total
    BEFORE UPDATE ON order_items
    FOR EACH ROW
BEGIN
    SET NEW.total_price = NEW.unit_price * NEW.quantity;
END$$
DELIMITER ;

-- Create trigger to automatically set unit_price and total_price on insert
DELIMITER $$
CREATE TRIGGER tr_order_items_insert_price
    BEFORE INSERT ON order_items
    FOR EACH ROW
BEGIN
    IF NEW.unit_price = 0 OR NEW.unit_price IS NULL THEN
        SELECT price INTO NEW.unit_price 
        FROM food_items 
        WHERE item_id = NEW.item_id;
    END IF;
    
    SET NEW.total_price = NEW.unit_price * NEW.quantity;
END$$
DELIMITER ;

-- Verify the database structure
SELECT 'Database setup completed successfully!' as status;

-- Show table structures 
DESCRIBE food_items;
DESCRIBE orders;
DESCRIBE order_tracking;
DESCRIBE order_items;