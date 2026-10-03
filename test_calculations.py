import pandas as pd

from utils.calculations import (
    calculate_inventory_status,
    calculate_order_risk,
    calculate_pickup_risk,
    calculate_order_inventory_status,
)


# --------------------------------------------------
# Load generated data
# --------------------------------------------------

inventory_df = pd.read_csv("data/inventory.csv")
orders_df = pd.read_csv("data/orders.csv")
order_items_df = pd.read_csv("data/order_items.csv")
shipments_df = pd.read_csv("data/shipments.csv")


# --------------------------------------------------
# Test 1: Inventory
# --------------------------------------------------

inventory_result = calculate_inventory_status(
    inventory_df
)

print("\n--- INVENTORY TEST ---")

print(
    inventory_result[
        inventory_result["sku"].isin(
            ["SKU-001", "SKU-002", "SKU-003"]
        )
    ][
        [
            "sku",
            "warehouse_id",
            "quantity_on_hand",
            "reserved_quantity",
            "available_quantity",
            "status",
        ]
    ].to_string(index=False)
)


# --------------------------------------------------
# Test 2: Order Risk
# --------------------------------------------------

order_risk_result = calculate_order_risk(
    orders_df
)

print("\n--- ORDER RISK TEST ---")

print(
    order_risk_result[
        order_risk_result["order_id"].isin(
            [
                "ORD-1001",
                "ORD-1002",
                "ORD-1003",
                "ORD-1004",
                "ORD-1005",
            ]
        )
    ][
        [
            "order_id",
            "priority",
            "required_ship_datetime",
            "status",
            "is_delayed",
            "is_priority_at_risk",
        ]
    ].to_string(index=False)
)


# --------------------------------------------------
# Test 3: Pickup Risk
# --------------------------------------------------

pickup_result = calculate_pickup_risk(
    shipments_df
)

print("\n--- PICKUP TEST ---")

print(
    pickup_result[
        pickup_result["order_id"].isin(
            ["ORD-1010"]
        )
    ][
        [
            "order_id",
            "courier_id",
            "pickup_datetime",
            "pickup_status",
            "pickup_overdue",
        ]
    ].to_string(index=False)
)


# --------------------------------------------------
# Test 4: Order Inventory
# --------------------------------------------------

order_inventory_result = calculate_order_inventory_status(
    orders_df,
    order_items_df,
    inventory_df,
)

print("\n--- ORDER INVENTORY TEST ---")

print(
    order_inventory_result[
        order_inventory_result["order_id"].isin(
            [
                "ORD-1001",
                "ORD-1002",
                "ORD-1003",
            ]
        )
    ][
        [
            "order_id",
            "inventory_status",
            "main_shortage",
            "inventory_shortage",
        ]
    ].to_string(index=False)
)