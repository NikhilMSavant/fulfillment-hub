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

    # Remove existing database so it can be rebuilt
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)

    try:
        # --------------------------------------------------
        # Load CSV files
        # --------------------------------------------------

        products_df = pd.read_csv(DATA_DIR / "products.csv")
        inventory_df = pd.read_csv(DATA_DIR / "inventory.csv")
        orders_df = pd.read_csv(DATA_DIR / "orders.csv")
        order_items_df = pd.read_csv(DATA_DIR / "order_items.csv")
        couriers_df = pd.read_csv(DATA_DIR / "couriers.csv")
        shipments_df = pd.read_csv(DATA_DIR / "shipments.csv")
        exceptions_df = pd.read_csv(DATA_DIR / "exceptions.csv")

        # --------------------------------------------------
        # Create SQLite tables
        # --------------------------------------------------

        products_df.to_sql(
            "products",
            connection,
            if_exists="replace",
            index=False
        )

        inventory_df.to_sql(
            "inventory",
            connection,
            if_exists="replace",
            index=False
        )

        orders_df.to_sql(
            "orders",
            connection,
            if_exists="replace",
            index=False
        )

        order_items_df.to_sql(
            "order_items",
            connection,
            if_exists="replace",
            index=False
        )

        couriers_df.to_sql(
            "couriers",
            connection,
            if_exists="replace",
            index=False
        )

        shipments_df.to_sql(
            "shipments",
            connection,
            if_exists="replace",
            index=False
        )

        exceptions_df.to_sql(
            "exceptions",
            connection,
            if_exists="replace",
            index=False
        )

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
        ]

        print("\nTable row counts:")

        for table in tables:

            count = pd.read_sql_query(
                f"SELECT COUNT(*) AS count FROM {table}",
                connection
            ).iloc[0]["count"]

            print(f"{table}: {count}")

    finally:
        connection.close()


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    create_database()