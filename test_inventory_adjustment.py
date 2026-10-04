import sqlite3

from utils.database import adjust_inventory_count
from utils.database import get_connection


def test_inventory_adjustment_creates_audit_and_exception():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT quantity_on_hand
            FROM inventory
            WHERE sku = 'SKU-001'
              AND warehouse_id = 'WH-MAIN'
            """
        )

        original_quantity = cursor.fetchone()[0]

        target_quantity = original_quantity + 3

    finally:
        connection.close()

    success, message = adjust_inventory_count(
        "SKU-001",
        "WH-MAIN",
        target_quantity,
        "Physical count correction test",
        "Warehouse",
    )

    assert success is True, message

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Inventory updated
        cursor.execute(
            """
            SELECT quantity_on_hand
            FROM inventory
            WHERE sku = 'SKU-001'
              AND warehouse_id = 'WH-MAIN'
            """
        )

        assert cursor.fetchone()[0] == target_quantity

        # Audit movement created
        cursor.execute(
            """
            SELECT movement_type, quantity_delta, reason
            FROM stock_movements
            WHERE sku = 'SKU-001'
              AND warehouse_id = 'WH-MAIN'
              AND movement_type = 'Inventory Adjustment'
            ORDER BY movement_id DESC
            LIMIT 1
            """
        )

        movement = cursor.fetchone()

        assert movement[0] == "Inventory Adjustment"
        assert movement[1] == 3
        assert movement[2] == "Physical count correction test"

        # Mismatch exception created
        cursor.execute(
            """
            SELECT issue_type, reference_type, reference_id, status
            FROM exceptions
            WHERE reference_type = 'Inventory'
              AND reference_id = 'WH-MAIN:SKU-001'
              AND issue_type = 'Inventory Mismatch'
            """
        )

        exception = cursor.fetchone()

        assert exception is not None
        assert exception[0] == "Inventory Mismatch"
        assert exception[1] == "Inventory"
        assert exception[2] == "WH-MAIN:SKU-001"
        assert exception[3] == "Open"

    finally:
        connection.close()


def test_inventory_adjustment_requires_reason():
    success, message = adjust_inventory_count(
        "SKU-001",
        "WH-MAIN",
        5,
        "",
        "Warehouse",
    )

    assert success is False
    assert "reason is required" in message.lower()


def test_inventory_adjustment_rejects_negative_count():
    success, message = adjust_inventory_count(
        "SKU-001",
        "WH-MAIN",
        -1,
        "Invalid physical count test",
        "Warehouse",
    )

    assert success is False
    assert "negative" in message.lower()


def test_inventory_adjustment_missing_sku():
    success, message = adjust_inventory_count(
        "SKU-DOES-NOT-EXIST",
        "WH-MAIN",
        5,
        "Missing SKU test",
        "Warehouse",
    )

    assert success is False
    assert "not found" in message.lower()