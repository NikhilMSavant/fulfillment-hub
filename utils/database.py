import sqlite3
from pathlib import Path
import pandas as pd

from utils.calculations import (
    can_start_picking,
    validate_stage_transition,
)


# --------------------------------------------------
# Database Path
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "fulfillment_hub.db"


# --------------------------------------------------
# Database Connection
# --------------------------------------------------

def get_connection():
    """Create and return a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


# --------------------------------------------------
# Run Query
# --------------------------------------------------

def run_query(query, params=None):
    """Run a SQL query and return the result as a DataFrame."""

    connection = get_connection()

    try:
        if params is None:
            return pd.read_sql_query(query, connection, params=())
        else:
            return pd.read_sql_query(query, connection, params=params)

    finally:
        connection.close()


# --------------------------------------------------
# Transfer Stock
# --------------------------------------------------

def transfer_stock(
    sku,
    quantity,
    user_role="Warehouse",
    reason="Operational stock transfer",
):
    """
    Transfer stock for a SKU from the secondary warehouse
    to the main warehouse.

    The transfer is atomic:
    - Secondary warehouse decreases.
    - Main warehouse increases.
    - Two stock movement audit records are created.

    Returns:
        (success, message)
    """

    if quantity <= 0:
        return (
            False,
            "Transfer quantity must be greater than zero.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------
        # Get secondary warehouse stock
        # ----------------------------------------------

        cursor.execute(
            """
            SELECT quantity_on_hand, reserved_quantity
            FROM inventory
            WHERE sku = ?
              AND warehouse_id = 'WH-SEC'
            """,
            (sku,),
        )

        secondary = cursor.fetchone()

        if secondary is None:
            return (
                False,
                "Secondary warehouse stock record not found.",
            )

        secondary_on_hand, secondary_reserved = secondary

        secondary_available = (
            secondary_on_hand - secondary_reserved
        )

        if quantity > secondary_available:
            return (
                False,
                f"Only {secondary_available} units are "
                f"available for transfer from the "
                f"secondary warehouse.",
            )

        # ----------------------------------------------
        # Verify main warehouse record
        # ----------------------------------------------

        cursor.execute(
            """
            SELECT quantity_on_hand
            FROM inventory
            WHERE sku = ?
              AND warehouse_id = 'WH-MAIN'
            """,
            (sku,),
        )

        main = cursor.fetchone()

        if main is None:
            return (
                False,
                "Main warehouse stock record not found.",
            )

        # ----------------------------------------------
        # Update secondary warehouse
        # ----------------------------------------------

        cursor.execute(
            """
            UPDATE inventory
            SET quantity_on_hand = quantity_on_hand - ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
              AND warehouse_id = 'WH-SEC'
            """,
            (quantity, sku),
        )

        # ----------------------------------------------
        # Update main warehouse
        # ----------------------------------------------

        cursor.execute(
            """
            UPDATE inventory
            SET quantity_on_hand = quantity_on_hand + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
              AND warehouse_id = 'WH-MAIN'
            """,
            (quantity, sku),
        )

        # ----------------------------------------------
        # Audit: secondary warehouse
        # ----------------------------------------------

        cursor.execute(
            """
            INSERT INTO stock_movements (
                sku,
                warehouse_id,
                movement_type,
                quantity_delta,
                reference_type,
                reference_id,
                reason,
                user_role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku,
                "WH-SEC",
                "Transfer Out",
                -quantity,
                "Stock Transfer",
                sku,
                reason,
                user_role,
            ),
        )

        # ----------------------------------------------
        # Audit: main warehouse
        # ----------------------------------------------

        cursor.execute(
            """
            INSERT INTO stock_movements (
                sku,
                warehouse_id,
                movement_type,
                quantity_delta,
                reference_type,
                reference_id,
                reason,
                user_role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku,
                "WH-MAIN",
                "Transfer In",
                quantity,
                "Stock Transfer",
                sku,
                reason,
                user_role,
            ),
        )

        connection.commit()

        return (
            True,
            f"Successfully transferred {quantity} unit(s) "
            f"of {sku} from WH-SEC to WH-MAIN.",
        )

    except Exception as e:

        connection.rollback()

        return False, f"Transfer failed: {e}"

    finally:

        connection.close()


# --------------------------------------------------
# Transition Order Stage
# --------------------------------------------------

def transition_order_stage(
    order_id,
    new_status,
    user_role="Warehouse",
    note=None,
):
    """
    Move an order to the next valid fulfillment stage.

    Rules:
    - Only immediate next-stage transitions are allowed.
    - Starting Picking is blocked when the main warehouse
      does not have enough available stock.
    - Every successful transition creates an order_events
      audit record.
    - Order update and audit event are atomic.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------
        # Get current order
        # ----------------------------------------------

        cursor.execute(
            """
            SELECT status
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        )

        order = cursor.fetchone()

        if order is None:
            return False, f"Order {order_id} was not found."

        current_status = order[0]

        # ----------------------------------------------
        # Validate stage transition
        # ----------------------------------------------

        is_valid, transition_message = validate_stage_transition(
            current_status,
            new_status,
        )

        if not is_valid:
            return False, transition_message

        # ----------------------------------------------
        # Picking stock check
        # ----------------------------------------------

        if new_status == "Picking":

            cursor.execute(
                """
                SELECT
                    oi.sku,
                    oi.quantity,
                    COALESCE(
                        i.quantity_on_hand - i.reserved_quantity,
                        0
                    ) AS available_quantity
                FROM order_items oi
                LEFT JOIN inventory i
                    ON oi.sku = i.sku
                    AND i.warehouse_id = 'WH-MAIN'
                WHERE oi.order_id = ?
                """,
                (order_id,),
            )

            order_items = cursor.fetchall()

            if not order_items:
                return (
                    False,
                    f"No order items found for {order_id}.",
                )

            for sku, required_quantity, available_quantity in order_items:

                allowed, stock_message = can_start_picking(
                    required_quantity,
                    available_quantity,
                )

                if not allowed:
                    return (
                        False,
                        f"Cannot start Picking for {order_id}. "
                        f"SKU {sku}: {stock_message}",
                    )

        # ----------------------------------------------
        # Update order status
        # ----------------------------------------------

        cursor.execute(
            """
            UPDATE orders
            SET status = ?
            WHERE order_id = ?
            """,
            (new_status, order_id),
        )

        # ----------------------------------------------
        # Create audit event
        # ----------------------------------------------

        cursor.execute(
            """
            INSERT INTO order_events (
                order_id,
                from_status,
                to_status,
                user_role,
                note
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id,
                current_status,
                new_status,
                user_role,
                note,
            ),
        )

        connection.commit()

        return (
            True,
            f"{order_id} moved from "
            f"{current_status} to {new_status}.",
        )

    except Exception as e:

        connection.rollback()

        return False, f"Stage transition failed: {e}"

    finally:

        connection.close()


# --------------------------------------------------
# Create Exception
# --------------------------------------------------

def create_exception(
    order_id,
    issue_type,
    description,
    priority="Medium",
    owner="Warehouse",
):
    """
    Create an operational exception.

    Duplicate exceptions for the same order and issue type
    are prevented.

    Returns:
        (success, message, exception_id)
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------
        # Check for an existing exception
        # ----------------------------------------------

        cursor.execute(
            """
            SELECT exception_id, status
            FROM exceptions
            WHERE order_id = ?
              AND issue_type = ?
            """,
            (order_id, issue_type),
        )

        existing = cursor.fetchone()

        if existing is not None:
            return (
                False,
                f"Exception already exists for {order_id}: "
                f"{issue_type}.",
                existing[0],
            )

        # ----------------------------------------------
        # Generate exception ID
        # ----------------------------------------------

        cursor.execute(
            """
            SELECT exception_id
            FROM exceptions
            ORDER BY exception_id DESC
            LIMIT 1
            """
        )

        latest = cursor.fetchone()

        if latest is None:
            exception_id = "EXC-0001"
        else:
            latest_number = int(
                latest[0].replace("EXC-", "")
            )
            exception_id = f"EXC-{latest_number + 1:04d}"

        # ----------------------------------------------
        # Insert exception
        # ----------------------------------------------

        cursor.execute(
            """
            INSERT INTO exceptions (
                exception_id,
                order_id,
                issue_type,
                description,
                priority,
                status,
                owner,
                created_at,
                resolved_at
            )
            VALUES (
                ?, ?, ?, ?, ?, 'Open', ?, CURRENT_TIMESTAMP, NULL
            )
            """,
            (
                exception_id,
                order_id,
                issue_type,
                description,
                priority,
                owner,
            ),
        )

        connection.commit()

        return (
            True,
            f"Exception {exception_id} created.",
            exception_id,
        )

    except Exception as e:

        connection.rollback()

        return (
            False,
            f"Exception creation failed: {e}",
            None,
        )

    finally:

        connection.close()


# --------------------------------------------------
# Update Exception Status
# --------------------------------------------------

def update_exception_status(
    exception_id,
    new_status,
):
    """
    Update an exception's workflow status.

    Valid statuses:
        Open
        In Progress
        Resolved

    resolved_at is automatically managed.
    """

    valid_statuses = {
        "Open",
        "In Progress",
        "Resolved",
    }

    if new_status not in valid_statuses:
        return (
            False,
            f"Invalid exception status: {new_status}.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT status
            FROM exceptions
            WHERE exception_id = ?
            """,
            (exception_id,),
        )

        existing = cursor.fetchone()

        if existing is None:
            return (
                False,
                f"Exception {exception_id} was not found.",
            )

        if new_status == "Resolved":

            cursor.execute(
                """
                UPDATE exceptions
                SET status = ?,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE exception_id = ?
                """,
                (new_status, exception_id),
            )

        else:

            cursor.execute(
                """
                UPDATE exceptions
                SET status = ?,
                    resolved_at = NULL
                WHERE exception_id = ?
                """,
                (new_status, exception_id),
            )

        connection.commit()

        return (
            True,
            f"Exception {exception_id} updated to {new_status}.",
        )

    except Exception as e:

        connection.rollback()

        return (
            False,
            f"Exception update failed: {e}",
        )

    finally:

        connection.close()