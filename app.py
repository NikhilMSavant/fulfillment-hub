import streamlit as st

from views.dashboard import render_dashboard
from views.orders import render_orders
from views.inventory import render_inventory
from views.fulfillment import render_fulfillment
from views.exceptions import render_exceptions

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
# Sidebar Navigation
# --------------------------------------------------

st.sidebar.title("📦 Fulfillment Hub")

st.sidebar.caption(
    "E-commerce fulfillment operations"
)

st.sidebar.divider()

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
# Page Routing
# --------------------------------------------------

if page == "Dashboard":

    render_dashboard()

elif page == "Orders":

    render_orders()

elif page == "Inventory":

    render_inventory()

elif page == "Fulfillment":

    render_fulfillment()

elif page == "Exceptions":

    render_exceptions()