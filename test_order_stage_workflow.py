import sqlite3

from utils.database import (
    transition_order_stage,
    verify_order_item_in_db,
)


DB_PATH = "database/fulfillment_hub.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def set_order_status(order_id, status):
    connection = get_connection()

    connection.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE order_id = ?
        """,
        (status, order_id),
    )

    connection.commit()
    connection.close()


def test_picking_to_picked_blocked_without_verification():
    set_order_status("ORD-1001", "Picking")

    success, message = transition_order_stage(
        order_id="ORD-1001",
        new_status="Picked",
        user_role="Warehouse",
    )

    assert success is False
    assert "need successful Picking verification" in message

    connection = get_connection()

    status = connection.execute(
        """
        SELECT status
        FROM orders
        WHERE order_id = ?
        """,
        ("ORD-1001",),
    ).fetchone()[0]

    connection.close()

    assert status == "Picking"


def test_picking_to_picked_allowed_after_verification():
    set_order_status("ORD-1002", "Picking")

    success, message = verify_order_item_in_db(
        order_item_id="OI-0002",
        scanned_sku="SKU-002",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="Black - 750ml",
        verified_quantity=5,
        stage="Picking",
        user_role="Warehouse",
    )

    assert success is True

    success, message = transition_order_stage(
        order_id="ORD-1002",
        new_status="Picked",
        user_role="Warehouse",
    )

    assert success is True

    connection = get_connection()

    status = connection.execute(
        """
        SELECT status
        FROM orders
        WHERE order_id = ?
        """,
        ("ORD-1002",),
    ).fetchone()[0]

    connection.close()

    assert status == "Picked"


def test_packing_to_packed_blocked_without_verification():
    set_order_status("ORD-1003", "Packing")

    success, message = transition_order_stage(
        order_id="ORD-1003",
        new_status="Packed",
        user_role="Warehouse",
    )

    assert success is False
    assert "need successful Packing verification" in message

    connection = get_connection()

    status = connection.execute(
        """
        SELECT status
        FROM orders
        WHERE order_id = ?
        """,
        ("ORD-1003",),
    ).fetchone()[0]

    connection.close()

    assert status == "Packing"


def test_packing_to_packed_allowed_after_verification():
    set_order_status("ORD-1004", "Packing")

    success, message = verify_order_item_in_db(
        order_item_id="OI-0004",
        scanned_sku="SKU-004",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="White - 750ml",
        verified_quantity=2,
        stage="Packing",
        user_role="Warehouse",
    )

    assert success is True

    success, message = transition_order_stage(
        order_id="ORD-1004",
        new_status="Packed",
        user_role="Warehouse",
    )

    assert success is True

    connection = get_connection()

    status = connection.execute(
        """
        SELECT status
        FROM orders
        WHERE order_id = ?
        """,
        ("ORD-1004",),
    ).fetchone()[0]

    connection.close()

    assert status == "Packed"