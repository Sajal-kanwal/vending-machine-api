# Vending Machine API Workflow

This document outlines the workflow, architecture, and logic of the Vending Machine API.

## 1. Project Overview

The project is a FastAPI-based application designed to simulate a pending machine's backend.
- **Entry Point**: `app/main.py` initializes the FastAPI app and includes routers.
- **Database**: Uses SQLAlchemy with SQLite (inferred from `db.py` and `models.py` usage, though `db.py` content wasn't fully shown, it's standard pattern).
- **Architecture**: Follows a layered architecture: `Routers -> Services -> Database Models`.

## 2. Key Entities

- **Slot**: Represents a physical slot in the vending machine (e.g., "A1", "B2"). It has a capacity and holds items.
- **Item**: specific products placed within a slot. Each item has a name, price, and quantity.
- **Purchase**: Represents a transaction where a user buys an item.

## 3. Workflow & Services

### 3.1. Slot Management (Admin/Setup)

**Service**: `app.services.slot_service`
**Router**: `app.routers.slots`

- **Create a Slot**:
  - **Endpoint**: `POST /slots`
  - **Logic**: validatest hat the maximum number of slots (`MAX_SLOTS`) hasn't been reached and that the slot code is unique. initializes capacity.
- **List Slots**:
  - **Endpoint**: `GET /slots`
  - **Logic**: Returns all defined slots with their current status (capacity, item count).
- **Full View**:
  - **Endpoint**: `GET /slots/full-view`
  - **Logic**: Returns a nested structure of slots and their contained items. *Note: Currently implemented with an N+1 query pattern.*
- **Delete Slot**:
  - **Endpoint**: `DELETE /slots/{slot_id}`
  - **Logic**: Removes a slot from the system.

### 3.2. Item Management (Stocking)

**Service**: `app.services.item_service`
**Router**: `app.routers.items` & `app.routers.slots`

- **Add Item to Slot**:
  - **Endpoint**: `POST /slots/{slot_id}/items`
  - **Logic**: Checks slot capacity before adding. If `MAX_ITEMS_PER_SLOT` or slot capacity is exceeded, it raises an error.
- **Bulk Add Items**:
  - **Endpoint**: `POST /slots/{slot_id}/items/bulk`
  - **Logic**: Adds multiple items at once. Includes a simulated delay (`time.sleep(0.05)`) to demonstrate race conditions during concurrent operations.
- **Update Price**:
  - **Endpoint**: `PATCH /items/{item_id}/price`
  - **Logic**: Updates the price of a specific item.
- **Remove Items**:
  - **Endpoint**: `DELETE /slots/{slot_id}/items/{item_id}` (Single) or `DELETE /slots/{slot_id}/items` (Bulk)
  - **Logic**: Removes specific quantities or clears a slot entirely.

### 3.3. Purchase Flow (Customer)

**Service**: `app.services.purchase_service`
**Router**: `app.routers.purchase`

- **Purchase Item**:
  - **Endpoint**: `POST /purchase`
  - **Payload**: `item_id`, `cash_inserted`
  - **Logic**:
    1.  **Validation**: Checks if item exists and is in stock.
    2.  **Concurrency Testing**: specific `time.sleep(0.05)` is added to widen the race condition window, allowing demonstration of double-booking or stock issues if not handled correctly.
    3.  **Payment**: Verifies `cash_inserted >= item.price`.
    4.  **Transaction**: Decrements item quantity and slot count. Calculates change.
    5.  **Return**: Returns success message, change amount, and remaining quantity.
- **Change Breakdown**:
  - **Endpoint**: `GET /purchase/change-breakdown`
  - **Logic**: helper utility to calculate the optimal breakdown of a change amount into supported denominations.

## 4. Technical Constraints & Features

- **Concurrency**: explicit sleeps are introduced in `purchase` and `bulk_add_items` to simulate and test concurrency issues (Race Conditions).
- **Validation**:
  - Capacity checks for slots.
  - Unique constraint on slot codes.
  - Basic input validation (positive numbers for prices/quantities).
