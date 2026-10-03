import streamlit as st
import pandas as pd

from utils.database import run_query


def render_exceptions():

    st.title("Exceptions")

    st.caption(
        "Track operational issues, ownership, and resolution status."
    )

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------

    exceptions_df = run_query(
        "SELECT * FROM exceptions"
    )

    # --------------------------------------------------
    # Prepare Data
    # --------------------------------------------------

    exceptions_df["created_at"] = pd.to_datetime(
        exceptions_df["created_at"],
        errors="coerce",
    )

    exceptions_df["resolved_at"] = pd.to_datetime(
        exceptions_df["resolved_at"],
        errors="coerce",
    )

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------

    open_count = len(
        exceptions_df[
            exceptions_df["status"] == "Open"
        ]
    )

    in_progress_count = len(
        exceptions_df[
            exceptions_df["status"] == "In Progress"
        ]
    )

    high_priority_count = len(
        exceptions_df[
            (exceptions_df["priority"] == "High")
            & (
                exceptions_df["status"]
                != "Resolved"
            )
        ]
    )

    resolved_count = len(
        exceptions_df[
            exceptions_df["status"] == "Resolved"
        ]
    )

    st.subheader("Exception Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Open",
            open_count,
        )

    with col2:
        st.metric(
            "In Progress",
            in_progress_count,
        )

    with col3:
        st.metric(
            "High Priority",
            high_priority_count,
        )

    with col4:
        st.metric(
            "Resolved",
            resolved_count,
        )

    st.divider()

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    st.subheader("Exception Queue")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:

        status_options = [
            "All"
        ] + sorted(
            exceptions_df["status"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Status",
            status_options,
        )

    with filter_col2:

        priority_options = [
            "All"
        ] + sorted(
            exceptions_df["priority"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_priority = st.selectbox(
            "Priority",
            priority_options,
        )

    with filter_col3:

        owner_options = [
            "All"
        ] + sorted(
            exceptions_df["owner"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_owner = st.selectbox(
            "Owner",
            owner_options,
        )

    with filter_col4:

        issue_options = [
            "All"
        ] + sorted(
            exceptions_df["issue_type"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_issue = st.selectbox(
            "Issue Type",
            issue_options,
        )

    # --------------------------------------------------
    # Apply Filters
    # --------------------------------------------------

    filtered = exceptions_df.copy()

    if selected_status != "All":

        filtered = filtered[
            filtered["status"]
            == selected_status
        ]

    if selected_priority != "All":

        filtered = filtered[
            filtered["priority"]
            == selected_priority
        ]

    if selected_owner != "All":

        filtered = filtered[
            filtered["owner"]
            == selected_owner
        ]

    if selected_issue != "All":

        filtered = filtered[
            filtered["issue_type"]
            == selected_issue
        ]

    # --------------------------------------------------
    # Exception Table
    # --------------------------------------------------

    display_df = filtered[
        [
            "exception_id",
            "order_id",
            "issue_type",
            "priority",
            "status",
            "owner",
            "created_at",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "exception_id": "Exception ID",
            "order_id": "Order ID",
            "issue_type": "Issue",
            "priority": "Priority",
            "status": "Status",
            "owner": "Owner",
            "created_at": "Created",
        }
    )

    display_df["Created"] = (
        display_df["Created"]
        .dt.strftime("%d %b %Y %H:%M")
    )

    st.caption(
        f"Showing {len(display_df)} exceptions"
    )

    if display_df.empty:

        st.info(
            "No exceptions match the selected filters."
        )

    else:

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # --------------------------------------------------
    # Exception Details
    # --------------------------------------------------

    st.subheader("Exception Details")

    available_exception_ids = (
        filtered["exception_id"]
        .dropna()
        .tolist()
    )

    if not available_exception_ids:

        st.info(
            "Select different filters to view an exception."
        )
        return

    selected_exception_id = st.selectbox(
        "Select an exception",
        available_exception_ids,
    )

    selected_exception = filtered[
        filtered["exception_id"]
        == selected_exception_id
    ].iloc[0]

    detail_col1, detail_col2, detail_col3 = st.columns(3)

    with detail_col1:

        st.markdown("**Exception Information**")

        st.write(
            f"**Exception ID:** "
            f"{selected_exception['exception_id']}"
        )

        st.write(
            f"**Order ID:** "
            f"{selected_exception['order_id']}"
        )

        st.write(
            f"**Issue Type:** "
            f"{selected_exception['issue_type']}"
        )

    with detail_col2:

        st.markdown("**Ownership**")

        st.write(
            f"**Priority:** "
            f"{selected_exception['priority']}"
        )

        st.write(
            f"**Owner:** "
            f"{selected_exception['owner']}"
        )

        st.write(
            f"**Status:** "
            f"{selected_exception['status']}"
        )

    with detail_col3:

        st.markdown("**Timeline**")

        created_at = selected_exception["created_at"]

        if pd.notna(created_at):

            st.write(
                f"**Created:** "
                f"{created_at.strftime('%d %b %Y %H:%M')}"
            )

        resolved_at = selected_exception["resolved_at"]

        if pd.notna(resolved_at):

            st.write(
                f"**Resolved:** "
                f"{resolved_at.strftime('%d %b %Y %H:%M')}"
            )

        else:

            st.write(
                "**Resolved:** Not yet resolved"
            )

    # --------------------------------------------------
    # Description
    # --------------------------------------------------

    st.markdown("**Issue Description**")

    st.info(
        selected_exception["description"]
    )

    # --------------------------------------------------
    # Current Action
    # --------------------------------------------------

    if selected_exception["status"] == "Open":

        st.warning(
            "This exception is open and requires follow-up."
        )

    elif selected_exception["status"] == "In Progress":

        st.warning(
            "This exception is currently being worked on."
        )

    else:

        st.success(
            "This exception has been resolved."
        )