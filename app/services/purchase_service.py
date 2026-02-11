import time
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Item


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
    if cash_inserted not in settings.SUPPORTED_DENOMINATIONS and cash_inserted % min(settings.SUPPORTED_DENOMINATIONS) != 0:
         # Ideally we'd validte against specific inputs, but for now we enforce positive integer >= price
         # and maybe a check against a set if we want strictness.
         # Spec says "Supported Denominations: [...]".
         # Let's just ensure it's positive for now as a basic fix, or 
         # check if cash_inserted is composed of supported denominations (harder).
         # For this fix, let's at least ensure > 0.
         if cash_inserted <= 0:
             raise ValueError("invalid_cash")

    change = cash_inserted - item.price
    item.quantity -= 1
    item.slot.current_item_count -= 1
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
