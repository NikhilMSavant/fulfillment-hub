import random
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Product Data
# --------------------------------------------------

def generate_products():
    products = []

    product_templates = [
        (
            "Stainless Steel Bottle",
            "Drinkware",
            ["Black - 500ml", "Black - 750ml", "White - 500ml", "White - 750ml"],
        ),
        (
            "Canvas Tote Bag",
            "Bags",
            ["Natural - Small", "Natural - Large", "Black - Small", "Black - Large"],
        ),
        (
            "Bamboo Serving Tray",
            "Home",
            ["Small", "Medium", "Large", "Extra Large"],
        ),
        (
            "Soy Candle",
            "Home Decor",
            ["Vanilla - 150g", "Vanilla - 250g", "Lavender - 150g", "Lavender - 250g"],
        ),
        (
            "Jute Storage Basket",
            "Storage",
            ["Small", "Medium", "Large", "Extra Large"],
        ),
        (
            "Ceramic Mug",
            "Drinkware",
            ["Black - 250ml", "Black - 350ml", "White - 250ml", "White - 350ml"],
        ),
        (
            "Wooden Planter",
            "Home Decor",
            ["Small", "Medium", "Large", "Extra Large"],
        ),
        (
            "Cotton Pouch",
            "Accessories",
            ["Black - Small", "Black - Large", "Natural - Small", "Natural - Large"],
        ),
        (
            "Desk Organizer",
            "Office",
            ["Black - Small", "Black - Large", "White - Small", "White - Large"],
        ),
        (
            "Eco Gift Box",
            "Gifts",
            ["Small", "Medium", "Large", "Premium"],
        ),
    ]

    product_id = 1

    for product_name, category, variants in product_templates:
        for variant in variants:
            products.append(
                {
                    "product_id": f"P{product_id:03d}",
                    "sku": f"SKU-{product_id:03d}",
                    "product_name": product_name,
                    "category": category,
                    "variant": variant,
                    "unit_price": random.choice(
                        [299, 399, 499, 599, 699, 799, 999]
                    ),
                }
            )

            product_id += 1

    products_df = pd.DataFrame(products)

    output_path = DATA_DIR / "products.csv"
    products_df.to_csv(output_path, index=False)

    print(f"Created {len(products_df)} products")
    print(f"Saved to: {output_path}")

    return products_df


# --------------------------------------------------
# Inventory Data
# --------------------------------------------------

def generate_inventory(products_df):
    inventory = []

    warehouses = ["WH-MAIN", "WH-SEC"]

    for _, product in products_df.iterrows():
        sku = product["sku"]

        for warehouse_id in warehouses:
            quantity_on_hand = random.randint(5, 30)
            reserved_quantity = random.randint(
                0,
                min(5, quantity_on_hand),
            )
            reorder_level = random.randint(5, 10)

            # Simple warehouse-friendly shelf/bin location.
            # Main warehouse uses A-prefix locations.
            # Secondary warehouse uses S-prefix locations.
            shelf_prefix = (
                "A"
                if warehouse_id == "WH-MAIN"
                else "S"
            )

            shelf_location = (
                f"{shelf_prefix}-"
                f"{random.randint(1, 12):02d}-"
                f"{random.randint(1, 4):02d}"
            )

            inventory.append(
                {
                    "inventory_id": (
                        f"INV-{len(inventory) + 1:03d}"
                    ),
                    "sku": sku,
                    "warehouse_id": warehouse_id,
                    "quantity_on_hand": quantity_on_hand,
                    "reserved_quantity": reserved_quantity,
                    "reorder_level": reorder_level,
                    "shelf_location": shelf_location,
                    "last_updated": "2026-09-30 10:00:00",
                }
            )

    inventory_df = pd.DataFrame(inventory)

    # --------------------------------------------------
    # Deliberate demo scenarios
    # --------------------------------------------------

    # Scenario 1:
    # Main warehouse has insufficient stock,
    # but secondary warehouse has enough stock.
    inventory_df.loc[
        0,
        "quantity_on_hand",
    ] = 2

    inventory_df.loc[
        0,
        "reserved_quantity",
    ] = 0

    inventory_df.loc[
        1,
        "quantity_on_hand",
    ] = 10

    inventory_df.loc[
        1,
        "reserved_quantity",
    ] = 0

    # Scenario 2:
    # Both warehouses have insufficient stock.
    inventory_df.loc[
        2,
        "quantity_on_hand",
    ] = 2

    inventory_df.loc[
        2,
        "reserved_quantity",
    ] = 0

    inventory_df.loc[
        3,
        "quantity_on_hand",
    ] = 1

    inventory_df.loc[
        3,
        "reserved_quantity",
    ] = 0

    # Scenario 3:
    # Reserved stock example.
    inventory_df.loc[
        4,
        "quantity_on_hand",
    ] = 15

    inventory_df.loc[
        4,
        "reserved_quantity",
    ] = 5

    output_path = DATA_DIR / "inventory.csv"

    inventory_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(inventory_df)} inventory records"
    )

    print(
        f"Saved to: {output_path}"
    )

    return inventory_df


