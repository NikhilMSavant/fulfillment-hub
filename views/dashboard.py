import streamlit as st
import pandas as pd
import plotly.express as px

from utils.database import run_query
from utils.calculations import (
    calculate_order_risk,
    calculate_pickup_risk,
    calculate_order_inventory_status,
)


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

def render_dashboard():

    st.title("Operations Dashboard")

    st.caption(
        "Monitor orders, fulfillment risks, inventory, and exceptions."
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

    exceptions_df = run_query(
        "SELECT * FROM exceptions"
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

    # --------------------------------------------------
    # Combine Pickup Risk With Orders
    # --------------------------------------------------
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


    # --------------------------------------------------
    # At-Risk Orders
    # --------------------------------------------------

    dashboard_orders["is_at_risk"] = (
        dashboard_orders["is_delayed"]
        | dashboard_orders["is_priority_at_risk"]
        | dashboard_orders["inventory_shortage"]
        | dashboard_orders["pickup_overdue"]
    )


    # --------------------------------------------------
    # Active Orders
    # --------------------------------------------------

    active_orders = dashboard_orders[
        ~dashboard_orders["status"].isin(
            ["Shipped", "Cancelled"]
        )
    ]

    
    # --------------------------------------------------
    # KPI Values
    # --------------------------------------------------

    active_count = len(active_orders)

    priority_count = len(
        active_orders[
            active_orders["priority"] == True
        ]
    )

    at_risk_count = len(
        active_orders[
            active_orders["is_at_risk"]
        ]
    )

    open_exception_count = len(
        exceptions_df[
            exceptions_df["status"] != "Resolved"
        ]
    )

    # --------------------------------------------------
    # KPI Cards
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Active Orders",
            active_count,
        )

    with col2:
        st.metric(
            "Priority Orders",
            priority_count,
        )

    with col3:
        st.metric(
            "At Risk",
            at_risk_count,
        )

    with col4:
        st.metric(
            "Open Exceptions",
            open_exception_count,
        )

    st.divider()

    # --------------------------------------------------
    # Needs Attention
    # --------------------------------------------------

    st.subheader("Needs Attention")

    attention_col1, attention_col2 = st.columns(2)

    # Priority at risk
    with attention_col1:

        priority_risk = dashboard_orders[
            dashboard_orders["is_priority_at_risk"]
        ][
            [
                "order_id",
                "required_ship_datetime",
                "status",
            ]
        ].copy()

        st.markdown("**Priority Orders At Risk**")

        if priority_risk.empty:

            st.success(
                "No priority orders are currently at risk."
            )

        else:

            priority_risk["required_ship_datetime"] = (
                pd.to_datetime(
                    priority_risk["required_ship_datetime"]
                ).dt.strftime(
                    "%d %b %H:%M"
                )
            )

            st.dataframe(
                priority_risk,
                use_container_width=True,
                hide_index=True,
            )

    # Inventory problems
    with attention_col2:

        inventory_issues = dashboard_orders[
            dashboard_orders["inventory_status"] != "Ready"
        ][
            [
                "order_id",
                "inventory_status",
                "main_shortage",
            ]
        ].copy()

        st.markdown("**Inventory Problems**")

        if inventory_issues.empty:

            st.success(
                "No inventory problems detected."
            )

        else:

            st.dataframe(
                inventory_issues,
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------
    # Additional Alerts
    # --------------------------------------------------

    alert_col1, alert_col2 = st.columns(2)

    with alert_col1:

        delayed_orders = dashboard_orders[
            dashboard_orders["is_delayed"]
        ][
            [
                "order_id",
                "required_ship_datetime",
                "status",
            ]
        ]

        st.markdown("**Delayed Orders**")

        if delayed_orders.empty:

            st.success(
                "No delayed orders detected."
            )

        else:

            st.dataframe(
                delayed_orders,
                use_container_width=True,
                hide_index=True,
            )

    with alert_col2:

        overdue_pickups = dashboard_orders[
            dashboard_orders["pickup_overdue"]
        ][
            [
                "order_id",
                "pickup_datetime",
                "pickup_status",
            ]
        ]

        st.markdown("**Overdue Courier Pickups**")

        if overdue_pickups.empty:

            st.success(
                "No overdue pickups detected."
            )

        else:

            st.dataframe(
                overdue_pickups,
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    # --------------------------------------------------
    # Priority Orders
    # --------------------------------------------------

    st.subheader("Priority Orders")

    priority_orders = dashboard_orders[
        (
            dashboard_orders["priority"] == True
        )
        & (
            dashboard_orders["status"]
            != "Cancelled"
        )
    ][
        [
            "order_id",
            "channel",
            "status",
            "required_ship_datetime",
            "inventory_status",
            "is_delayed",
            "is_priority_at_risk",
        ]
    ].copy()

    priority_orders["required_ship_datetime"] = (
        pd.to_datetime(
            priority_orders["required_ship_datetime"]
        ).dt.strftime(
            "%d %b %Y %H:%M"
        )
    )

    st.dataframe(
        priority_orders,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # --------------------------------------------------
    # Fulfillment Pipeline
    # --------------------------------------------------

    st.subheader("Fulfillment Pipeline")

    pipeline = (
        active_orders[
            "status"
        ]
        .value_counts()
        .reindex(
            [
                "Received",
                "Processed",
                "Picking",
                "Picked",
                "Packing",
                "Packed",
                "Staged",
                "Awaiting Pickup",
            ],
            fill_value=0,
        )
        .reset_index()
    )

    pipeline.columns = [
        "Status",
        "Orders",
    ]

    fig = px.bar(
        pipeline,
        x="Status",
        y="Orders",
        title="Active Orders by Fulfillment Stage",
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="Orders",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )