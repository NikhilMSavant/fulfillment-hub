import streamlit as st

from views.dashboard import render_dashboard
from views.orders import render_orders
from views.inventory import render_inventory
from views.fulfillment import render_fulfillment
from views.exceptions import render_exceptions
from views.warehouse import render_warehouse


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Fulfillment Hub",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

st.sidebar.title("📦 Fulfillment Hub")

st.sidebar.caption(
    "E-commerce fulfillment operations"
)

st.sidebar.divider()


# --------------------------------------------------
# Role Selection
# --------------------------------------------------

role = st.sidebar.radio(
    "Work Mode",
    [
        "Office",
        "Warehouse",
        "Manager",
    ],
    index=0,
)


st.sidebar.divider()


# --------------------------------------------------
# Navigation by Role
# --------------------------------------------------

if role == "Warehouse":

    page = st.sidebar.radio(
        "Navigate",
        [
            "Warehouse Mode",
        ],
    )

else:

    page = st.sidebar.radio(
        "Navigate",
        [
            "Dashboard",
            "Orders",
            "Inventory",
            "Fulfillment",
            "Exceptions",
        ],
    )


# --------------------------------------------------
# Role Information
# --------------------------------------------------

if role == "Warehouse":

    st.sidebar.success(
        "Warehouse Mode\n\n"
        "Use this mode for picking, packing, staging, "
        "and courier handover."
    )

elif role == "Office":

    st.sidebar.info(
        "Office Mode\n\n"
        "Use this mode for order processing and "
        "operational monitoring."
    )

else:

    st.sidebar.info(
        "Manager Mode\n\n"
        "Use this mode for monitoring fulfillment, "
        "inventory, risks, and exceptions."
    )


# --------------------------------------------------
# Page Routing
# --------------------------------------------------

if page == "Warehouse Mode":

    render_warehouse()

elif page == "Dashboard":

    render_dashboard()

elif page == "Orders":

    render_orders()

elif page == "Inventory":

    render_inventory()

elif page == "Fulfillment":

    render_fulfillment()

elif page == "Exceptions":

    render_exceptions()