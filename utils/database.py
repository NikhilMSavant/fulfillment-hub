import sqlite3
from pathlib import Path

import pandas as pd

from utils.calculations import (
    can_start_picking,
    validate_stage_transition,
    verify_order_item,
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
            return pd.read_sql_query(
                query,
                connection,
                params=(),
            )

        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )

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
        # Record transfer out
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
        # Record transfer in
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

        return (
            False,
            f"Transfer failed: {e}",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Adjust Inventory Count
# --------------------------------------------------

def adjust_inventory_count(
    sku,
    warehouse_id,
    counted_quantity,
    reason,
    user_role="Warehouse",
):
    """
    Correct system inventory to match a physical count.

    Returns:
        (success, message)
    """

    if counted_quantity < 0:
        return (
            False,
            "Counted quantity cannot be negative.",
        )

    if not reason or not reason.strip():
        return (
            False,
            "A reason is required for an inventory adjustment.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT quantity_on_hand
            FROM inventory
            WHERE sku = ?
              AND warehouse_id = ?
            """,
            (
                sku,
                warehouse_id,
            ),
        )

        inventory = cursor.fetchone()

        if inventory is None:
            return (
                False,
                f"Inventory record not found for "
                f"{sku} at {warehouse_id}.",
            )

        system_quantity = inventory[0]

        quantity_delta = (
            counted_quantity - system_quantity
        )

        if quantity_delta == 0:
            return (
                True,
                f"No adjustment required. "
                f"{sku} already has a quantity of "
                f"{system_quantity}.",
            )

        cursor.execute(
            """
            UPDATE inventory
            SET quantity_on_hand = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
              AND warehouse_id = ?
            """,
            (
                counted_quantity,
                sku,
                warehouse_id,
            ),
        )

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
                warehouse_id,
                "Inventory Adjustment",
                quantity_delta,
                "Inventory Count",
                f"{warehouse_id}:{sku}",
                reason.strip(),
                user_role,
            ),
        )

        reference_type = "Inventory"
        reference_id = f"{warehouse_id}:{sku}"

        cursor.execute(
            """
            SELECT exception_id
            FROM exceptions
            WHERE reference_type = ?
              AND reference_id = ?
              AND issue_type = 'Inventory Mismatch'
            """,
            (
                reference_type,
                reference_id,
            ),
        )

        existing_exception = cursor.fetchone()

        if existing_exception is None:
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
                exception_id = (
                    f"EXC-{latest_number + 1:04d}"
                )

            description = (
                f"Physical count mismatch for {sku} at "
                f"{warehouse_id}. System quantity: "
                f"{system_quantity}. Counted quantity: "
                f"{counted_quantity}."
            )

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
                    resolved_at,
                    reference_type,
                    reference_id
                )
                VALUES (
                    ?, NULL, ?, ?, ?, 'Open', ?,
                    CURRENT_TIMESTAMP, NULL, ?, ?
                )
                """,
                (
                    exception_id,
                    "Inventory Mismatch",
                    description,
                    "High",
                    "Warehouse",
                    reference_type,
                    reference_id,
                ),
            )

        connection.commit()

        return (
            True,
            f"Inventory for {sku} at {warehouse_id} "
            f"adjusted from {system_quantity} to "
            f"{counted_quantity}.",
        )

    except Exception as e:
        connection.rollback()

        return (
            False,
            f"Inventory adjustment failed: {e}",
        )

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

    Returns:
        (success, message)
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

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
            return (
                False,
                f"Order {order_id} was not found.",
            )

        current_status = order[0]

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

            for (
                sku,
                required_quantity,
                available_quantity,
            ) in order_items:

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
        # Staging location check
        # ----------------------------------------------

        if new_status == "Staged":
            cursor.execute(
                """
                SELECT
                    o.courier_id,
                    s.staging_location
                FROM orders o
                LEFT JOIN shipments s
                    ON o.order_id = s.order_id
                WHERE o.order_id = ?
                """,
                (order_id,),
            )

            staging = cursor.fetchone()

            if staging is None:
                return (
                    False,
                    f"Shipment information not found for {order_id}.",
                )

            courier_id, staging_location = staging

            if not staging_location:
                return (
                    False,
                    f"Cannot move {order_id} to Staged. "
                    f"Assign a staging bay first.",
                )

            cursor.execute(
                """
                SELECT bay_id
                FROM staging_bays
                WHERE bay_id = ?
                  AND courier_id = ?
                  AND active = 1
                """,
                (
                    staging_location,
                    courier_id,
                ),
            )

            valid_bay = cursor.fetchone()

            if valid_bay is None:
                return (
                    False,
                    f"Staging bay {staging_location} is not valid "
                    f"for courier {courier_id}.",
                )

        # ----------------------------------------------
        # Item verification check
        # ----------------------------------------------

        if new_status in {"Picked", "Packed"}:
            verification_stage = (
                "Picking"
                if new_status == "Picked"
                else "Packing"
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM order_items oi
                WHERE oi.order_id = ?
                  AND NOT EXISTS (
                      SELECT 1
                      FROM order_item_verifications v
                      WHERE v.order_item_id = oi.order_item_id
                        AND v.stage = ?
                  )
                """,
                (
                    order_id,
                    verification_stage,
                ),
            )

            unverified_count = cursor.fetchone()[0]

            if unverified_count > 0:
                return (
                    False,
                    f"Cannot move {order_id} to {new_status}. "
                    f"{unverified_count} order item(s) still need "
                    f"successful {verification_stage} verification.",
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
            (
                new_status,
                order_id,
            ),
        )

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

        return (
            False,
            f"Stage transition failed: {e}",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Assign Staging Bay
# --------------------------------------------------

def assign_staging_bay(
    order_id,
    bay_id,
    user_role="Warehouse",
):
    """
    Assign a packed order to a valid staging bay.

    The bay must belong to the order's courier.

    Returns:
        (success, message)
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                o.status,
                o.courier_id
            FROM orders o
            WHERE o.order_id = ?
            """,
            (order_id,),
        )

        order = cursor.fetchone()

        if order is None:
            return (
                False,
                f"Order {order_id} was not found.",
            )

        current_status, courier_id = order

        if current_status != "Packed":
            return (
                False,
                f"{order_id} must be Packed before "
                f"a staging bay can be assigned.",
            )

        cursor.execute(
            """
            SELECT bay_id
            FROM staging_bays
            WHERE bay_id = ?
              AND courier_id = ?
              AND active = 1
            """,
            (
                bay_id,
                courier_id,
            ),
        )

        bay = cursor.fetchone()

        if bay is None:
            return (
                False,
                f"Staging bay {bay_id} is not valid "
                f"for courier {courier_id}.",
            )

        cursor.execute(
            """
            SELECT shipment_id
            FROM shipments
            WHERE order_id = ?
            """,
            (order_id,),
        )

        shipment = cursor.fetchone()

        if shipment is None:
            return (
                False,
                f"Shipment record not found for {order_id}.",
            )

        cursor.execute(
            """
            UPDATE shipments
            SET staging_location = ?
            WHERE order_id = ?
            """,
            (
                bay_id,
                order_id,
            ),
        )

        connection.commit()

        return (
            True,
            f"{order_id} assigned to staging bay {bay_id}.",
        )

    except Exception as e:
        connection.rollback()

        return (
            False,
            f"Staging bay assignment failed: {e}",
        )

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

        cursor.execute(
            """
            SELECT exception_id, status
            FROM exceptions
            WHERE order_id = ?
              AND issue_type = ?
            """,
            (
                order_id,
                issue_type,
            ),
        )

        existing = cursor.fetchone()

        if existing is not None:
            return (
                False,
                f"Exception already exists for {order_id}: "
                f"{issue_type}.",
                existing[0],
            )

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
            exception_id = (
                f"EXC-{latest_number + 1:04d}"
            )

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
                ?, ?, ?, ?, ?, 'Open', ?,
                CURRENT_TIMESTAMP, NULL
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
# Process Courier Pickup
# --------------------------------------------------

def process_courier_pickup(
    courier_id,
    handed_over_order_ids,
    user_role="Warehouse",
):
    """
    Process a courier pickup.

    Only explicitly handed-over staged boxes are shipped.

    Boxes that remain staged receive a
    Courier Pickup Missed exception.

    Returns:
        (success, message)
    """

    handed_over_order_ids = set(
        handed_over_order_ids or []
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                o.order_id,
                o.status,
                s.staging_location
            FROM orders o
            INNER JOIN shipments s
                ON o.order_id = s.order_id
            WHERE o.courier_id = ?
              AND o.status = 'Staged'
              AND s.staging_location IS NOT NULL
              AND s.staging_location != ''
            ORDER BY o.required_ship_datetime
            """,
            (courier_id,),
        )

        staged_orders = cursor.fetchall()

        if not staged_orders:
            return (
                False,
                f"No staged orders are waiting for courier {courier_id}.",
            )

        staged_order_ids = {
            row[0]
            for row in staged_orders
        }

        invalid_orders = (
            handed_over_order_ids - staged_order_ids
        )

        if invalid_orders:
            invalid_list = ", ".join(
                sorted(invalid_orders)
            )

            return (
                False,
                f"These orders are not currently staged "
                f"for courier {courier_id}: {invalid_list}",
            )

        shipped_count = 0
        missed_count = 0

        for (
            order_id,
            current_status,
            staging_location,
        ) in staged_orders:

            if order_id in handed_over_order_ids:

                cursor.execute(
                    """
                    UPDATE orders
                    SET status = 'Awaiting Pickup'
                    WHERE order_id = ?
                    """,
                    (order_id,),
                )

                cursor.execute(
                    """
                    INSERT INTO order_events (
                        order_id,
                        from_status,
                        to_status,
                        user_role,
                        note
                    )
                    VALUES (?, 'Staged', 'Awaiting Pickup', ?, ?)
                    """,
                    (
                        order_id,
                        user_role,
                        f"Courier {courier_id} pickup initiated "
                        f"from staging bay {staging_location}.",
                    ),
                )

                cursor.execute(
                    """
                    UPDATE orders
                    SET status = 'Shipped'
                    WHERE order_id = ?
                    """,
                    (order_id,),
                )

                cursor.execute(
                    """
                    INSERT INTO order_events (
                        order_id,
                        from_status,
                        to_status,
                        user_role,
                        note
                    )
                    VALUES (?, 'Awaiting Pickup', 'Shipped', ?, ?)
                    """,
                    (
                        order_id,
                        user_role,
                        f"Handed over to courier {courier_id}.",
                    ),
                )

                cursor.execute(
                    """
                    UPDATE shipments
                    SET pickup_status = 'Picked Up',
                        pickup_datetime = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                    """,
                    (order_id,),
                )

                shipped_count += 1

            else:

                cursor.execute(
                    """
                    SELECT exception_id
                    FROM exceptions
                    WHERE order_id = ?
                      AND issue_type = 'Courier Pickup Missed'
                    """,
                    (order_id,),
                )

                existing_exception = cursor.fetchone()

                if existing_exception is None:

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
                        exception_id = (
                            f"EXC-{latest_number + 1:04d}"
                        )

                    description = (
                        f"Courier {courier_id} pickup completed "
                        f"without collecting {order_id}. "
                        f"Box remains in staging bay "
                        f"{staging_location}."
                    )

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
                            ?, ?, ?, ?, ?, 'Open', ?,
                            CURRENT_TIMESTAMP, NULL
                        )
                        """,
                        (
                            exception_id,
                            order_id,
                            "Courier Pickup Missed",
                            description,
                            "High",
                            "Warehouse",
                        ),
                    )

                missed_count += 1

        connection.commit()

        return (
            True,
            f"Courier {courier_id} pickup processed. "
            f"{shipped_count} box(es) handed over; "
            f"{missed_count} box(es) remain staged and flagged.",
        )

    except Exception as e:
        connection.rollback()

        return (
            False,
            f"Courier pickup failed: {e}",
        )

    finally:
        connection.close()


# --------------------------------------------------
# Verify Order Item
# --------------------------------------------------

def verify_order_item_in_db(
    order_item_id,
    scanned_sku,
    scanned_product_name,
    scanned_variant,
    verified_quantity,
    stage,
    user_role="Warehouse",
):
    """
    Verify one order item against product master data
    and store the successful verification.

    The same item can be verified once at Picking
    and once at Packing, but repeated verification
    at the same stage is not recorded again.
    """

    valid_stages = {
        "Picking",
        "Packing",
    }

    if stage not in valid_stages:
        return (
            False,
            "Verification is only allowed during "
            "Picking or Packing.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                oi.order_id,
                oi.sku,
                oi.quantity,
                p.product_name,
                p.variant
            FROM order_items oi
            JOIN products p
                ON oi.sku = p.sku
            WHERE oi.order_item_id = ?
            """,
            (order_item_id,),
        )

        item = cursor.fetchone()

        if item is None:
            return (
                False,
                f"Order item {order_item_id} was not found.",
            )

        (
            order_id,
            expected_sku,
            required_quantity,
            expected_product_name,
            expected_variant,
        ) = item

        result = verify_order_item(
            expected_sku=expected_sku,
            expected_product_name=expected_product_name,
            expected_variant=expected_variant,
            scanned_sku=scanned_sku,
            scanned_product_name=scanned_product_name,
            scanned_variant=scanned_variant,
            verified_quantity=verified_quantity,
            required_quantity=required_quantity,
        )

        if not result["is_valid"]:

            if result["status"] in {
                "WRONG ITEM",
                "WRONG VARIANT",
            }:
                create_exception(
                    order_id=order_id,
                    issue_type="Variant Mismatch",
                    description=result["message"],
                    priority="High",
                    owner=user_role,
                )

            return (
                False,
                result["message"],
            )

        # Prevent duplicate successful verification
        # for the same item at the same stage.
        cursor.execute(
            """
            SELECT verification_id
            FROM order_item_verifications
            WHERE order_item_id = ?
              AND stage = ?
            ORDER BY verification_id DESC
            LIMIT 1
            """,
            (
                order_item_id,
                stage,
            ),
        )

        existing_verification = cursor.fetchone()

        if existing_verification is not None:
            return (
                True,
                "Item was already verified for this stage.",
            )

        cursor.execute(
            """
            INSERT INTO order_item_verifications (
                order_item_id,
                stage,
                verified_sku,
                verified_product_name,
                verified_variant,
                verified_quantity,
                user_role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_item_id,
                stage,
                scanned_sku,
                scanned_product_name,
                scanned_variant,
                verified_quantity,
                user_role,
            ),
        )

        connection.commit()

        return (
            True,
            "Item and quantity verified successfully.",
        )

    except Exception:
        connection.rollback()
        raise

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
                (
                    new_status,
                    exception_id,
                ),
            )

        else:
            cursor.execute(
                """
                UPDATE exceptions
                SET status = ?,
                    resolved_at = NULL
                WHERE exception_id = ?
                """,
                (
                    new_status,
                    exception_id,
                ),
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