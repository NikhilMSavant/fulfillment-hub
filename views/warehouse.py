import streamlit as st
import pandas as pd

from utils.database import (
    run_query,
    transition_order_stage,
    verify_order_item_in_db,
    assign_staging_bay,
    process_courier_pickup,
)


# --------------------------------------------------
# Warehouse Mode Styling
# --------------------------------------------------

def apply_warehouse_style():
    st.markdown(
        """
        <style>
        .warehouse-title {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .warehouse-subtitle {
            font-size: 1.15rem;
            margin-bottom: 1rem;
        }

        .warehouse-priority {
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            border: 2px solid;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .warehouse-card {
            padding: 1rem;
            border: 1px solid;
            border-radius: 0.5rem;
            margin-bottom: 0.75rem;
        }

        div.stButton > button {
            min-height: 3.2rem;
            font-size: 1.05rem;
            font-weight: 650;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.7rem;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# Demo Clock
# --------------------------------------------------

def get_demo_now():
    """
    Return the warehouse demo time.

    The default is calculated from the generated order data
    so the demo remains useful even if the generated date range
    changes later.
    """

    orders = run_query(
        """
        SELECT required_ship_datetime
        FROM orders
        WHERE required_ship_datetime IS NOT NULL
        """
    )

    if orders.empty:
        return pd.Timestamp.now().floor("min")

    deadlines = pd.to_datetime(
        orders["required_ship_datetime"],
        errors="coerce",
    ).dropna()

    if deadlines.empty:
        return pd.Timestamp.now().floor("min")

    minimum = deadlines.min()
    maximum = deadlines.max()

    midpoint = minimum + (
        maximum - minimum
    ) / 2

    default_demo_now = midpoint.floor("min")

    if "warehouse_demo_now" not in st.session_state:
        st.session_state[
            "warehouse_demo_now"
        ] = default_demo_now

    return pd.Timestamp(
        st.session_state["warehouse_demo_now"]
    )


def render_demo_clock():
    """
    Display the warehouse demo clock in the sidebar.
    """

    st.sidebar.divider()

    st.sidebar.markdown(
        "### Demo Clock"
    )

    st.sidebar.caption(
        "Use this clock to demonstrate deadline and "
        "pickup-risk scenarios without depending on "
        "the real current time."
    )

    current_demo_now = get_demo_now()

    selected_demo_now = st.sidebar.datetime_input(
        "Demo Now",
        value=current_demo_now.to_pydatetime(),
        key="warehouse_demo_clock",
    )

    selected_demo_now = pd.Timestamp(
        selected_demo_now
    ).floor("min")

    st.session_state[
        "warehouse_demo_now"
    ] = selected_demo_now

    st.sidebar.caption(
        selected_demo_now.strftime(
            "%d %b %Y, %H:%M"
        )
    )

    return selected_demo_now


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def get_order_worklist():
    """
    Return active orders with courier, staging,
    and deadline information.

    Orders are sorted by:
    1. Priority orders first
    2. Earliest ship-by deadline first
    """

    orders = run_query(
        """
        SELECT
            o.order_id,
            o.customer_name,
            o.priority,
            o.status,
            o.required_ship_datetime,
            o.courier_id,
            s.staging_location,
            s.pickup_status,
            s.pickup_datetime
        FROM orders o
        LEFT JOIN shipments s
            ON o.order_id = s.order_id
        WHERE o.status NOT IN ('Shipped', 'Cancelled')
        """
    )

    if orders.empty:
        return orders

    orders["required_ship_datetime"] = pd.to_datetime(
        orders["required_ship_datetime"],
        errors="coerce",
    )

    now = get_demo_now()

    orders["minutes_remaining"] = (
        (
            orders["required_ship_datetime"]
            - now
        ).dt.total_seconds()
        / 60
    )

    orders["deadline_breached"] = (
        orders["minutes_remaining"] < 0
    )

    orders["priority_rank"] = (
        orders["priority"]
        .astype(bool)
        .map(
            {
                True: 0,
                False: 1,
            }
        )
    )

    orders = orders.sort_values(
        [
            "priority_rank",
            "minutes_remaining",
        ],
        ascending=[
            True,
            True,
        ],
        na_position="last",
    ).reset_index(drop=True)

    return orders

def deadline_label(row):
    """
    Produce a simple warehouse-friendly deadline label.
    """

    if pd.isna(row["required_ship_datetime"]):
        return "SHIP BY TIME UNKNOWN"

    deadline = row["required_ship_datetime"]

    if row["deadline_breached"]:
        return (
            f"DEADLINE BREACHED — "
            f"SHIP BY {deadline.strftime('%H:%M')}"
        )

    minutes = row["minutes_remaining"]

    if minutes <= 60:
        return (
            f"PRIORITY — "
            f"SHIP BY {deadline.strftime('%H:%M')}"
        )

    if bool(row["priority"]):
        return (
            f"PRIORITY — "
            f"SHIP BY {deadline.strftime('%H:%M')}"
        )

    return (
        f"SHIP BY {deadline.strftime('%H:%M')}"
    )


def format_time_remaining(row):
    """
    Return human-readable time remaining.
    """

    minutes = row["minutes_remaining"]

    if pd.isna(minutes):
        return "Unknown"

    if minutes < 0:
        overdue_minutes = abs(int(minutes))

        if overdue_minutes >= 60:
            hours = overdue_minutes // 60
            mins = overdue_minutes % 60

            return f"{hours}h {mins}m overdue"

        return f"{overdue_minutes}m overdue"

    remaining_minutes = int(minutes)

    if remaining_minutes >= 60:
        hours = remaining_minutes // 60
        mins = remaining_minutes % 60

        return f"{hours}h {mins}m remaining"

    return f"{remaining_minutes}m remaining"


def get_order_items(order_id):
    """
    Return order items enriched with product and shelf data.
    """

    return run_query(
        """
        SELECT
            oi.order_item_id,
            oi.order_id,
            oi.sku,
            p.product_name,
            p.variant,
            oi.quantity,
            i.shelf_location
        FROM order_items oi
        INNER JOIN products p
            ON oi.sku = p.sku
        LEFT JOIN inventory i
            ON oi.sku = i.sku
           AND i.warehouse_id = 'WH-MAIN'
        WHERE oi.order_id = ?
        ORDER BY oi.order_item_id
        """,
        (order_id,),
    )


def get_staging_bays(courier_id):
    """
    Return active staging bays assigned to a courier.
    """

    return run_query(
        """
        SELECT
            bay_id,
            courier_id
        FROM staging_bays
        WHERE courier_id = ?
          AND active = 1
        ORDER BY bay_id
        """,
        (courier_id,),
    )


def get_staged_orders():
    """
    Return all currently staged orders.
    """

    return run_query(
        """
        SELECT
            o.order_id,
            o.priority,
            o.required_ship_datetime,
            o.courier_id,
            s.staging_location
        FROM orders o
        INNER JOIN shipments s
            ON o.order_id = s.order_id
        WHERE o.status = 'Staged'
        ORDER BY
            o.courier_id,
            o.required_ship_datetime
        """
    )


# --------------------------------------------------
# Order Worklist
# --------------------------------------------------

def render_worklist():
    st.subheader("Warehouse Worklist")

    orders = get_order_worklist()

    if orders.empty:
        st.success(
            "No active warehouse orders are waiting."
        )
        return

    stage_options = [
        "All",
        "Picking",
        "Packing",
        "Staging",
        "Awaiting Pickup",
    ]

    selected_stage = st.selectbox(
        "Work Stage",
        stage_options,
        key="warehouse_work_stage",
    )

    if selected_stage == "All":

        worklist = orders[
            orders["status"].isin(
                [
                    "Picking",
                    "Picked",
                    "Packing",
                    "Packed",
                    "Staged",
                    "Awaiting Pickup",
                ]
            )
        ].copy()

    elif selected_stage == "Picking":

        worklist = orders[
            orders["status"] == "Picking"
        ].copy()

    elif selected_stage == "Packing":

        worklist = orders[
            orders["status"].isin(
                [
                    "Picked",
                    "Packing",
                ]
            )
        ].copy()

    elif selected_stage == "Staging":

        worklist = orders[
            orders["status"] == "Packed"
        ].copy()

    else:

        worklist = orders[
            orders["status"] == "Awaiting Pickup"
        ].copy()

    if worklist.empty:
        st.info(
            "No orders currently require work at this stage."
        )
        return

    total_orders = len(worklist)

    # Keep Warehouse Mode focused on the most urgent tasks.
    # The complete dataset remains available through the
    # selected work stage and other manager/office views.
    display_limit = 20

    worklist = worklist.head(display_limit)

    if total_orders > display_limit:
        st.caption(
            f"Showing the {display_limit} most urgent "
            f"of {total_orders} order(s) requiring attention."
        )
    else:
        st.caption(
            f"{total_orders} order(s) requiring attention."
        )

    for _, row in worklist.iterrows():

        label = deadline_label(row)
        remaining = format_time_remaining(row)

        st.markdown(
            f"### {row['order_id']}"
        )

        st.markdown(
            f"**{label}**  \n"
            f"Current Stage: **{row['status']}**  \n"
            f"Time: **{remaining}**  \n"
            f"Courier: **{row['courier_id']}**"
        )

        staging_location = row["staging_location"]

        if (
            pd.notna(staging_location)
            and str(staging_location).strip()
        ):
            st.write(
                f"Staging Bay: **{staging_location}**"
            )
        else:
            st.write(
                "Staging Bay: **Not Assigned**"
            )

        if row["status"] in {
            "Picking",
            "Picked",
            "Packing",
            "Packed",
        }:

            if st.button(
                f"Work on {row['order_id']}",
                key=f"work_{row['order_id']}",
                type="primary",
            ):
                st.session_state[
                    "warehouse_selected_order"
                ] = row["order_id"]

                st.rerun()

        st.divider()

# --------------------------------------------------
# Order Detail
# --------------------------------------------------

def render_order_detail(order_id):
    st.subheader(
        f"Order {order_id}"
    )

    order_df = run_query(
        """
        SELECT
            o.order_id,
            o.priority,
            o.status,
            o.required_ship_datetime,
            o.courier_id,
            s.staging_location
        FROM orders o
        LEFT JOIN shipments s
            ON o.order_id = s.order_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    )

    if order_df.empty:
        st.error(
            f"Order {order_id} was not found."
        )
        return

    order = order_df.iloc[0]

    st.markdown(
        f"**Current Stage:** `{order['status']}`"
    )

    if bool(order["priority"]):
        st.warning("PRIORITY ORDER")

    if pd.notna(order["required_ship_datetime"]):

        deadline = pd.to_datetime(
            order["required_ship_datetime"]
        )

        st.markdown(
            f"**Ship By:** "
            f"{deadline.strftime('%d %b %Y %H:%M')}"
        )

    st.markdown(
        f"**Courier:** {order['courier_id']}"
    )

    staging_location = order["staging_location"]

    if (
        pd.notna(staging_location)
        and str(staging_location).strip()
    ):
        st.markdown(
            f"**Staging Bay:** "
            f"{staging_location}"
        )
    else:
        st.markdown(
            "**Staging Bay:** Not Assigned"
        )

    st.divider()

    # --------------------------------------------------
    # Items
    # --------------------------------------------------

    st.markdown("### Items to Handle")

    items = get_order_items(order_id)

    if items.empty:
        st.error(
            "No order items were found."
        )
        return

    display_items = items[
        [
            "sku",
            "product_name",
            "variant",
            "quantity",
            "shelf_location",
        ]
    ].copy()

    display_items.columns = [
        "SKU",
        "Product",
        "Variant",
        "Quantity",
        "Shelf",
    ]

    st.dataframe(
        display_items,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # Picking
    # --------------------------------------------------

    if order["status"] == "Picking":

        render_item_verification(
            order_id,
            items,
            "Picking",
        )

    # --------------------------------------------------
    # Packing
    # --------------------------------------------------

    elif order["status"] == "Picked":

        st.success(
            "Picking is complete. "
            "Move the order into Packing to verify packed items."
        )

        if st.button(
            "Start Packing",
            type="primary",
            key=f"start_packing_{order_id}",
        ):

            success, message = transition_order_stage(
                order_id,
                "Packing",
                user_role="Warehouse",
                note="Warehouse started packing.",
            )

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    elif order["status"] == "Packing":

        render_item_verification(
            order_id,
            items,
            "Packing",
        )

    # --------------------------------------------------
    # Packed
    # --------------------------------------------------

    elif order["status"] == "Packed":

        st.success(
            "Packing is complete."
        )

        render_staging_assignment(
            order_id,
            order["courier_id"],
        )


# --------------------------------------------------
# Item Verification
# --------------------------------------------------

def render_item_verification(
    order_id,
    items,
    stage,
):
    st.markdown(
        f"### {stage} Verification"
    )

    st.caption(
        "Verify every item before completing this stage."
    )

    selected_item_id = st.selectbox(
        "Item to verify",
        items["order_item_id"].tolist(),
        format_func=lambda item_id: (
            items.loc[
                items["order_item_id"] == item_id,
                "sku",
            ].iloc[0]
            + " — "
            + items.loc[
                items["order_item_id"] == item_id,
                "product_name",
            ].iloc[0]
            + " — "
            + items.loc[
                items["order_item_id"] == item_id,
                "variant",
            ].iloc[0]
        ),
        key=f"verify_item_{order_id}_{stage}",
    )

    selected = items[
        items["order_item_id"] == selected_item_id
    ].iloc[0]

    st.info(
        f"Expected: **{selected['product_name']}** | "
        f"**{selected['variant']}** | "
        f"Qty **{int(selected['quantity'])}** | "
        f"Shelf **{selected['shelf_location']}**"
    )

    input_col1, input_col2 = st.columns(2)

    with input_col1:

        scanned_sku = st.text_input(
            "Scanned / Verified SKU",
            value=selected["sku"],
            key=f"sku_{order_id}_{stage}_{selected_item_id}",
        )

        scanned_product = st.text_input(
            "Product Name",
            value=selected["product_name"],
            key=f"product_{order_id}_{stage}_{selected_item_id}",
        )

    with input_col2:

        scanned_variant = st.text_input(
            "Variant",
            value=selected["variant"],
            key=f"variant_{order_id}_{stage}_{selected_item_id}",
        )

        verified_quantity = st.number_input(
            "Verified Quantity",
            min_value=0,
            value=int(selected["quantity"]),
            step=1,
            key=f"qty_{order_id}_{stage}_{selected_item_id}",
        )

    message_key = (
        f"verification_message_{order_id}_{stage}_{selected_item_id}"
    )

    message_type_key = (
        f"verification_message_type_{order_id}_{stage}_{selected_item_id}"
    )

    if st.button(
        f"Verify {stage} Item",
        type="primary",
        key=f"verify_{order_id}_{stage}_{selected_item_id}",
    ):

        success, message = verify_order_item_in_db(
            order_item_id=selected_item_id,
            scanned_sku=scanned_sku.strip(),
            scanned_product_name=scanned_product.strip(),
            scanned_variant=scanned_variant.strip(),
            verified_quantity=verified_quantity,
            stage=stage,
            user_role="Warehouse",
        )

        st.session_state[message_key] = message
        st.session_state[message_type_key] = (
            "success" if success else "error"
        )

        st.rerun()

    saved_message = st.session_state.get(message_key)
    saved_message_type = st.session_state.get(message_type_key)

    if saved_message:
        if saved_message_type == "success":
            st.success(saved_message)
        else:
            st.error(saved_message)

    st.divider()
    
    # --------------------------------------------------
    # Verification Progress
    # --------------------------------------------------

    verification_df = run_query(
        """
        SELECT
            oi.order_item_id,
            oi.sku,
            p.product_name,
            p.variant,
            oi.quantity,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM order_item_verifications v
                    WHERE v.order_item_id = oi.order_item_id
                      AND v.stage = ?
                )
                THEN 'Verified'
                ELSE 'Not Verified'
            END AS verification_status
        FROM order_items oi
        INNER JOIN products p
            ON oi.sku = p.sku
        WHERE oi.order_id = ?
        ORDER BY oi.order_item_id
        """,
        (stage, order_id),
    )

    display_verification = verification_df[
        [
            "sku",
            "product_name",
            "variant",
            "quantity",
            "verification_status",
        ]
    ].copy()

    display_verification.columns = [
        "SKU",
        "Product",
        "Variant",
        "Qty",
        "Verification",
    ]

    st.dataframe(
        display_verification,
        use_container_width=True,
        hide_index=True,
    )

    all_verified = (
        len(verification_df) > 0
        and (
            verification_df["verification_status"]
            == "Verified"
        ).all()
    )

    if all_verified:

        next_stage = (
            "Picked"
            if stage == "Picking"
            else "Packed"
        )

        st.success(
            f"All items verified. "
            f"Order can now move to **{next_stage}**."
        )

        if st.button(
            f"Complete {stage}",
            type="primary",
            key=f"complete_{order_id}_{stage}",
        ):

            success, message = transition_order_stage(
                order_id,
                next_stage,
                user_role="Warehouse",
                note=(
                    f"All items verified during {stage}."
                ),
            )

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    else:

        remaining = len(
            verification_df[
                verification_df["verification_status"]
                != "Verified"
            ]
        )

        st.warning(
            f"{remaining} item(s) still need successful "
            f"{stage} verification."
        )


# --------------------------------------------------
# Staging Assignment
# --------------------------------------------------

def render_staging_assignment(
    order_id,
    courier_id,
):
    st.markdown(
        "### Assign Staging Bay"
    )

    bays = get_staging_bays(courier_id)

    if bays.empty:
        st.error(
            f"No active staging bays are configured "
            f"for courier {courier_id}."
        )
        return

    bay_options = bays["bay_id"].tolist()

    selected_bay = st.selectbox(
        f"Staging Bay for {courier_id}",
        bay_options,
        key=f"bay_{order_id}",
    )

    st.caption(
        "Only bays assigned to this order's courier "
        "are available."
    )

    if st.button(
        "Assign Staging Bay",
        type="primary",
        key=f"assign_bay_{order_id}",
    ):

        success, message = assign_staging_bay(
            order_id,
            selected_bay,
            user_role="Warehouse",
        )

        if success:
            st.session_state[
                f"staging_assignment_message_{order_id}"
            ] = message
            st.rerun()
        else:
            st.error(message)

    assignment_message = st.session_state.get(
        f"staging_assignment_message_{order_id}"
    )

    if assignment_message:
        st.success(assignment_message)

    st.divider()

    if st.button(
        "Move to Staged",
        type="primary",
        key=f"stage_{order_id}",
    ):

        success, message = transition_order_stage(
            order_id,
            "Staged",
            user_role="Warehouse",
            note=(
                "Order staged after bay assignment."
            ),
        )

        if success:
            st.session_state.pop(
                f"staging_assignment_message_{order_id}",
                None,
            )
            st.success(message)
            st.rerun()
        else:
            st.error(message)

# --------------------------------------------------
# Courier Pickup
# --------------------------------------------------

def render_courier_pickup():
    st.subheader("Courier Pickup")

    staged = get_staged_orders()

    if staged.empty:

        st.success(
            "No staged boxes are currently waiting "
            "for courier pickup."
        )
        return

    courier_options = (
        staged["courier_id"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    selected_courier = st.selectbox(
        "Courier",
        courier_options,
    )

    courier_orders = staged[
        staged["courier_id"] == selected_courier
    ].copy()

    st.markdown(
        f"### {selected_courier} — "
        f"{len(courier_orders)} staged box(es)"
    )

    display_orders = courier_orders[
        [
            "order_id",
            "priority",
            "required_ship_datetime",
            "staging_location",
        ]
    ].copy()

    display_orders["required_ship_datetime"] = (
        pd.to_datetime(
            display_orders["required_ship_datetime"],
            errors="coerce",
        ).dt.strftime("%d %b %H:%M")
    )

    display_orders.columns = [
        "Order ID",
        "Priority",
        "Ship By",
        "Bay",
    ]

    st.dataframe(
        display_orders,
        use_container_width=True,
        hide_index=True,
    )

    order_ids = courier_orders[
        "order_id"
    ].tolist()

    handed_over = st.multiselect(
        "Select boxes physically handed to courier",
        order_ids,
    )

    if not handed_over:

        st.warning(
            "No boxes selected. "
            "If you process the pickup now, all staged boxes "
            "will be flagged as Courier Pickup Missed."
        )

    if st.button(
        "Process Courier Pickup",
        type="primary",
    ):

        success, message = process_courier_pickup(
            courier_id=selected_courier,
            handed_over_order_ids=handed_over,
            user_role="Warehouse",
        )

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)


# --------------------------------------------------
# Find a Box
# --------------------------------------------------

def render_find_box():
    st.subheader("Find a Box")

    search_order = st.text_input(
        "Order ID",
        placeholder="e.g. ORD-1010",
    )

    if not search_order:
        st.info(
            "Enter an Order ID to find its current "
            "fulfillment stage and location."
        )
        return

    normalized_order_id = (
        search_order.strip()
        .replace(" ", "")
        .upper()
    )

    result = run_query(
        """
        SELECT
            o.order_id,
            o.status,
            o.priority,
            o.courier_id,
            s.staging_location,
            s.pickup_status,
            s.pickup_datetime
        FROM orders o
        LEFT JOIN shipments s
            ON o.order_id = s.order_id
        WHERE UPPER(REPLACE(o.order_id, ' ', '')) = ?
        """,
        (normalized_order_id,),
    )

    if result.empty:
        st.error(
            f"Order {search_order.strip()} was not found."
        )
        return

    row = result.iloc[0]

    staging_location = row["staging_location"]
    pickup_status = row["pickup_status"]

    if (
        pd.isna(staging_location)
        or not str(staging_location).strip()
    ):
        staging_display = "Not Assigned"
    else:
        staging_display = str(staging_location)

    if (
        pd.isna(pickup_status)
        or not str(pickup_status).strip()
    ):
        pickup_display = "Not Ready"
    else:
        pickup_display = str(pickup_status)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Stage",
            row["status"],
        )

    with col2:
        st.metric(
            "Courier",
            row["courier_id"],
        )

    with col3:
        st.metric(
            "Staging Bay",
            staging_display,
        )

    with col4:
        st.metric(
            "Pickup",
            pickup_display,
        )

    if row["status"] == "Staged":

        st.success(
            f"Box is staged at **{staging_display}** "
            f"for courier **{row['courier_id']}**."
        )

    elif row["status"] == "Shipped":

        st.success(
            "Box has been handed over to the courier."
        )

    else:

        st.info(
            f"Box is currently in the **{row['status']}** stage."
        )

# --------------------------------------------------
# Warehouse Mode
# --------------------------------------------------

def render_warehouse():

    apply_warehouse_style()

    st.markdown(
        '<div class="warehouse-title">'
        'Warehouse Mode'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="warehouse-subtitle">'
        'Simple workflow for picking, packing, staging, '
        'and courier handover.'
        '</div>',
        unsafe_allow_html=True,
    )

    render_demo_clock()

    # --------------------------------------------------
    # Quick Navigation
    # --------------------------------------------------

    action = st.radio(
        "Warehouse Task",
        [
            "Worklist",
            "Find a Box",
            "Courier Pickup",
        ],
        horizontal=True,
        key="warehouse_task",
    )

    st.divider()

    # --------------------------------------------------
    # Order Detail Screen
    # --------------------------------------------------

    selected_order = st.session_state.get(
        "warehouse_selected_order"
    )

    if (
        action == "Worklist"
        and selected_order
    ):

        if st.button(
            "← Back to Worklist",
            key="back_to_worklist",
        ):
            del st.session_state[
                "warehouse_selected_order"
            ]
            st.rerun()

        st.divider()

        render_order_detail(
            selected_order
        )

        return

    # --------------------------------------------------
    # Main Warehouse Screens
    # --------------------------------------------------

    if action == "Worklist":

        render_worklist()

    elif action == "Find a Box":

        if "warehouse_selected_order" in st.session_state:
            del st.session_state[
                "warehouse_selected_order"
            ]

        render_find_box()

    else:

        if "warehouse_selected_order" in st.session_state:
            del st.session_state[
                "warehouse_selected_order"
            ]

        render_courier_pickup()