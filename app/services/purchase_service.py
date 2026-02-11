from sqlalchemy.orm import Session
from app.config import settings
from app.models import Item, Slot


def purchase(db: Session, item_id: str, cash_inserted: int) -> dict:
    # Use with_for_update to lock the row during transaction
    item = db.query(Item).filter(Item.id == item_id).with_for_update().first()
    if not item:
        raise ValueError("item_not_found")
    
    # time.sleep(0.05) removed to fix race condition
    
    if item.quantity <= 0:
        raise ValueError("out_of_stock")
    if cash_inserted < item.price:
        raise ValueError("insufficient_cash", item.price, cash_inserted)
    
    # Validation for supported denominations
    # Validation for supported denominations
    # Logic note: cash_inserted must be positive.
    if cash_inserted <= 0:
        raise ValueError("invalid_cash")

    # Optional strict check: is it composed of supported denominations?
    # Given min denomination is 1, any integer > 0 is technically valid if we assume infinite supply of 1s.
    # But if we want to enforce that the USER provides valid bills/coins:
    # This is a bit complex (Knapsack-like or just set membership if single coin). 
    # For now, let's stick to positive amount as the primary fix.
    
    # The previous logic `cash_inserted % min(...) != 0` was always False because min=1.
    # We replaced it with a simple check.
    
    # We must lock the slot too to safely decrement current_item_count
    # Since we have item, we could re-query Slot with lock.
    slot = db.query(Slot).filter(Slot.id == item.slot_id).with_for_update().first()
    # slot is now locked. item.slot might refer to it or a different instance in session identity map.
    # To be safe, use the locked instance `slot`.
    
    change = cash_inserted - item.price
    item.quantity -= 1
    slot.current_item_count -= 1
    db.commit()
    db.refresh(item)
    return {
        "item": item.name,
        "price": item.price,
        "cash_inserted": cash_inserted,
        "change_returned": change,
        "remaining_quantity": item.quantity,
        "message": "Purchase successful",
    }


def change_breakdown(change: int) -> dict:
    denominations = sorted(settings.SUPPORTED_DENOMINATIONS, reverse=True)
    result: dict[str, int] = {}
    remaining = change
    for d in denominations:
        if remaining <= 0:
            break
        count = remaining // d
        if count > 0:
            result[str(d)] = count
            remaining -= count * d
    return {"change": change, "denominations": result}
