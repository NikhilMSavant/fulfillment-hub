import streamlit as st
import pandas as pd

from utils.database import run_query
from utils.calculations import (
    calculate_order_risk,
    calculate_pickup_risk,
    calculate_order_inventory_status,
)


def render_orders():

    st.title("Orders")

    st.caption(
        "Track order status, priority, inventory readiness, and fulfillment risk."
    )

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------

    orders_df = run_query(
        "SELECT * FROM orders"
    )

    order_items_df = run_query(
        "SELECT * FROM order_items"
    )

    inventory_df = run_query(
        "SELECT * FROM inventory"
    )

    shipments_df = run_query(
        "SELECT * FROM shipments"
    )

    products_df = run_query(
        "SELECT * FROM products"
    )

    # --------------------------------------------------
    # Apply Business Rules
    # --------------------------------------------------

    orders_risk = calculate_order_risk(
        orders_df
    )

    orders_inventory = calculate_order_inventory_status(
        orders_risk,
        order_items_df,
        inventory_df,
    )

    pickup_risk = calculate_pickup_risk(
        shipments_df
    )

    pickup_flags = pickup_risk[
        [
            "order_id",
            "pickup_datetime",
            "pickup_status",
            "pickup_overdue",
        ]
    ]

    dashboard_orders = orders_inventory.merge(
        pickup_flags,
        on="order_id",
        how="left",
    )

    dashboard_orders["pickup_overdue"] = (
        dashboard_orders["pickup_overdue"]
        .fillna(False)
    )

    dashboard_orders["is_at_risk"] = (
        dashboard_orders["is_delayed"]
        | dashboard_orders["is_priority_at_risk"]
        | dashboard_orders["inventory_shortage"]
        | dashboard_orders["pickup_overdue"]
    )

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    st.subheader("Order Queue")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:

        search_order = st.text_input(
            "Search Order",
            placeholder="e.g. ORD-1001",
        )

    with filter_col2:

        status_options = [
            "All"
        ] + sorted(
            dashboard_orders["status"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Status",
            status_options,
        )

    with filter_col3:

        priority_options = [
            "All",
            "Priority",
            "Standard",
        ]

        selected_priority = st.selectbox(
            "Priority",
            priority_options,
        )

    with filter_col4:

        risk_options = [
            "All",
            "At Risk",
            "Not At Risk",
        ]

        selected_risk = st.selectbox(
            "Risk",
            risk_options,
        )

    # --------------------------------------------------
    # Apply Filters
    # --------------------------------------------------

    filtered_orders = dashboard_orders.copy()

    if search_order:

        filtered_orders = filtered_orders[
            filtered_orders["order_id"]
            .astype(str)
            .str.contains(
                search_order,
                case=False,
                na=False,
            )
        ]

    if selected_status != "All":

        filtered_orders = filtered_orders[
            filtered_orders["status"]
            == selected_status
        ]

    if selected_priority == "Priority":

        filtered_orders = filtered_orders[
            filtered_orders["priority"] == True
        ]

    elif selected_priority == "Standard":

        filtered_orders = filtered_orders[
            filtered_orders["priority"] == False
        ]

    if selected_risk == "At Risk":

        filtered_orders = filtered_orders[
            filtered_orders["is_at_risk"] == True
        ]

    elif selected_risk == "Not At Risk":

        filtered_orders = filtered_orders[
            filtered_orders["is_at_risk"] == False
        ]

    # --------------------------------------------------
    # Order Table
    # --------------------------------------------------

    display_orders = filtered_orders[
        [
            "order_id",
            "priority",
            "status",
            "inventory_status",
            "is_delayed",
            "is_at_risk",
            "pickup_status",
        ]
    ].copy()

    display_orders = display_orders.rename(
        columns={
            "order_id": "Order ID",
            "priority": "Priority",
            "status": "Status",
            "inventory_status": "Inventory",
            "is_delayed": "Delayed",
            "is_at_risk": "At Risk",
            "pickup_status": "Pickup",
        }
    )

    st.caption(
        f"Showing {len(display_orders)} orders"
    )

    if display_orders.empty:

        st.info(
            "No orders match the selected filters."
        )

    else:

        st.dataframe(
            display_orders,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # --------------------------------------------------
    # Order Detail
    # --------------------------------------------------

    st.subheader("Order Details")

    available_order_ids = (
        filtered_orders["order_id"]
        .dropna()
        .tolist()
    )

    if not available_order_ids:

        st.info(
            "Select different filters to view an order."
        )
        return

    selected_order_id = st.selectbox(
        "Select an order",
        available_order_ids,
    )

    selected_order = filtered_orders[
        filtered_orders["order_id"]
        == selected_order_id
    ].iloc[0]

    # --------------------------------------------------
    # Order Summary
    # --------------------------------------------------

    detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)

    with detail_col1:

        st.metric(
            "Status",
            selected_order["status"],
        )

    with detail_col2:

        priority_text = (
            "Priority"
            if selected_order["priority"]
            else "Standard"
        )

        st.metric(
            "Order Type",
            priority_text,
        )

    with detail_col3:

        st.markdown("**Inventory**")
        st.info(selected_order["inventory_status"])


    with detail_col4:

        st.markdown("**Risk**")

        if selected_order["is_at_risk"]:
            st.warning("At Risk")
        else:
            st.success("On Track")

    
    # --------------------------------------------------
    # Order Information
    # --------------------------------------------------

    info_col1, info_col2 = st.columns(2)

    with info_col1:

        st.markdown("**Order Information**")

        st.write(
            f"**Customer:** {selected_order['customer_name']}"
        )

        st.write(
            f"**Channel:** {selected_order['channel']}"
        )

        required_ship = pd.to_datetime(
            selected_order["required_ship_datetime"]
        )

        st.write(
            f"**Required Ship Time:** "
            f"{required_ship.strftime('%d %b %Y %H:%M')}"
        )

    with info_col2:

        st.markdown("**Fulfillment Information**")

        st.write(
            f"**Courier:** {selected_order['courier_id']}"
        )

        st.write(
            f"**Pickup Status:** "
            f"{selected_order['pickup_status']}"
        )

        pickup_value = selected_order["pickup_datetime"]

        if pd.notna(pickup_value):

            pickup_time = pd.to_datetime(
                pickup_value
            )

            st.write(
            f"**Pickup Time:** "
            f"{pickup_time.strftime('%d %b %Y %H:%M')}"
            )

        else:

            st.write(
                "**Pickup Time:** Not scheduled"
            )

    # --------------------------------------------------
    # Fulfillment Progress
    # --------------------------------------------------

    st.markdown("**Fulfillment Progress**")

    stages = [
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

    current_status = selected_order["status"]

    if current_status in stages:

        current_index = stages.index(
            current_status
        )

        progress_value = (
            current_index / (len(stages) - 1)
        )

        st.progress(
            progress_value
        )

        st.caption(
            f"Current stage: {current_status}"
        )

    else:

        st.info(
            f"Current status: {current_status}"
        )

    # --------------------------------------------------
    # Order Items
    # --------------------------------------------------

    st.markdown("**Order Items**")

    selected_items = order_items_df[
        order_items_df["order_id"]
        == selected_order_id
    ].copy()

    selected_items = selected_items.merge(
        products_df[
            [
                "sku",
                "product_name",
                "variant",
            ]
        ],
        on="sku",
        how="left",
    )

    inventory_summary = inventory_df[
        [
            "sku",
            "warehouse_id",
            "quantity_on_hand",
            "reserved_quantity",
        ]
    ].copy()

    inventory_summary["available"] = (
        inventory_summary["quantity_on_hand"]
        - inventory_summary["reserved_quantity"]
    )

    main_inventory = inventory_summary[
        inventory_summary["warehouse_id"]
        == "WH-MAIN"
    ][
        [
            "sku",
            "available",
        ]
    ].rename(
        columns={
            "available": "Main Available",
        }
    )

    secondary_inventory = inventory_summary[
        inventory_summary["warehouse_id"]
        == "WH-SEC"
    ][
        [
            "sku",
            "available",
        ]
    ].rename(
        columns={
            "available": "Secondary Available",
        }
    )

    selected_items = selected_items.merge(
        main_inventory,
        on="sku",
        how="left",
    )

    selected_items = selected_items.merge(
        secondary_inventory,
        on="sku",
        how="left",
    )

    selected_items = selected_items[
        [
            "sku",
            "product_name",
            "variant",
            "quantity",
            "Main Available",
            "Secondary Available",
        ]
    ]

    selected_items = selected_items.rename(
        columns={
            "sku": "SKU",
            "product_name": "Product",
            "variant": "Variant",
            "quantity": "Qty",
        }
    )

    st.dataframe(
        selected_items,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # Attention Message
    # --------------------------------------------------

    if selected_order["inventory_status"] == "Transfer Required":

        st.warning(
            "Inventory action required: "
            "stock needs to be transferred from the "
            "secondary warehouse before fulfillment."
        )

    elif selected_order["inventory_status"] == "Insufficient Stock":

        st.error(
            "Inventory shortage: available stock across "
            "the warehouses is not sufficient for this order."
        )

    elif selected_order["is_delayed"]:

        st.error(
            "Fulfillment delay detected. "
            "This order has passed its required ship time."
        )

    elif selected_order["pickup_overdue"]:

        st.warning(
            "Courier pickup is overdue."
        )

    elif selected_order["is_priority_at_risk"]:

        st.warning(
            "Priority order requires attention."
        )

    else:

        st.success(
            "No immediate fulfillment issue detected."
        )