# --------------------------------------------------
# Order Data
# --------------------------------------------------

def generate_orders():
    orders = []

    channels = [
        "Website",
        "Marketplace A",
        "Marketplace B",
    ]

    statuses = [
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

    reference_now = pd.Timestamp("2026-10-01 12:00:00")

    # Specific priority orders so the dataset has
    # a predictable number of priority cases.
    priority_orders = {
        "ORD-1001",
        "ORD-1002",
        "ORD-1009",
        "ORD-1014",
        "ORD-1020",
        "ORD-1027",
        "ORD-1033",
        "ORD-1041",
        "ORD-1046",
        "ORD-1055",
        "ORD-1062",
        "ORD-1070",
        "ORD-1078",
        "ORD-1088",
        "ORD-1092",
        "ORD-1096",
        "ORD-1106",
        "ORD-1126",
        "ORD-1136",
        "ORD-1140",
    }

    # Generate a realistic daily demo volume of 240 orders.
    for order_number in range(1, 241):

        order_id = f"ORD-{1000 + order_number}"

        priority = order_id in priority_orders

        status = random.choice(statuses)

        # --------------------------------------------------
        # Date logic
        # --------------------------------------------------

        if status == "Shipped":

            # Completed orders were created sufficiently
            # before the reference time.
            order_date = reference_now - pd.Timedelta(
                days=random.randint(1, 3),
                hours=random.randint(1, 8),
                minutes=random.randint(0, 59),
            )

            # Deadline is after order creation but before now.
            required_ship_datetime = order_date + pd.Timedelta(
                hours=random.randint(4, 24)
            )

            # Make sure the deadline is actually in the past.
            if required_ship_datetime >= reference_now:
                required_ship_datetime = reference_now - pd.Timedelta(
                    hours=random.randint(1, 6)
                )

        else:

            # Active orders were created recently.
            order_date = reference_now - pd.Timedelta(
                days=random.randint(0, 2),
                hours=random.randint(0, 8),
                minutes=random.randint(0, 59),
            )

            # Deadline is always after order creation.
            required_ship_datetime = order_date + pd.Timedelta(
                hours=random.choice([8, 12, 18, 24, 36])
            )

            # For normal active orders, keep the deadline
            # reasonably close to the reference date.
            if required_ship_datetime <= reference_now:
                required_ship_datetime = reference_now + pd.Timedelta(
                    hours=random.choice([4, 8, 12, 24])
                )

        courier_id = random.choice(
            ["C001", "C002", "C003"]
        )

        orders.append(
            {
                "order_id": order_id,
                "order_date": order_date.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "customer_name": f"Customer {order_number:03d}",
                "channel": random.choice(channels),
                "priority": priority,
                "required_ship_datetime": (
                    required_ship_datetime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
                "status": status,
                "courier_id": courier_id,
            }
        )

    orders_df = pd.DataFrame(orders)

    # --------------------------------------------------
    # Deliberate demo scenarios
    # --------------------------------------------------

    # ORD-1001
    # Priority order approaching deadline.
    # Used with SKU-001 qty 5.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1001",
        [
            "priority",
            "status",
            "required_ship_datetime",
        ],
    ] = [
        True,
        "Processed",
        "2026-10-01 13:00:00",
    ]

    # ORD-1002
    # Priority order already past deadline.
    # Used with SKU-002 qty 5.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1002",
        [
            "priority",
            "status",
            "required_ship_datetime",
        ],
    ] = [
        True,
        "Picking",
        "2026-10-01 09:00:00",
    ]

    # ORD-1003
    # Reserved inventory demonstration.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1003",
        [
            "priority",
            "status",
            "required_ship_datetime",
        ],
    ] = [
        False,
        "Processed",
        "2026-10-01 20:00:00",
    ]

    # ORD-1004
    # Normal insufficient-inventory style order.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1004",
        [
            "priority",
            "status",
            "required_ship_datetime",
        ],
    ] = [
        False,
        "Processed",
        "2026-10-01 18:00:00",
    ]

    # ORD-1005
    # Normal completed order.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1005",
        [
            "priority",
            "status",
            "required_ship_datetime",
        ],
    ] = [
        False,
        "Shipped",
        "2026-09-30 18:00:00",
    ]

    # ORD-1006
    # Deterministic staging workflow demonstration.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1006",
        [
            "priority",
            "status",
            "required_ship_datetime",
            "courier_id",
        ],
    ] = [
        False,
        "Packed",
        "2026-10-01 16:00:00",
        "C001",
    ]

    # ORD-1010
    # Deterministic overdue courier pickup scenario.
    orders_df.loc[
        orders_df["order_id"] == "ORD-1010",
        [
            "priority",
            "status",
            "required_ship_datetime",
            "courier_id",
        ],
    ] = [
        False,
        "Awaiting Pickup",
        "2026-09-30 18:00:00",
        "C001",
    ]

    # Save
    output_path = DATA_DIR / "orders.csv"

    orders_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(orders_df)} orders"
    )

    print(
        f"Saved to: {output_path}"
    )

    return orders_df


