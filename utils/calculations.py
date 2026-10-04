import pandas as pd


# --------------------------------------------------
# Fulfillment Workflow Rules
# --------------------------------------------------

FULFILLMENT_STAGES = [
    "Received",
    "Processed",
    "Picking",
    "Picked",
    "Packing",
    "Packed",
    "Staged",
    "Awaiting Pickup",
    "Shipped",
]

VALID_STAGE_TRANSITIONS = {
    "Received": "Processed",
    "Processed": "Picking",
    "Picking": "Picked",
    "Picked": "Packing",
    "Packing": "Packed",
    "Packed": "Staged",
    "Staged": "Awaiting Pickup",
    "Awaiting Pickup": "Shipped",
}


def validate_stage_transition(current_status, new_status):
    """
    Validate that an order moves only to the next
    allowed fulfillment stage.

    Returns:
        (is_valid, message)
    """

    if current_status not in FULFILLMENT_STAGES:
        return (
            False,
            f"Unknown current fulfillment stage: {current_status}",
        )

    if new_status not in FULFILLMENT_STAGES:
        return (
            False,
            f"Unknown target fulfillment stage: {new_status}",
        )

    if current_status == "Shipped":
        return (
            False,
            "Shipped orders cannot move to another fulfillment stage.",
        )

    expected_next = VALID_STAGE_TRANSITIONS.get(current_status)

    if new_status != expected_next:
        return (
            False,
            f"Invalid transition: {current_status} → {new_status}. "
            f"The next allowed stage is {expected_next}.",
        )

    return True, "Valid fulfillment stage transition."


def can_start_picking(
    required_quantity,
    main_available_quantity,
):
    """
    Determine whether an order line can enter Picking.

    Picking is allowed only when the main warehouse
    has enough available stock.
    """

    if required_quantity <= 0:
        return (
            False,
            "Required quantity must be greater than zero.",
        )

    if main_available_quantity < required_quantity:
        return (
            False,
            "Picking is blocked because the main warehouse "
            "does not have enough available stock. "
            "Transfer stock to the main warehouse first.",
        )

    return True, "Main warehouse has enough stock for picking."


def verify_order_item(
    expected_sku,
    expected_product_name,
    expected_variant,
    scanned_sku,
    scanned_product_name,
    scanned_variant,
    verified_quantity,
    required_quantity,
):
    """
    Verify a picked/packed item against the expected order line.

    Returns:
        dict containing verification status and message.
    """

    if scanned_sku != expected_sku:
        return {
            "status": "WRONG ITEM",
            "is_valid": False,
            "message": (
                f"Wrong item. Expected SKU {expected_sku}, "
                f"but received SKU {scanned_sku}."
            ),
        }

    if scanned_product_name != expected_product_name:
        return {
            "status": "WRONG ITEM",
            "is_valid": False,
            "message": (
                f"Wrong item. Expected product "
                f"'{expected_product_name}', "
                f"but received '{scanned_product_name}'."
            ),
        }

    if scanned_variant != expected_variant:
        return {
            "status": "WRONG VARIANT",
            "is_valid": False,
            "message": (
                f"Wrong variant. Expected "
                f"'{expected_variant}', "
                f"but received '{scanned_variant}'."
            ),
        }

    if verified_quantity != required_quantity:
        return {
            "status": "QUANTITY MISMATCH",
            "is_valid": False,
            "message": (
                f"Quantity mismatch. Expected "
                f"{required_quantity}, "
                f"but verified {verified_quantity}."
            ),
        }

    return {
        "status": "Correct item",
        "is_valid": True,
        "message": "Item and quantity verified successfully.",
    }


# --------------------------------------------------
# Inventory Calculations
# --------------------------------------------------

def calculate_inventory_status(inventory_df):
    """
    Calculate available inventory and inventory status.

    Available stock = quantity_on_hand - reserved_quantity
    """

    inventory = inventory_df.copy()

    inventory["available_quantity"] = (
        inventory["quantity_on_hand"]
        - inventory["reserved_quantity"]
    )

    inventory["status"] = "Available"

    inventory.loc[
        inventory["available_quantity"] <= 0,
        "status"
    ] = "Out of Stock"

    inventory.loc[
        (inventory["available_quantity"] > 0)
        & (
            inventory["available_quantity"]
            <= inventory["reorder_level"]
        ),
        "status"
    ] = "Low Stock"

    return inventory


# --------------------------------------------------
# Order Risk Calculations
# --------------------------------------------------

