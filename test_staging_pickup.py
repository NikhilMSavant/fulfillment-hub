import subprocess
import sys

import pytest

from utils.database import (
    assign_staging_bay,
    process_courier_pickup,
    transition_order_stage,
)


@pytest.fixture(autouse=True)
def reset_database():
    subprocess.run(
        [sys.executable, "database/db_setup.py"],
        check=True,
        capture_output=True,
        text=True,
    )


def get_ord1006_courier_and_bay():
    import sqlite3

    connection = sqlite3.connect(
        "database/fulfillment_hub.db"
    )

    try:
        courier_id = connection.execute(
            """
            SELECT courier_id
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD-1006",),
        ).fetchone()[0]

        bay_id = connection.execute(
            """
            SELECT bay_id
            FROM staging_bays
            WHERE courier_id = ?
              AND active = 1
            ORDER BY bay_id
            LIMIT 1
            """,
            (courier_id,),
        ).fetchone()[0]

        return courier_id, bay_id

    finally:
        connection.close()


def test_packed_order_requires_staging_bay():
    success, message = transition_order_stage(
        "ORD-1006",
        "Staged",
        "Warehouse",
    )

    assert success is False
    assert "staging bay" in message.lower()


def test_staging_bay_must_match_courier():
    import sqlite3

    connection = sqlite3.connect(
        "database/fulfillment_hub.db"
    )

    try:
        courier_id = connection.execute(
            """
            SELECT courier_id
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD-1006",),
        ).fetchone()[0]

        wrong_bay = connection.execute(
            """
            SELECT bay_id
            FROM staging_bays
            WHERE courier_id != ?
              AND active = 1
            ORDER BY bay_id
            LIMIT 1
            """,
            (courier_id,),
        ).fetchone()[0]

    finally:
        connection.close()

    success, message = assign_staging_bay(
        "ORD-1006",
        wrong_bay,
    )

    assert success is False
    assert "courier" in message.lower()


def test_valid_staging_bay_assignment():
    courier_id, bay_id = get_ord1006_courier_and_bay()

    success, message = assign_staging_bay(
        "ORD-1006",
        bay_id,
    )

    assert success is True
    assert "assigned" in message.lower()


def test_packed_order_can_move_to_staged_after_bay_assignment():
    courier_id, bay_id = get_ord1006_courier_and_bay()

    assert assign_staging_bay(
        "ORD-1006",
        bay_id,
    )[0] is True

    success, message = transition_order_stage(
        "ORD-1006",
        "Staged",
        "Warehouse",
    )

    assert success is True
    assert "Staged" in message


def test_courier_pickup_ships_handed_over_box():
    courier_id, bay_id = get_ord1006_courier_and_bay()

    assert assign_staging_bay(
        "ORD-1006",
        bay_id,
    )[0] is True

    assert transition_order_stage(
        "ORD-1006",
        "Staged",
        "Warehouse",
    )[0] is True

    success, message = process_courier_pickup(
        courier_id,
        ["ORD-1006"],
    )

    assert success is True
    assert "1 box(es) handed over" in message

    import sqlite3

    connection = sqlite3.connect(
        "database/fulfillment_hub.db"
    )

    try:
        status = connection.execute(
            """
            SELECT status
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD-1006",),
        ).fetchone()[0]

        pickup_status = connection.execute(
            """
            SELECT pickup_status
            FROM shipments
            WHERE order_id = ?
            """,
            ("ORD-1006",),
        ).fetchone()[0]

    finally:
        connection.close()

    assert status == "Shipped"
    assert pickup_status == "Picked Up"


def test_non_handed_over_box_gets_pickup_exception():
    courier_id, bay_id = get_ord1006_courier_and_bay()

    assert assign_staging_bay(
        "ORD-1006",
        bay_id,
    )[0] is True

    assert transition_order_stage(
        "ORD-1006",
        "Staged",
        "Warehouse",
    )[0] is True

    success, message = process_courier_pickup(
        courier_id,
        [],
    )

    assert success is True

    # Other staged orders may exist for the same courier.
    # The important rule is that the test order remains staged
    # and is flagged with a pickup-missed exception.
    assert "box(es) remain staged" in message

    import sqlite3

    connection = sqlite3.connect(
        "database/fulfillment_hub.db"
    )

    try:
        status = connection.execute(
            """
            SELECT status
            FROM orders
            WHERE order_id = ?
            """,
            ("ORD-1006",),
        ).fetchone()[0]

        exception = connection.execute(
            """
            SELECT issue_type, status
            FROM exceptions
            WHERE order_id = ?
              AND issue_type = ?
            """,
            (
                "ORD-1006",
                "Courier Pickup Missed",
            ),
        ).fetchone()

    finally:
        connection.close()

    assert status == "Staged"
    assert exception is not None
    assert exception[0] == "Courier Pickup Missed"
    assert exception[1] == "Open"


def test_pickup_exception_is_not_duplicated():
    courier_id, bay_id = get_ord1006_courier_and_bay()

    assert assign_staging_bay(
        "ORD-1006",
        bay_id,
    )[0] is True

    assert transition_order_stage(
        "ORD-1006",
        "Staged",
        "Warehouse",
    )[0] is True

    first_success, _ = process_courier_pickup(
        courier_id,
        [],
    )

    second_success, _ = process_courier_pickup(
        courier_id,
        [],
    )

    assert first_success is True
    assert second_success is True

    import sqlite3

    connection = sqlite3.connect(
        "database/fulfillment_hub.db"
    )

    try:
        exception_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM exceptions
            WHERE order_id = ?
              AND issue_type = ?
            """,
            (
                "ORD-1006",
                "Courier Pickup Missed",
            ),
        ).fetchone()[0]

    finally:
        connection.close()

    assert exception_count == 1