# --------------------------------------------------
# Order Item Data
# --------------------------------------------------

def generate_order_items(
    orders_df,
    products_df,
):
    order_items = []

    # Use SKU-004 to SKU-040 for normal random orders.
    # SKU-001, SKU-002 and SKU-003 are reserved for
    # deliberate demonstration scenarios.
    normal_products = products_df[
        ~products_df["sku"].isin(
            [
                "SKU-001",
                "SKU-002",
                "SKU-003",
            ]
        )
    ]

    # --------------------------------------------------
    # Deliberate scenarios
    # --------------------------------------------------

    special_order_items = {
        "ORD-1001": [("SKU-001", 5)],
        "ORD-1002": [("SKU-002", 5)],
        "ORD-1003": [("SKU-003", 5)],
        "ORD-1004": [("SKU-004", 2)],
        "ORD-1005": [("SKU-005", 1)],
        "ORD-1006": [("SKU-006", 1)],
    }

    for _, order in orders_df.iterrows():

        order_id = order["order_id"]

        # --------------------------------------------------
        # Special demo orders
        # --------------------------------------------------

        if order_id in special_order_items:

            selected_items = special_order_items[
                order_id
            ]

        else:

            # Most orders have 1–2 items.
            item_count = random.choices(
                [1, 2, 3],
                weights=[60, 30, 10],
                k=1,
            )[0]

            # random.sample guarantees unique SKUs
            # within the same order.
            selected_products = random.sample(
                list(normal_products["sku"]),
                item_count,
            )

            selected_items = [
                (
                    sku,
                    random.randint(1, 3),
                )
                for sku in selected_products
            ]

        # --------------------------------------------------
        # Create order item records
        # --------------------------------------------------

        for sku, quantity in selected_items:

            order_items.append(
                {
                    "order_item_id": (
                        f"OI-{len(order_items) + 1:04d}"
                    ),
                    "order_id": order_id,
                    "sku": sku,
                    "quantity": quantity,
                }
            )

    order_items_df = pd.DataFrame(
        order_items
    )

    # Save
    output_path = DATA_DIR / "order_items.csv"

    order_items_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(order_items_df)} order items"
    )

    print(
        f"Saved to: {output_path}"
    )

    return order_items_df