def calculate_order_risk(orders_df):
    """
    Identify delayed and priority-at-risk orders.
    """

    orders = orders_df.copy()

    reference_now = pd.Timestamp("2026-10-01 12:00:00")

    orders["required_ship_datetime"] = pd.to_datetime(
        orders["required_ship_datetime"]
    )

    # --------------------------------------------------
    # Delayed
    # --------------------------------------------------

    orders["is_delayed"] = (
        (orders["required_ship_datetime"] < reference_now)
        & (orders["status"] != "Shipped")
        & (orders["status"] != "Cancelled")
    )

    # --------------------------------------------------
    # Priority order at risk
    # --------------------------------------------------

    time_remaining = (
        orders["required_ship_datetime"] - reference_now
    ).dt.total_seconds() / 3600

    orders["is_priority_at_risk"] = (
        (orders["priority"] == True)
        & (orders["status"] != "Shipped")
        & (orders["status"] != "Cancelled")
        & (time_remaining <= 4)
        & (time_remaining >= 0)
    )

    return orders


# --------------------------------------------------
# Pickup Risk Calculations
# --------------------------------------------------

def calculate_pickup_risk(shipments_df):
    """
    Identify shipments whose scheduled pickup time
    has already passed.
    """

    shipments = shipments_df.copy()

    reference_now = pd.Timestamp("2026-10-01 12:00:00")

    shipments["pickup_datetime"] = pd.to_datetime(
        shipments["pickup_datetime"],
        errors="coerce"
    )

    shipments["pickup_overdue"] = (
        (shipments["pickup_status"] == "Awaiting Pickup")
        & (shipments["pickup_datetime"] < reference_now)
    )

    return shipments


# --------------------------------------------------
# Order Inventory Check
# --------------------------------------------------

def calculate_order_inventory_status(
    orders_df,
    order_items_df,
    inventory_df
):
    """
    Compare each order's required quantity with
    available stock in the main and secondary warehouses.

    Inventory status:
    - Ready: Main warehouse can fulfill the order.
    - Transfer Required: Main warehouse is short,
      but secondary warehouse can cover the shortage.
    - Insufficient Stock: Combined stock is not enough.
    """

    inventory = calculate_inventory_status(inventory_df)

    # --------------------------------------------------
    # Separate Main and Secondary Warehouse Stock
    # --------------------------------------------------

    main_inventory = inventory[
        inventory["warehouse_id"] == "WH-MAIN"
    ][
        ["sku", "available_quantity"]
    ].rename(
        columns={
            "available_quantity": "main_available"
        }
    )

    secondary_inventory = inventory[
        inventory["warehouse_id"] == "WH-SEC"
    ][
        ["sku", "available_quantity"]
    ].rename(
        columns={
            "available_quantity": "secondary_available"
        }
    )

    # --------------------------------------------------
    # Add Inventory to Order Items
    # --------------------------------------------------

    items = order_items_df.copy()

    items = items.merge(
        main_inventory,
        on="sku",
        how="left"
    )

    items = items.merge(
        secondary_inventory,
        on="sku",
        how="left"
    )

    items["main_available"] = (
        items["main_available"].fillna(0)
    )

    items["secondary_available"] = (
        items["secondary_available"].fillna(0)
    )

    # --------------------------------------------------
    # Calculate Shortage
    # --------------------------------------------------

    items["main_shortage"] = (
        items["quantity"] - items["main_available"]
    ).clip(lower=0)

    items["total_available"] = (
        items["main_available"]
        + items["secondary_available"]
    )

    # --------------------------------------------------
    # Determine Item-Level Status
    # --------------------------------------------------

    items["inventory_status"] = "Ready"

    items.loc[
        items["main_shortage"] > 0,
        "inventory_status"
    ] = "Transfer Required"

    items.loc[
        items["total_available"] < items["quantity"],
        "inventory_status"
    ] = "Insufficient Stock"

    # --------------------------------------------------
    # Determine Order-Level Status
    # --------------------------------------------------

    status_priority = {
        "Ready": 0,
        "Transfer Required": 1,
        "Insufficient Stock": 2,
    }

    items["status_priority"] = (
        items["inventory_status"]
        .map(status_priority)
    )

    order_inventory = (
        items.groupby("order_id")
        .agg(
            inventory_status=(
                "status_priority",
                "max"
            ),
            main_shortage=(
                "main_shortage",
                "sum"
            ),
        )
        .reset_index()
    )

    reverse_status = {
        0: "Ready",
        1: "Transfer Required",
        2: "Insufficient Stock",
    }

    order_inventory["inventory_status"] = (
        order_inventory["inventory_status"]
        .map(reverse_status)
    )

    # --------------------------------------------------
    # Merge Back to Orders
    # --------------------------------------------------

    orders = orders_df.merge(
        order_inventory[
            [
                "order_id",
                "inventory_status",
                "main_shortage",
            ]
        ],
        on="order_id",
        how="left"
    )

    orders["inventory_status"] = (
        orders["inventory_status"]
        .fillna("Ready")
    )

    orders["main_shortage"] = (
        orders["main_shortage"]
        .fillna(0)
    )

    orders["inventory_shortage"] = (
        orders["inventory_status"]
        != "Ready"
    )

    return orders