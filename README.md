# Fulfillment Hub

A lightweight operations dashboard for managing e-commerce order fulfillment, inventory readiness, courier pickups, and operational exceptions.

## Problem

The fulfillment process uses spreadsheets and shared folders to coordinate orders between the office, warehouse, and courier partners.

This can make it difficult to:

- See the current status of every order
- Identify priority orders that need attention
- Detect fulfillment delays
- Check whether inventory is available in the main warehouse
- Identify when stock needs to be transferred from a secondary warehouse
- Track courier pickup status
- Keep operational exceptions visible and assigned

Fulfillment Hub provides a single operational view of these activities.

## Key Features

### Operations Dashboard

Provides an overview of:

- Active orders
- Priority orders
- Orders at risk
- Open operational exceptions
- Priority orders requiring attention
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

### Fulfillment

The Fulfillment page provides a queue of active orders across fulfillment stages including:

- Received
- Processed
- Picking
- Picked
- Packing
- Packed
- Staged
- Awaiting Pickup

It also highlights orders requiring attention.

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

Each exception includes priority, owner, status, and timeline information.

## Business Rules

### Inventory Availability

Available inventory is calculated as:

`Available = Quantity on Hand - Reserved Quantity`

### Inventory Readiness

- **Ready** — main warehouse has enough available stock
- **Transfer Required** — main warehouse is short, but secondary warehouse can cover the shortage
- **Insufficient Stock** — combined available stock is not enough

### Order Risk

An order can be flagged when:

- Its required ship time has passed
- A priority order is approaching its required ship deadline
- Required inventory is unavailable
- Courier pickup is overdue

## Technology

- Python
- Streamlit
- Pandas
- SQLite
- Plotly

## Project Structure

```text
fulfillment-hub/
├── app.py
├── database/
│   └── fulfillment_hub.db
├── data/
├── scripts/
├── views/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── orders.py
│   └── inventory.py
├── utils/
│   ├── database.py
│   ├── calculations.py
│   └── ui.py
├── requirements.txt
└── README.md

## Author

Nikhil M. Savant

Computer Science Engineering Graduate