# --------------------------------------------------
# Courier Data
# --------------------------------------------------

def generate_couriers():
    couriers = [
        {
            "courier_id": "C001",
            "courier_name": "Courier A",
            "service_level": "Standard",
            "pickup_time": "15:00",
            "delivery_days": 3,
            "cost_per_order": 70,
        },
        {
            "courier_id": "C002",
            "courier_name": "Courier B",
            "service_level": "Express",
            "pickup_time": "14:00",
            "delivery_days": 1,
            "cost_per_order": 110,
        },
        {
            "courier_id": "C003",
            "courier_name": "Courier C",
            "service_level": "Economy",
            "pickup_time": "17:00",
            "delivery_days": 4,
            "cost_per_order": 55,
        },
    ]

    couriers_df = pd.DataFrame(
        couriers
    )

    output_path = DATA_DIR / "couriers.csv"

    couriers_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(couriers_df)} couriers"
    )

    print(
        f"Saved to: {output_path}"
    )

    return couriers_df


# --------------------------------------------------
# Shipment Data
# --------------------------------------------------

def generate_shipments(orders_df):
    shipments = []

    reference_now = pd.Timestamp(
        "2026-10-01 12:00:00"
    )

    # Courier pickup schedules
    courier_pickup_times = {
        "C001": "15:00",
        "C002": "14:00",
        "C003": "17:00",
    }

    # These IDs must match the staging_bays table
    # created by database/db_setup.py.
    #
    # Each courier can only use its assigned bays:
    #
    # C001 -> A1, A2, B3
    # C002 -> A3, A4, B4
    # C003 -> B1, B2
    staging_bays_by_courier = {
        "C001": ["A1", "A2", "B3"],
        "C002": ["A3", "A4", "B4"],
        "C003": ["B1", "B2"],
    }

    for _, order in orders_df.iterrows():

        order_id = order["order_id"]
        status = order["status"]
        courier_id = order["courier_id"]

        # Always initialize these values first.
        # This prevents UnboundLocalError for
        # statuses that do not assign a pickup time.
        pickup_datetime = pd.NaT
        pickup_status = "Not Ready"
        staging_location = ""

        courier_staging_bays = staging_bays_by_courier[
            courier_id
        ]

        # --------------------------------------------------
        # Shipment status based on fulfillment status
        # --------------------------------------------------

        if status == "Shipped":

            # Shipment has already been collected.
            pickup_status = "Picked Up"

            pickup_datetime = (
                reference_now
                - pd.Timedelta(
                    hours=random.randint(2, 48)
                )
            )

            staging_location = random.choice(
                courier_staging_bays
            )

        elif status == "Awaiting Pickup":

            pickup_status = "Awaiting Pickup"

            # Use the courier's scheduled pickup time.
            pickup_time = courier_pickup_times[
                courier_id
            ]

            scheduled_pickup_today = pd.Timestamp(
                f"2026-10-01 {pickup_time}:00"
            )

            # Some orders are deliberately overdue.
            if random.random() < 0.4:

                # Previous scheduled pickup
                pickup_datetime = (
                    scheduled_pickup_today
                    - pd.Timedelta(days=1)
                )

            else:

                # Today's scheduled pickup
                pickup_datetime = (
                    scheduled_pickup_today
                )

            staging_location = random.choice(
                courier_staging_bays
            )

        elif status == "Staged":

            # Staged orders have a physical staging
            # location and are waiting for pickup.
            pickup_status = "Awaiting Pickup"

            pickup_time = courier_pickup_times[
                courier_id
            ]

            pickup_datetime = pd.Timestamp(
                f"2026-10-01 {pickup_time}:00"
            )

            staging_location = random.choice(
                courier_staging_bays
            )

        elif status == "Packed":

            # Packed means ready to be staged,
            # but no physical staging bay has been
            # assigned yet.
            pickup_status = "Not Ready"
            pickup_datetime = pd.NaT
            staging_location = ""

        # --------------------------------------------------
        # Tracking ID
        # --------------------------------------------------

        tracking_id = (
            f"TRK-{order_id.replace('ORD-', '')}"
        )

        shipments.append(
            {
                "shipment_id": (
                    f"SHP-{len(shipments) + 1:04d}"
                ),
                "order_id": order_id,
                "courier_id": courier_id,
                "pickup_datetime": (
                    pickup_datetime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if pd.notna(pickup_datetime)
                    else ""
                ),
                "pickup_status": pickup_status,
                "staging_location": staging_location,
                "tracking_id": tracking_id,
            }
        )

    shipments_df = pd.DataFrame(
        shipments
    )

    # --------------------------------------------------
    # Deliberate overdue pickup scenario
    # --------------------------------------------------

    # ORD-1010 uses Courier C001.
    # C001's scheduled pickup time is 15:00.
    #
    # We deliberately set the scheduled pickup to
    # yesterday so the application can detect an
    # overdue pickup at the reference time of
    # 2026-10-01 12:00.

    shipments_df.loc[
        shipments_df["order_id"] == "ORD-1010",
        [
            "courier_id",
            "pickup_status",
            "pickup_datetime",
            "staging_location",
        ],
    ] = [
        "C001",
        "Awaiting Pickup",
        "2026-09-30 15:00:00",
        "A1",
    ]

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    output_path = DATA_DIR / "shipments.csv"

    shipments_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(shipments_df)} shipments"
    )

    print(
        f"Saved to: {output_path}"
    )

    return shipments_df


