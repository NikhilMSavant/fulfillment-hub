import pandas as pd

from utils.calculations import (
    calculate_inventory_status,
    calculate_order_inventory_status,
    calculate_order_risk,
    calculate_pickup_risk,
    can_start_picking,
    verify_order_item,
    validate_stage_transition,
)


def test_verify_correct_item():
    result = verify_order_item(
        expected_sku="SKU-001",
        expected_product_name="Product 1",
        expected_variant="Blue / M",
        scanned_sku="SKU-001",
        scanned_product_name="Product 1",
        scanned_variant="Blue / M",
        verified_quantity=2,
        required_quantity=2,
    )

    assert result["is_valid"] is True
    assert result["status"] == "Correct item"


def test_verify_wrong_item():
    result = verify_order_item(
        expected_sku="SKU-001",
        expected_product_name="Product 1",
        expected_variant="Blue / M",
        scanned_sku="SKU-002",
        scanned_product_name="Product 2",
        scanned_variant="Red / L",
        verified_quantity=2,
        required_quantity=2,
    )

    assert result["is_valid"] is False
    assert result["status"] == "WRONG ITEM"


def test_verify_wrong_variant():
    result = verify_order_item(
        expected_sku="SKU-001",
        expected_product_name="Product 1",
        expected_variant="Blue / M",
        scanned_sku="SKU-001",
        scanned_product_name="Product 1",
        scanned_variant="Red / M",
        verified_quantity=2,
        required_quantity=2,
    )

    assert result["is_valid"] is False
    assert result["status"] == "WRONG VARIANT"


def test_verify_quantity_mismatch():
    result = verify_order_item(
        expected_sku="SKU-001",
        expected_product_name="Product 1",
        expected_variant="Blue / M",
        scanned_sku="SKU-001",
        scanned_product_name="Product 1",
        scanned_variant="Blue / M",
        verified_quantity=1,
        required_quantity=2,
    )

    assert result["is_valid"] is False
    assert result["status"] == "QUANTITY MISMATCH"

# --------------------------------------------------
# Existing calculation tests
# --------------------------------------------------

def test_inventory_available_quantity():
    inventory = pd.DataFrame(
        [
            {
                "sku": "SKU-001",
                "warehouse_id": "WH-MAIN",
                "quantity_on_hand": 10,
                "reserved_quantity": 3,
                "reorder_level": 5,
            }
        ]
    )

    result = calculate_inventory_status(inventory)

    assert result.iloc[0]["available_quantity"] == 7
    assert result.iloc[0]["status"] == "Available"


def test_order_risk_flags_delayed_order():
    orders = pd.DataFrame(
        [
            {
                "order_id": "ORD-TEST",
                "priority": False,
                "required_ship_datetime": "2026-10-01 09:00:00",
                "status": "Processed",
            }
        ]
    )

    result = calculate_order_risk(orders)

    assert bool(result.iloc[0]["is_delayed"]) is True


def test_pickup_risk_flags_overdue_pickup():
    shipments = pd.DataFrame(
        [
            {
                "order_id": "ORD-TEST",
                "pickup_datetime": "2026-09-30 15:00:00",
                "pickup_status": "Awaiting Pickup",
            }
        ]
    )

    result = calculate_pickup_risk(shipments)

    assert bool(result.iloc[0]["pickup_overdue"]) is True


# --------------------------------------------------
# Stage Transition Tests
# --------------------------------------------------

def test_valid_stage_transition():
    valid, message = validate_stage_transition(
        "Received",
        "Processed",
    )

    assert valid is True
    assert "Valid" in message


def test_invalid_stage_transition_cannot_skip_stage():
    valid, message = validate_stage_transition(
        "Received",
        "Picking",
    )

    assert valid is False
    assert "Invalid transition" in message


def test_shipped_order_cannot_move():
    valid, message = validate_stage_transition(
        "Shipped",
        "Received",
    )

    assert valid is False
    assert "Shipped" in message


# --------------------------------------------------
# Picking Stock Gate Tests
# --------------------------------------------------

def test_picking_allowed_when_main_stock_is_sufficient():
    valid, message = can_start_picking(
        required_quantity=5,
        main_available_quantity=5,
    )

    assert valid is True


def test_picking_blocked_when_main_stock_is_insufficient():
    valid, message = can_start_picking(
        required_quantity=5,
        main_available_quantity=2,
    )

    assert valid is False
    assert "main warehouse" in message.lower()
    assert "transfer" in message.lower()


# --------------------------------------------------
# Existing Inventory Logic Protection
# --------------------------------------------------

def test_order_inventory_status_preserves_transfer_required():
    orders = pd.DataFrame(
        [
            {
                "order_id": "ORD-1001",
                "status": "Processed",
            }
        ]
    )

    order_items = pd.DataFrame(
        [
            {
                "order_item_id": "OI-1",
                "order_id": "ORD-1001",
                "sku": "SKU-001",
                "quantity": 5,
            }
        ]
    )

    inventory = pd.DataFrame(
        [
            {
                "sku": "SKU-001",
                "warehouse_id": "WH-MAIN",
                "quantity_on_hand": 2,
                "reserved_quantity": 0,
                "reorder_level": 5,
            },
            {
                "sku": "SKU-001",
                "warehouse_id": "WH-SEC",
                "quantity_on_hand": 10,
                "reserved_quantity": 0,
                "reorder_level": 5,
            },
        ]
    )

    result = calculate_order_inventory_status(
        orders,
        order_items,
        inventory,
    )

    assert (
        result.iloc[0]["inventory_status"]
        == "Transfer Required"
    )

    assert result.iloc[0]["main_shortage"] == 3