# Gap Analysis: Current vs Correct Implementation

This document compares the current implementation of the Vending Machine API against the specifications defined in `api-specifications.md` and standard best practices.

## 1. Concurrency & Atomicity (Critical)

| Feature | Specification / Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Transaction Atomicity** | Transactions must be atomic. Concurrent purchases or stocking should not lead to inconsistent state (e.g., negative stock, double spending). | Code explicitly introduces `time.sleep(0.05)` in `purchase` and `bulk_add_items` to **widen the race condition window**. No locking mechanisms (optimistic or pessimistic) are used. | ❌ **Buggy** (Intentionally) |

## 2. Data Integrity (Deletion Logic)

| Feature | Specification / Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Delete Slot** | "Cannot delete if slot contains items" (Optional strict rule). | Deleting a slot does **not** check for items. `Item.slot_id` has `ondelete="SET NULL"`, meaning items become orphaned (null slot) instead of being deleted or blocking the action. | ❌ **Incorrect Behavior** |

## 3. Input Validation

| Feature | Specification / Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Cash Denominations** | `SUPPORTED_DENOMINATIONS`: [1, 2, 5, 10, 20, 50, 100]. Inputs should likely be validated against this. | Code comment in `purchase_service.py`: "No validation that cash_inserted or change use SUPPORTED_DENOMINATIONS". Accepts any integer. | ⚠️ **Missing Validation** |
| **Slot Capacity** | Total items must not exceed slot capacity. | Implemented checks for `MAX_ITEMS_PER_SLOT` and slot capacity. | ✅ **Correct** |

## 4. Performance

| Feature | Specification / Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Full View** | `GET /slots/full-view` returns slots with nested items. | Implemented, but code explicitly notes an **N+1 query problem**: `slot.items` is loaded lazily for every slot in the loop. | ⚠️ **Inefficient** |

## 5. Configuration & Models

| Feature | Specification / Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Global Config** | `MAX_SLOTS`, `MAX_ITEMS_PER_SLOT`. | Implemented in `config.py` and used in services. | ✅ **Correct** |
| **Data Models** | `Slot` and `Item` fields. | Matches spec. | ✅ **Correct** |

## Summary of Fixes Needed

1.  **Fix Concurrency**: Remove `time.sleep` calls and implement database locking (e.g., `with db.begin()`, `select for update` if supported, or check-then-act with versioning) to prevent race conditions.
2.  **Fix Slot Deletion**: Update `delete_slot` logic to check `slot.current_item_count` and raise an error if > 0, or implement cascading delete if preferred (though spec suggests blocking).
3.  **Add Validation**: Validate `cash_inserted` against `SUPPORTED_DENOMINATIONS` in `purchase` endpoint.
4.  **Optimize Query**: Rewrite `get_full_view` to use a JOIN (e.g., `joinedload`) to fetch slots and items in a single query, eliminating the N+1 problem.