# --------------------------------------------------
# Exception Data
# --------------------------------------------------

def generate_exceptions(
    orders_df,
    shipments_df,
    inventory_df,
):
    exceptions = []

    reference_now = pd.Timestamp(
        "2026-10-01 12:00:00"
    )

    # --------------------------------------------------
    # Helper function
    # --------------------------------------------------

    def add_exception(
        order_id,
        issue_type,
        description,
        priority,
        status,
        owner,
        created_at,
        resolved_at="",
    ):
        exceptions.append(
            {
                "exception_id": (
                    f"EXC-{len(exceptions) + 1:04d}"
                ),
                "order_id": order_id,
                "issue_type": issue_type,
                "description": description,
                "priority": priority,
                "status": status,
                "owner": owner,
                "created_at": created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "resolved_at": (
                    resolved_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if resolved_at != ""
                    else ""
                ),
            }
        )

    # --------------------------------------------------
    # 1. Inventory shortage
    # --------------------------------------------------

    add_exception(
        order_id="ORD-1002",
        issue_type="Inventory Shortage",
        description=(
            "Main warehouse does not have enough "
            "stock to fulfill the order."
        ),
        priority="High",
        status="Open",
        owner="Warehouse",
        created_at=(
            reference_now
            - pd.Timedelta(hours=3)
        ),
    )

    # --------------------------------------------------
    # 2. Stock transfer required
    # --------------------------------------------------

    add_exception(
        order_id="ORD-1001",
        issue_type="Stock Transfer Required",
        description=(
            "Required stock is available in the "
            "secondary warehouse but must be moved "
            "to the main warehouse before picking."
        ),
        priority="High",
        status="In Progress",
        owner="Warehouse",
        created_at=(
            reference_now
            - pd.Timedelta(hours=2)
        ),
    )

    # --------------------------------------------------
    # 3. Variant mismatch
    # --------------------------------------------------

    add_exception(
        order_id="ORD-1004",
        issue_type="Variant Mismatch",
        description=(
            "Picked product variant does not match "
            "the variant ordered by the customer."
        ),
        priority="High",
        status="Open",
        owner="Warehouse",
        created_at=(
            reference_now
            - pd.Timedelta(hours=1)
        ),
    )

    # --------------------------------------------------
    # 4. Courier pickup missed
    # --------------------------------------------------

    add_exception(
        order_id="ORD-1010",
        issue_type="Courier Pickup Missed",
        description=(
            "Order is staged and awaiting pickup, "
            "but the scheduled courier pickup time "
            "has passed."
        ),
        priority="High",
        status="Open",
        owner="Operations",
        created_at=(
            reference_now
            - pd.Timedelta(hours=4)
        ),
    )

    # --------------------------------------------------
    # 5. Priority order at risk
    # --------------------------------------------------

    add_exception(
        order_id="ORD-1001",
        issue_type="Priority Order At Risk",
        description=(
            "Priority order is still being processed "
            "and is approaching its required shipping "
            "deadline."
        ),
        priority="High",
        status="Open",
        owner="Operations",
        created_at=(
            reference_now
            - pd.Timedelta(minutes=45)
        ),
    )

    # --------------------------------------------------
    # Additional realistic operational exceptions
    # --------------------------------------------------

    additional_exceptions = [
        (
            "ORD-1020",
            "Picking Issue",
            (
                "Warehouse team could not immediately "
                "locate the required product."
            ),
            "Medium",
            "Open",
            "Warehouse",
        ),
        (
            "ORD-1030",
            "Packing Issue",
            (
                "Package requires repacking before "
                "it can be staged."
            ),
            "Medium",
            "In Progress",
            "Warehouse",
        ),
        (
            "ORD-1040",
            "Staging Issue",
            (
                "Packed shipment was temporarily "
                "misplaced in the staging area."
            ),
            "Medium",
            "Open",
            "Warehouse",
        ),
        (
            "ORD-1050",
            "Inventory Mismatch",
            (
                "Recorded inventory does not match "
                "the physical stock count."
            ),
            "High",
            "In Progress",
            "Warehouse",
        ),
        (
            "ORD-1060",
            "Courier Pickup Missed",
            (
                "Courier did not collect the shipment "
                "during the scheduled pickup window."
            ),
            "High",
            "Resolved",
            "Operations",
        ),
        (
            "ORD-1070",
            "Packing Issue",
            (
                "Packaging material was unavailable "
                "and delayed packing."
            ),
            "Low",
            "Resolved",
            "Warehouse",
        ),
        (
            "ORD-1080",
            "Picking Issue",
            (
                "Picker needed additional time to "
                "locate the product."
            ),
            "Medium",
            "Resolved",
            "Warehouse",
        ),
    ]

    for i, exception_data in enumerate(
        additional_exceptions
    ):

        (
            order_id,
            issue_type,
            description,
            priority,
            status,
            owner,
        ) = exception_data

        created_at = (
            reference_now
            - pd.Timedelta(hours=(i + 2))
        )

        if status == "Resolved":
            resolved_at = (
                created_at
                + pd.Timedelta(hours=1)
            )
        else:
            resolved_at = ""

        add_exception(
            order_id=order_id,
            issue_type=issue_type,
            description=description,
            priority=priority,
            status=status,
            owner=owner,
            created_at=created_at,
            resolved_at=resolved_at,
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    exceptions_df = pd.DataFrame(
        exceptions
    )

    output_path = DATA_DIR / "exceptions.csv"

    exceptions_df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Created {len(exceptions_df)} exceptions"
    )

    print(
        f"Saved to: {output_path}"
    )

    return exceptions_df


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    products_df = generate_products()

    inventory_df = generate_inventory(
        products_df
    )

    orders_df = generate_orders()

    order_items_df = generate_order_items(
        orders_df,
        products_df,
    )

    couriers_df = generate_couriers()

    shipments_df = generate_shipments(
        orders_df
    )

    exceptions_df = generate_exceptions(
        orders_df,
        shipments_df,
        inventory_df,
    )