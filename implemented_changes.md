# implemented_changes.md

## Overview
This document details the bug fixes and improvements implemented in the Vending Machine API project. All changes were made to align the codebase with the `api-specifications.md` and to address critical issues such as race conditions, data integrity flaws, and performance bottlenecks.

## 1. Slot Management (`app/routers/slots.py` & `app/services/slot_service.py`)

### A. N+1 Query Problem
*   **Change**: Modified `get_full_view` to use `joinedload(Slot.items)`.
    *   **Previous**: Used a loop to fetch items for each slot individually (`lazy="select"`), causing N+1 database queries.
    *   **New**: `db.query(Slot).options(joinedload(Slot.items)).all()` fetches all slots and their items in a single query.
*   **Reasoning**: Greatly improves performance, especially as the number of slots increases.

### B. Deletion Logic (Data Integrity)
*   **Change**: Added a check in `delete_slot` to raise a `ValueError("slot_not_empty")` if the slot has items.
    *   **Logic**: Before deleting, we check `slot.current_item_count`. If greater than 0, we block the deletion.
    *   **Router Update**: Added an exception handler in `app/routers/slots.py` to map this error to `HTTP 400 Bad Request`.
*   **Reasoning**: Prevents accidental data loss or "orphaning" of items. The specification states a slot cannot be deleted if it contains items.

## 2. Item Management (`app/services/item_service.py`)

### A. Logical Error in Capacity Check
*   **Change**: Corrected the capacity check logic in `add_item_to_slot`.
    *   **Previous**: `if ... < MAX_ITEMS_PER_SLOT: raise ValueError("capacity_exceeded")` (incorrectly raising error when *under* limit).
    *   **New**: `if ... > MAX_ITEMS_PER_SLOT: raise ValueError("capacity_exceeded")` (only raise if count *exceeds* limit).
*   **Reasoning**: The previous code was logically broken, rejecting valid additions.

### B. Atomicity in Bulk Import
*   **Change**: Moved `db.commit()` outside the loop in `bulk_add_items`.
    *   **Previous**: Committed after every single item insertion.
    *   **New**: Commits once at the end of the operation.
*   **Reasoning**: Ensures atomicity (All-or-Nothing). If the 5th item fails validation, the previous 4 should not be persisted. This prevents partial data states.

### C. Timestamp Update
*   **Change**: Removed the code that manually reverted `updated_at` in `update_item_price`.
    *   **Previous**: Explicitly set `item.updated_at = prev_updated`.
    *   **New**: Allowed SQLAlchemy to automatically update the timestamp.
*   **Reasoning**: Updates should reflect when they happened. Reverting the timestamp was hiding the modification.

## 3. Purchasing (`app/services/purchase_service.py`)

### A. Critical Race Condition
*   **Change**:
    1.  Removed `time.sleep(0.05)`.
    2.  Added `with_for_update()` to the item query: `db.query(Item)...with_for_update().first()`.
*   **Reasoning**:
    *   The `sleep` was artificially creating a race window.
    *   `with_for_update()` locks the row for the duration of the transaction. This prevents two concurrent requests from reading the same stock quantity (e.g., "1") and both successfully decrementing it, leading to negative inventory ("-1").

### B. Input Validation
*   **Change**: Added a check that `cash_inserted > 0`.
*   **Reasoning**: Basic sanity check. While full denomination validation wasn't strictly enforced, ensuring positive cash is a minimum requirement.

## 4. Configuration & Models

### A. Supported Denominations
*   **Change**: Updated `SUPPORTED_DENOMINATIONS` in `app/config.py` to include `1` and `2`.
    *   **Previous**: `[5, 10, 20, 50, 100]`
    *   **New**: `[1, 2, 5, 10, 20, 50, 100]`
*   **Reasoning**: Alignment with `api-specifications.md` which lists `[1, 2, 5, 10, 20, 50, 100]`. This ensures low-value transactions or change breakdown works as expected for all defined values.

### B. Cascade Delete (`app/models.py`)
*   **Change**: Updated `Item.slot_id` foreign key to `ondelete="CASCADE"`.
    *   **Previous**: `ondelete="SET NULL"`.
    *   **New**: If a slot is deleted (and the application logic allows it), the items within it are also deleted.
*   **Reasoning**: Aligns the database schema with the physical reality (removing a tray removes its contents) and prevents orphaned item records with `slot_id=NULL`.

### C. Schema Consistency (`app/schemas.py`)
*   **Change**: Updated `ItemPriceUpdate` validation from `price > 0` (`gt=0`) to `price >= 0` (`ge=0`).
*   **Reasoning**: `ItemCreate` allows price of 0 (free items), so updates should also allow it. Fixed inconsistency.

### D. Slot Count Race Condition (`app/services/purchase_service.py`)
*   **Change**: Added explicit row locking for the `Slot` during a purchase.
    *   **Logic**: `slot = db.query(Slot).filter(Slot.id == item.slot_id).with_for_update().first()`
*   **Reasoning**: While `Item` was locked, two concurrent purchases of *different* items in the *same* slot could race to update `Slot.current_item_count`. Locking the slot ensures the count decrements are serialized safely.
