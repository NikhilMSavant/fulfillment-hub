# Fulfillment Hub

A lightweight operations dashboard for managing e-commerce order fulfillment, inventory readiness, courier pickups, and operational exceptions.

## Problem

The fulfillment process uses spreadsheets and shared folders to coordinate orders between the office, warehouse, and courier partners.

This can make it difficult to:

* See the current status of every order
* Identify priority orders that need attention
* Detect fulfillment delays
* Check whether inventory is available in the main warehouse
* Identify when stock needs to be transferred from a secondary warehouse
* Track courier pickup status
* Keep operational exceptions visible and assigned

Fulfillment Hub provides a single operational view to help operators identify what is happening, what is at risk, and what needs attention next.

## Key Features

### Operations Dashboard

Provides an overview of:

* Active orders
* Priority orders
* Orders at risk
* Open operational exceptions
* Priority orders requiring attention
* Inventory problems
* Delayed orders
* Overdue courier pickups
* Fulfillment pipeline by stage

### Orders

The Orders page allows operators to:

* Search and filter orders
* Filter by fulfillment status
* Filter by priority
* Filter by operational risk
* View order details
* Track fulfillment progress
* Check inventory readiness
* Review courier and pickup information
* Identify fulfillment issues requiring attention

### Inventory

The Inventory page provides:

* Main warehouse stock
* Secondary warehouse stock
* Available stock after reservations
* Low-stock and out-of-stock identification
* SKU-level stock position
* Stock transfer from the secondary warehouse to the main warehouse

### Fulfillment

The Fulfillment page provides an operational queue across fulfillment stages, including:

* Received
* Processed
* Picking
* Picked
* Packing
* Packed
* Staged
* Awaiting Pickup

It also highlights orders that require operational attention.

### Exceptions

The Exceptions page tracks operational issues such as:

* Inventory shortages
* Stock transfer requirements
* Variant mismatches
* Picking issues
* Packing issues
* Staging issues
* Courier pickup problems
* Inventory mismatches

Each exception includes priority, owner, status, and timeline information.

## Business Rules

### Inventory Availability

Available inventory is calculated as:

`Available Quantity = Quantity on Hand - Reserved Quantity`

### Inventory Readiness

An order is classified as:

* **Ready** — the main warehouse has enough available stock.
* **Transfer Required** — the main warehouse is short, but the secondary warehouse can cover the shortage.
* **Insufficient Stock** — the combined available stock across warehouses is not enough.

### Order Risk

An order can be flagged when:

* Its required ship time has passed.
* A priority order is approaching its required ship deadline.
* Required inventory is unavailable.
* A courier pickup is overdue.

## Sample Data

The project uses self-generated sample data because the take-home project does not provide access to real store, warehouse, or courier systems.

The sample dataset includes:

* Products
* Orders
* Order items
* Warehouse inventory
* Couriers
* Shipments
* Operational exceptions

The application uses SQLite for the operational data store and includes a pre-populated sample database.

## Technology

* Python
* Streamlit
* Pandas
* SQLite
* Plotly

## Project Structure

```text
fulfillment-hub/
├── app.py
├── README.md
├── requirements.txt
├── test_calculations.py
│
├── data/
│   ├── couriers.csv
│   ├── exceptions.csv
│   ├── inventory.csv
│   ├── order_items.csv
│   ├── orders.csv
│   ├── products.csv
│   └── shipments.csv
│
├── database/
│   ├── db_setup.py
│   └── fulfillment_hub.db
│
├── scripts/
│   └── generate_data.py
│
├── utils/
│   ├── calculations.py
│   └── database.py
│
└── views/
    ├── __init__.py
    ├── dashboard.py
    ├── exceptions.py
    ├── fulfillment.py
    ├── inventory.py
    └── orders.py
```

## Running Locally

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python -m streamlit run app.py
```

The application will open in your browser at the local Streamlit address.

## Deployment

The application can be deployed using Streamlit Community Cloud by connecting the GitHub repository and selecting:

* Branch: `main`
* Main file: `app.py`

## Scope

This project focuses on operational visibility and decision support rather than replacing a full e-commerce or warehouse management system.

It does not implement:

* Real store integrations
* Real courier APIs
* Payment processing
* Barcode hardware
* GPS tracking
* ERP integration
* Customer-facing order management

## Future Improvements

Possible future improvements include:

* Integration with real e-commerce platforms
* Courier API integration
* Barcode-based picking and packing
* Automated notifications for delayed orders
* User authentication and role-based access
* Historical operational analytics
* Automated inventory synchronization

## Author

**Nikhil M. Savant**

Computer Science Engineering Graduate
