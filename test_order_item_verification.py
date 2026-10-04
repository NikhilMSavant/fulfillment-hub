import sqlite3
import subprocess
import sys

import pytest

from utils.database import verify_order_item_in_db



DB_PATH = "database/fulfillment_hub.db"


@pytest.fixture(autouse=True)
def reset_database():
    subprocess.run(
        [sys.executable, "database/db_setup.py"],
        check=True,
        capture_output=True,
        text=True,
    )

def get_connection():
    return sqlite3.connect(DB_PATH)


def test_valid_picking_verification():
    success, message = verify_order_item_in_db(
        order_item_id="OI-0001",
        scanned_sku="SKU-001",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="Black - 500ml",
        verified_quantity=5,
        stage="Picking",
        user_role="Warehouse",
    )

    assert success is True
    assert message == "Item and quantity verified successfully."

    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            order_item_id,
            stage,
            verified_sku,
            verified_product_name,
            verified_variant,
            verified_quantity,
            user_role
        FROM order_item_verifications
        WHERE order_item_id = ?
          AND stage = ?
        ORDER BY verification_id DESC
        LIMIT 1
        """,
        ("OI-0001", "Picking"),
    ).fetchone()

    connection.close()

    assert row == (
        "OI-0001",
        "Picking",
        "SKU-001",
        "Stainless Steel Bottle",
        "Black - 500ml",
        5,
        "Warehouse",
    )


def test_wrong_sku_rejected_and_exception_created():
    success, message = verify_order_item_in_db(
        order_item_id="OI-0002",
        scanned_sku="SKU-999",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="Black - 750ml",
        verified_quantity=5,
        stage="Picking",
        user_role="Warehouse",
    )

    assert success is False
    assert "Wrong item" in message

    connection = get_connection()

    verification_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM order_item_verifications
        WHERE order_item_id = ?
          AND stage = ?
        """,
        ("OI-0002", "Picking"),
    ).fetchone()[0]

    exception = connection.execute(
        """
        SELECT issue_type, status, owner
        FROM exceptions
        WHERE order_id = ?
          AND issue_type = ?
        """,
        ("ORD-1002", "Variant Mismatch"),
    ).fetchone()

    connection.close()

    assert verification_count == 0
    assert exception == ("Variant Mismatch", "Open", "Warehouse")


def test_wrong_variant_rejected():
    success, message = verify_order_item_in_db(
        order_item_id="OI-0003",
        scanned_sku="SKU-003",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="Wrong Variant",
        verified_quantity=5,
        stage="Picking",
        user_role="Warehouse",
    )

    assert success is False
    assert "Wrong variant" in message

    connection = get_connection()

    verification_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM order_item_verifications
        WHERE order_item_id = ?
          AND stage = ?
        """,
        ("OI-0003", "Picking"),
    ).fetchone()[0]

    connection.close()

    assert verification_count == 0


def test_quantity_mismatch_rejected_without_verification():
    success, message = verify_order_item_in_db(
        order_item_id="OI-0004",
        scanned_sku="SKU-004",
        scanned_product_name="Stainless Steel Bottle",
        scanned_variant="White - 750ml",
        verified_quantity=1,
        stage="Picking",
        user_role="Warehouse",
    )

    assert success is False
    assert "Quantity mismatch" in message

    connection = get_connection()

    verification_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM order_item_verifications
        WHERE order_item_id = ?
          AND stage = ?
        """,
        ("OI-0004", "Picking"),
    ).fetchone()[0]

    connection.close()

    assert verification_count == 0


def test_invalid_verification_stage_rejected():
    success, message = verify_order_item_in_db(
        order_item_id="OI-0005",
        scanned_sku="SKU-005",
        scanned_product_name="Canvas Tote Bag",
        scanned_variant="Natural - Small",
        verified_quantity=1,
        stage="Staged",
        user_role="Warehouse",
    )

    assert success is False
    assert "only allowed during Picking or Packing" in message