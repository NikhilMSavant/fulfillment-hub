import streamlit as st
import pandas as pd

from utils.database import run_query
from utils.calculations import (
    calculate_order_risk,
    calculate_pickup_risk,
    calculate_order_inventory_status,
)


def render_fulfillment():

    st.title("Fulfillment")

    st.caption(
        "Monitor orders through picking, packing, staging, and courier pickup."
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
            "staging_location",
        ]
    ]

    fulfillment = orders_inventory.merge(
        pickup_flags,
        on="order_id",
        how="left",
    )

    fulfillment["pickup_overdue"] = (
        fulfillment["pickup_overdue"]
        .fillna(False)
    )

    fulfillment["is_at_risk"] = (
        fulfillment["is_delayed"]
        | fulfillment["is_priority_at_risk"]
        | fulfillment["inventory_shortage"]
        | fulfillment["pickup_overdue"]
    )

    # --------------------------------------------------
    # KPI Section
    # --------------------------------------------------

    st.subheader("Fulfillment Overview")

    active_orders = fulfillment[
        ~fulfillment["status"].isin(
            ["Shipped", "Cancelled"]
        )
    ]

    picking_count = len(
        active_orders[
            active_orders["status"] == "Picking"
        ]
    )

    packing_count = len(
        active_orders[
            active_orders["status"].isin(
                ["Packing", "Picked"]
            )
        ]
    )

    staged_count = len(
        active_orders[
            active_orders["status"] == "Staged"
        ]
    )

    pickup_count = len(
        active_orders[
            active_orders["status"] == "Awaiting Pickup"
        ]
    )

    overdue_pickups = len(
        active_orders[
            active_orders["pickup_overdue"]
        ]
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Picking",
            picking_count,
        )

    with col2:
        st.metric(
            "Packing",
            packing_count,
        )

    with col3:
        st.metric(
            "Staged",
            staged_count,
        )

    with col4:
        st.metric(
            "Awaiting Pickup",
            pickup_count,
        )

    with col5:
        st.metric(
            "Pickup Overdue",
            overdue_pickups,
        )

    st.divider()

    # --------------------------------------------------
    # Operational Queue
    # --------------------------------------------------

    st.subheader("Fulfillment Queue")

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        status_options = [
            "All"
        ] + sorted(
            active_orders["status"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Fulfillment Stage",
            status_options,
        )

    with filter_col2:

        attention_options = [
            "All",
            "Needs Attention",
            "No Immediate Issue",
        ]

        selected_attention = st.selectbox(
            "Attention",
            attention_options,
        )

    filtered = active_orders.copy()

    if selected_status != "All":

        filtered = filtered[
            filtered["status"] == selected_status
        ]

    if selected_attention == "Needs Attention":

        filtered = filtered[
            filtered["is_at_risk"] == True
        ]

    elif selected_attention == "No Immediate Issue":

        filtered = filtered[
            filtered["is_at_risk"] == False
        ]

    # --------------------------------------------------
    # Fulfillment Table
    # --------------------------------------------------

    display_df = filtered[
        [
            "order_id",
            "priority",
            "status",
            "inventory_status",
            "courier_id",
            "pickup_status",
            "staging_location",
            "is_at_risk",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "order_id": "Order ID",
            "priority": "Priority",
            "status": "Stage",
            "inventory_status": "Inventory",
            "courier_id": "Courier",
            "pickup_status": "Pickup",
            "staging_location": "Staging",
            "is_at_risk": "At Risk",
        }
    )

    st.caption(
        f"Showing {len(display_df)} active orders"
    )

    if display_df.empty:

        st.info(
            "No orders match the selected filters."
        )

    else:

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # --------------------------------------------------
    # Orders Requiring Attention
    # --------------------------------------------------

    st.subheader("Orders Requiring Attention")

    attention_orders = active_orders[
        active_orders["is_at_risk"]
    ].copy()

    if attention_orders.empty:

        st.success(
            "No active fulfillment issues detected."
        )

    else:

        attention_display = attention_orders[
            [
                "order_id",
                "priority",
                "status",
                "inventory_status",
                "is_delayed",
                "is_priority_at_risk",
                "pickup_overdue",
            ]
        ].copy()

        attention_display = attention_display.rename(
            columns={
                "order_id": "Order ID",
                "priority": "Priority",
                "status": "Stage",
                "inventory_status": "Inventory",
                "is_delayed": "Delayed",
                "is_priority_at_risk": "Priority Risk",
                "pickup_overdue": "Pickup Overdue",
            }
        )

        st.dataframe(
            attention_display,
            use_container_width=True,
            hide_index=True,
        )