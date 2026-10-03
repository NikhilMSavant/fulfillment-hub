import streamlit as st
import pandas as pd

from utils.database import (
    run_query,
    transfer_stock,
)


def render_inventory():

    st.title("Inventory")

    st.caption(
        "Monitor stock across the main and secondary warehouses."
    )

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------

    inventory_df = run_query(
        "SELECT * FROM inventory"
    )

    products_df = run_query(
        "SELECT * FROM products"
    )

    # --------------------------------------------------
    # Prepare Inventory
    # --------------------------------------------------

    inventory_df["available_quantity"] = (
        inventory_df["quantity_on_hand"]
        - inventory_df["reserved_quantity"]
    )

    inventory_df["stock_status"] = "Available"

    inventory_df.loc[
        inventory_df["available_quantity"] <= 0,
        "stock_status",
    ] = "Out of Stock"

    inventory_df.loc[
        (
            inventory_df["available_quantity"] > 0
        )
        & (
            inventory_df["available_quantity"]
            <= inventory_df["reorder_level"]
        ),
        "stock_status",
    ] = "Low Stock"

    # --------------------------------------------------
    # Add Product Information
    # --------------------------------------------------

    inventory_df = inventory_df.merge(
        products_df[
            [
                "sku",
                "product_name",
                "category",
                "variant",
            ]
        ],
        on="sku",
        how="left",
    )

    # --------------------------------------------------
    # Warehouse Summary
    # --------------------------------------------------

    main_inventory = inventory_df[
        inventory_df["warehouse_id"] == "WH-MAIN"
    ].copy()

    secondary_inventory = inventory_df[
        inventory_df["warehouse_id"] == "WH-SEC"
    ].copy()

    total_main_available = (
        main_inventory["available_quantity"].sum()
    )

    total_secondary_available = (
        secondary_inventory["available_quantity"].sum()
    )

    main_out_of_stock = len(
        main_inventory[
            main_inventory["available_quantity"] <= 0
        ]
    )

    main_low_stock = len(
        main_inventory[
            (
                main_inventory["available_quantity"] > 0
            )
            & (
                main_inventory["available_quantity"]
                <= main_inventory["reorder_level"]
            )
        ]
    )

    # --------------------------------------------------
    # KPI Cards
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Main Available",
            int(total_main_available),
        )

    with col2:

        st.metric(
            "Secondary Available",
            int(total_secondary_available),
        )

    with col3:

        st.metric(
            "Main Low Stock",
            main_low_stock,
        )

    with col4:

        st.metric(
            "Main Out of Stock",
            main_out_of_stock,
        )

    st.divider()

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    st.subheader("Inventory Overview")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:

        search_sku = st.text_input(
            "Search SKU / Product",
            placeholder="e.g. SKU-001",
        )

    with filter_col2:

        warehouse_options = [
            "All",
            "WH-MAIN",
            "WH-SEC",
        ]

        selected_warehouse = st.selectbox(
            "Warehouse",
            warehouse_options,
        )

    with filter_col3:

        status_options = [
            "All",
            "Available",
            "Low Stock",
            "Out of Stock",
        ]

        selected_status = st.selectbox(
            "Stock Status",
            status_options,
        )

    # --------------------------------------------------
    # Apply Filters
    # --------------------------------------------------

    filtered_inventory = inventory_df.copy()

    if search_sku:

        search_value = search_sku.strip()

        filtered_inventory = filtered_inventory[
            filtered_inventory["sku"]
            .astype(str)
            .str.contains(
                search_value,
                case=False,
                na=False,
            )
            |
            filtered_inventory["product_name"]
            .astype(str)
            .str.contains(
                search_value,
                case=False,
                na=False,
            )
        ]

    if selected_warehouse != "All":

        filtered_inventory = filtered_inventory[
            filtered_inventory["warehouse_id"]
            == selected_warehouse
        ]

    if selected_status != "All":

        filtered_inventory = filtered_inventory[
            filtered_inventory["stock_status"]
            == selected_status
        ]

    # --------------------------------------------------
    # Inventory Table
    # --------------------------------------------------

    display_inventory = filtered_inventory[
        [
            "sku",
            "product_name",
            "variant",
            "warehouse_id",
            "quantity_on_hand",
            "reserved_quantity",
            "available_quantity",
            "reorder_level",
            "stock_status",
        ]
    ].copy()

    display_inventory = display_inventory.rename(
        columns={
            "sku": "SKU",
            "product_name": "Product",
            "variant": "Variant",
            "warehouse_id": "Warehouse",
            "quantity_on_hand": "On Hand",
            "reserved_quantity": "Reserved",
            "available_quantity": "Available",
            "reorder_level": "Reorder Level",
            "stock_status": "Status",
        }
    )

    st.caption(
        f"Showing {len(display_inventory)} inventory records"
    )

    if display_inventory.empty:

        st.info(
            "No inventory records match the selected filters."
        )

    else:

        st.dataframe(
            display_inventory,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # --------------------------------------------------
    # Stock Position by SKU
    # --------------------------------------------------

    st.subheader("Stock Position")

    sku_options = (
        inventory_df["sku"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    if not sku_options:
        st.info("No inventory data available.")
        return

    selected_sku = st.selectbox(
        "Select SKU",
        sku_options,
    )

    selected_product = inventory_df[
        inventory_df["sku"] == selected_sku
    ].copy()

    product_name = (
        selected_product["product_name"]
        .iloc[0]
    )

    variant = (
        selected_product["variant"]
        .iloc[0]
    )

    st.markdown(
        f"**{product_name}** — {variant}"
    )

    # --------------------------------------------------
    # Main / Secondary Comparison
    # --------------------------------------------------

    main_row = selected_product[
        selected_product["warehouse_id"]
        == "WH-MAIN"
    ]

    secondary_row = selected_product[
        selected_product["warehouse_id"]
        == "WH-SEC"
    ]

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:

        st.markdown("**Main Warehouse**")

        if not main_row.empty:

            row = main_row.iloc[0]

            st.metric(
                "Available",
                int(row["available_quantity"]),
            )

            st.write(
                f"On Hand: {int(row['quantity_on_hand'])}"
            )

            st.write(
                f"Reserved: {int(row['reserved_quantity'])}"
            )

            st.write(
                f"Reorder Level: {int(row['reorder_level'])}"
            )

        else:

            st.info(
                "No stock record in main warehouse."
            )

    with detail_col2:

        st.markdown("**Secondary Warehouse**")

        if not secondary_row.empty:

            row = secondary_row.iloc[0]

            st.metric(
                "Available",
                int(row["available_quantity"]),
            )

            st.write(
                f"On Hand: {int(row['quantity_on_hand'])}"
            )

            st.write(
                f"Reserved: {int(row['reserved_quantity'])}"
            )

            st.write(
                f"Reorder Level: {int(row['reorder_level'])}"
            )

        else:

            st.info(
                "No stock record in secondary warehouse."
            )

    # --------------------------------------------------
    # Operational Recommendation
    # --------------------------------------------------

    st.markdown("**Operational Status**")

    main_available = (
        int(main_row["available_quantity"].iloc[0])
        if not main_row.empty
        else 0
    )

    secondary_available = (
        int(secondary_row["available_quantity"].iloc[0])
        if not secondary_row.empty
        else 0
    )

    if main_available <= 0 and secondary_available > 0:

        st.warning(
            "Main warehouse has no available stock. "
            "Secondary warehouse stock is available "
            "and may require transfer before fulfillment."
        )

    elif (
        main_available <= 0
        and secondary_available <= 0
    ):

        st.error(
            "No available stock across either warehouse."
        )

    elif (
        main_available > 0
        and main_available
        <= int(main_row["reorder_level"].iloc[0])
    ):

        st.warning(
            "Main warehouse stock is low."
        )

    else:

        st.success(
            "Main warehouse has available stock."
        )

        st.divider()

    # --------------------------------------------------
    # Stock Transfer
    # --------------------------------------------------

    st.subheader("Stock Transfer")

    st.caption(
        "Transfer available stock from the secondary warehouse "
        "to the main warehouse."
    )

    transfer_col1, transfer_col2 = st.columns(2)

    with transfer_col1:

        transfer_quantity = st.number_input(
            "Transfer Quantity",
            min_value=1,
            value=1,
            step=1,
        )

    with transfer_col2:

        st.markdown("**Available for Transfer**")

        st.metric(
            "Secondary Available",
            secondary_available,
        )

    if transfer_quantity > secondary_available:

        st.error(
            "Transfer quantity exceeds available secondary stock."
        )

    if st.button(
        "Transfer to Main Warehouse",
        type="primary",
        disabled=transfer_quantity > secondary_available,
    ):

        success, message = transfer_stock(
            selected_sku,
            transfer_quantity,
        )

        if success:

            st.success(message)

            st.rerun()

        else:

            st.error(message)