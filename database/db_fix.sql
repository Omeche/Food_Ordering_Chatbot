-- Quick Fix SQL Commands for Theo Eat Database
-- Run these commands in your MySQL console to fix the immediate integrity error

USE theo_eat;

-- 1. Show current problematic state
SELECT 'Current Orders without Tracking:' as info;
SELECT o.order_id, o.session_id, o.created_at 
FROM orders o 
LEFT JOIN order_tracking ot ON o.order_id = ot.order_id 
WHERE ot.order_id IS NULL;

SELECT 'Current Tracking without Orders:' as info;
SELECT ot.order_id, ot.status 
FROM order_tracking ot 
LEFT JOIN orders o ON ot.order_id = o.order_id 
WHERE o.order_id IS NULL;

-- 2. Fix missing tracking records (this will fix the immediate error)
INSERT IGNORE INTO order_tracking (order_id, status)
SELECT o.order_id, 'Pending'
FROM orders o
LEFT JOIN order_tracking ot ON o.order_id = ot.order_id
WHERE ot.order_id IS NULL;

-- 3. Remove orphaned tracking records
DELETE ot FROM order_tracking ot
LEFT JOIN orders o ON ot.order_id = o.order_id
WHERE o.order_id IS NULL;

-- 4. Clean up duplicate or problematic records (if any)
-- This removes duplicate tracking entries (keep the first one)
DELETE t1 FROM order_tracking t1
INNER JOIN order_tracking t2 
WHERE t1.order_id = t2.order_id AND t1.updated_at > t2.updated_at;

-- 5. Show fixed state
SELECT 'After Fix - Orders:' as info;
SELECT COUNT(*) as total_orders FROM orders;

SELECT 'After Fix - Tracking:' as info;
SELECT status, COUNT(*) as count 
FROM order_tracking 
GROUP BY status;

SELECT 'After Fix - Consistency Check:' as info;
SELECT 
    (SELECT COUNT(*) FROM orders) as orders_count,
    (SELECT COUNT(*) FROM order_tracking) as tracking_count,
    (SELECT COUNT(*) FROM orders o LEFT JOIN order_tracking ot ON o.order_id = ot.order_id WHERE ot.order_id IS NULL) as missing_tracking;

-- 6. Verify no integrity issues remain
SELECT 'Verification Complete - Should show 0 missing tracking records above' as final_check;