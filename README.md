# Fulfillment Hub

A lightweight operations dashboard for managing e-commerce order fulfillment, inventory readiness, courier pickups, and operational exceptions.

**Hosted Application:**

https://nikhil-fulfillment.streamlit.app/

**GitHub Repository:**

https://github.com/NikhilMSavant/fulfillment-hub

---

## Problem

The fulfillment process uses spreadsheets and shared folders to coordinate orders between the office, warehouse, and courier partners.

This can make it difficult to:

- See the current status of every order
- Identify priority orders that need attention
- Detect fulfillment delays
- Check whether inventory is available in the main warehouse
- Identify when stock needs to be transferred from a secondary warehouse
- Detect wrong products, variants, or quantities
- Track packed boxes and staging locations
- Track courier pickup status
- Keep operational exceptions visible and assigned

Fulfillment Hub provides a single operational view to help operators identify what is happening, what is at risk, and what needs attention next.

---

## Solution

The application models the complete fulfillment workflow:

**Received → Processed → Picking → Picked → Packing → Packed → Staged → Awaiting Pickup → Shipped**

The design focuses on the operational problems described in the take-home rather than attempting to replace a full warehouse management or e-commerce system.

---

## Key Features

### Operations Dashboard

Provides an overview of:

- Active orders
- Priority orders
- Orders at risk
- Open operational exceptions
- Inventory problems
- Delayed orders
- Overdue courier pickups
- Fulfillment pipeline by stage

### Orders

The Orders page allows operators to:

- Search and filter orders
- Filter by fulfillment status
- Filter by priority
- Filter by operational risk
- View order details
- Track fulfillment progress
- Check inventory readiness
- Review courier and pickup information
- Identify fulfillment issues requiring attention

### Inventory

The Inventory page provides:

- Main warehouse stock
- Secondary warehouse stock
- Available stock after reservations
- Low-stock and out-of-stock identification
- SKU-level stock position
- Stock transfer from the secondary warehouse to the main warehouse
- Inventory adjustment tracking

### Fulfillment

The Fulfillment page provides an operational queue across fulfillment stages:

- Received
- Processed
- Picking
- Picked
- Packing
- Packed
- Staged
- Awaiting Pickup
- Shipped

Stage transitions are controlled so that orders cannot skip required steps.

### Warehouse Mode

Warehouse Mode provides a simplified interface designed for warehouse operators who may not be comfortable with complex software.

It provides:

- A focused worklist
- Picking, packing, staging, and pickup queues
- Priority and deadline visibility
- Large action controls
- Order-level work screens
- Product, variant, SKU, quantity, and shelf-location information
- Find a Box functionality
- Courier Pickup processing

### Item Verification

Before an order can move through picking and packing, warehouse operators can verify:

- Product
- SKU
- Variant
- Quantity

Incorrect items, variants, or quantities are rejected and can generate an operational exception.

Successful verifications are recorded for auditability, and duplicate verification for the same item and stage is prevented.

### Staging

Packed orders can be assigned to staging bays associated with their courier.

The application records the staging location and keeps staged orders visible before courier pickup.

### Courier Pickup

The Courier Pickup workflow allows warehouse operators to:

- Select a courier
- View staged orders awaiting pickup
- Record which boxes were handed over
- Mark handed-over orders as shipped
- Record pickup status and pickup time
- Create an exception when a staged order is missed during pickup

### Find a Box

Warehouse operators can search for an order and quickly identify:

- Current fulfillment stage
- Courier
- Staging bay
- Pickup status
- Other relevant fulfillment information

This helps locate boxes without searching through spreadsheets or shared folders.

### Exceptions

The Exceptions page tracks operational issues such as:

- Inventory shortages
- Stock transfer requirements
- Variant mismatches
- Picking issues
- Packing issues
- Staging issues
- Courier pickup problems
- Inventory mismatches

Each exception includes information such as:

- Priority
- Owner
- Status
- Created time
- Resolution time where applicable

---

## Business Rules

### Inventory Availability

Available inventory is calculated as:

`Available Quantity = Quantity on Hand - Reserved Quantity`

### Inventory Readiness

An order is classified as:

- **Ready** — the main warehouse has enough available stock.
- **Transfer Required** — the main warehouse is short, but the secondary warehouse can cover the shortage.
- **Insufficient Stock** — the combined available stock across warehouses is not enough.

Stock transfers from the secondary warehouse to the main warehouse are recorded as inventory movements.

### Fulfillment Stage Control

Orders must follow the defined fulfillment sequence.

For example:

- An order cannot move directly from Processed to Picked.
- Picking requires sufficient main-warehouse inventory.
- Picking and packing require item verification.
- Packing requires shipment and staging information.
- Packed orders must be assigned to a valid courier-specific staging bay before being staged.

### Order Risk

An order can be flagged when:

- Its required ship time has passed.
- A priority order is approaching its required ship deadline.
- Required inventory is unavailable.
- A courier pickup is overdue.

---

## Auditability

Important operational actions are recorded so that changes can be traced.

The application maintains records for:

- Order stage transitions
- Item verification
- Inventory movements
- Inventory adjustments
- Operational exceptions
- Courier pickup activity

This provides a basic operational history without requiring a full enterprise warehouse management system.

---

## Sample Data

The project uses self-generated sample data because the take-home project does not provide access to real store, warehouse, or courier systems.

The sample dataset includes:

- 40 products
- 240 orders
- Order items
- Main warehouse inventory
- Secondary warehouse inventory
- 3 couriers
- Shipments
- Operational exceptions
- Staging bays

The application uses SQLite for the operational data store and includes a pre-populated sample database.

---

## Technology

- Python
- Streamlit
- Pandas
- SQLite
- Plotly

---

## Project Structure

```text
fulfillment-hub/
├── app.py
├── README.md
├── requirements.txt
├── test_calculations.py
├── test_staging_pickup.py
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
    ├── orders.py
    └── warehouse.py


Author

Nikhil M. Savant

Computer Science Engineering Graduate

Author's Note

This project was designed around the operational problems described in the XYZ fulfillment scenario, with a focus on practical usability for office and warehouse teams.

The goal was not to build a large enterprise system, but to create a simple workflow that makes order status, inventory readiness, fulfillment risks, verification, staging, courier pickup, and exceptions easier to manage.

AI tools were used as a development and review assistant for requirement breakdown, implementation ideas, debugging, edge-case analysis, and reviewing the workflow. Final design decisions, implementation, testing, and verification were performed and evaluated against the requirements of the assignment.