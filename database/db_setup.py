import sqlite3
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "database" / "fulfillment_hub.db"


# --------------------------------------------------
# Database Setup
# --------------------------------------------------

def create_database():
    """Rebuild the demo SQLite database from the generated CSV files."""

    # --------------------------------------------------
    # Remove existing database so it can be rebuilt
    # --------------------------------------------------

    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)

    try:
        # --------------------------------------------------
        # Load CSV files
        # --------------------------------------------------

        products_df = pd.read_csv(
            DATA_DIR / "products.csv"
        )

        inventory_df = pd.read_csv(
            DATA_DIR / "inventory.csv"
        )

        orders_df = pd.read_csv(
            DATA_DIR / "orders.csv"
        )

        order_items_df = pd.read_csv(
            DATA_DIR / "order_items.csv"
        )

        couriers_df = pd.read_csv(
            DATA_DIR / "couriers.csv"
        )

        shipments_df = pd.read_csv(
            DATA_DIR / "shipments.csv"
        )

        exceptions_df = pd.read_csv(
            DATA_DIR / "exceptions.csv"
        )

        # --------------------------------------------------
        # Create base SQLite tables
        # --------------------------------------------------

        products_df.to_sql(
            "products",
            connection,
            if_exists="replace",
            index=False,
        )

        inventory_df.to_sql(
            "inventory",
            connection,
            if_exists="replace",
            index=False,
        )

        orders_df.to_sql(
            "orders",
            connection,
            if_exists="replace",
            index=False,
        )

        order_items_df.to_sql(
            "order_items",
            connection,
            if_exists="replace",
            index=False,
        )

        couriers_df.to_sql(
            "couriers",
            connection,
            if_exists="replace",
            index=False,
        )

        shipments_df.to_sql(
            "shipments",
            connection,
            if_exists="replace",
            index=False,
        )

        exceptions_df.to_sql(
            "exceptions",
            connection,
            if_exists="replace",
            index=False,
        )

        # --------------------------------------------------
        # Order Event Audit Table
        # --------------------------------------------------

        connection.execute(
            """
            CREATE TABLE order_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                user_role TEXT NOT NULL,
                event_timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
            )
            """
        )


        # --------------------------------------------------
        # Order Item Verification Audit Table
        # --------------------------------------------------

        connection.execute(
            """
            CREATE TABLE order_item_verifications (
                verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_item_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                verified_sku TEXT NOT NULL,
                verified_product_name TEXT NOT NULL,
                verified_variant TEXT NOT NULL,
                verified_quantity INTEGER NOT NULL,
                user_role TEXT NOT NULL,
                verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_item_id)
                    REFERENCES order_items(order_item_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX idx_order_item_verifications_item_stage
            ON order_item_verifications(order_item_id, stage)
            """
        )

        connection.execute(
            """
            CREATE INDEX idx_order_events_order
            ON order_events(order_id)
            """
        )

        # --------------------------------------------------
        # Stock Movement Audit Table
        # --------------------------------------------------

        connection.execute(
            """
            CREATE TABLE stock_movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                quantity_delta INTEGER NOT NULL,
                reference_type TEXT,
                reference_id TEXT,
                reason TEXT NOT NULL,
                user_role TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sku)
                    REFERENCES products(sku)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX idx_stock_movements_sku
            ON stock_movements(sku)
            """
        )

        # --------------------------------------------------
        # Staging Bays
        # --------------------------------------------------

        staging_bays = pd.DataFrame(
            [
                {
                    "bay_id": "A1",
                    "courier_id": "C001",
                    "bay_label": "Bay A1",
                    "active": 1,
                },
                {
                    "bay_id": "A2",
                    "courier_id": "C001",
                    "bay_label": "Bay A2",
                    "active": 1,
                },
                {
                    "bay_id": "A3",
                    "courier_id": "C002",
                    "bay_label": "Bay A3",
                    "active": 1,
                },
                {
                    "bay_id": "A4",
                    "courier_id": "C002",
                    "bay_label": "Bay A4",
                    "active": 1,
                },
                {
                    "bay_id": "B1",
                    "courier_id": "C003",
                    "bay_label": "Bay B1",
                    "active": 1,
                },
                {
                    "bay_id": "B2",
                    "courier_id": "C003",
                    "bay_label": "Bay B2",
                    "active": 1,
                },
                {
                    "bay_id": "B3",
                    "courier_id": "C001",
                    "bay_label": "Bay B3",
                    "active": 1,
                },
                {
                    "bay_id": "B4",
                    "courier_id": "C002",
                    "bay_label": "Bay B4",
                    "active": 1,
                },
            ]
        )

        staging_bays.to_sql(
            "staging_bays",
            connection,
            if_exists="replace",
            index=False,
        )

        # --------------------------------------------------
        # Exception Reference Fields
        # --------------------------------------------------

        connection.execute(
            """
            ALTER TABLE exceptions
            ADD COLUMN reference_type TEXT
            """
        )

        connection.execute(
            """
            ALTER TABLE exceptions
            ADD COLUMN reference_id TEXT
            """
        )


        # --------------------------------------------------
        # Exception Duplicate Protection
        # --------------------------------------------------

        connection.execute(
            """
            CREATE UNIQUE INDEX idx_exceptions_order_issue
            ON exceptions(order_id, issue_type)
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX idx_exceptions_reference_issue
            ON exceptions(reference_type, reference_id, issue_type)
            """
        )


        # --------------------------------------------------
        # Commit
        # --------------------------------------------------

        connection.commit()

        print("Database created successfully.")
        print(f"Database path: {DB_PATH}")

        # --------------------------------------------------
        # Verify row counts
        # --------------------------------------------------

        tables = [
            "products",
            "inventory",
            "orders",
            "order_items",
            "couriers",
            "shipments",
            "exceptions",
            "order_events",
            "order_item_verifications",
            "stock_movements",
            "staging_bays",
        ]

        print("\nTable row counts:")

        for table in tables:

            count = pd.read_sql_query(
                f"SELECT COUNT(*) AS count FROM {table}",
                connection,
            ).iloc[0]["count"]

            print(f"{table}: {count}")

    finally:
        connection.close()


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    create_database()
