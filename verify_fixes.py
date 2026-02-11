import asyncio
import httpx
import time

BASE_URL = "http://127.0.0.1:8000"

async def test_slot_management():
    print("\n--- Testing Slot Management ---")
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("Creating slot A100...")
        resp = await client.post("/slots", json={"code": "A100", "capacity": 10})
        if resp.status_code == 201:
            slot_id = resp.json()["id"]
            print(f"Slot created: {slot_id}")
        else:
            print(f"Failed to create slot: {resp.text}")
            return

        # Add Item
        print("Adding items...")
        resp = await client.post(f"/slots/{slot_id}/items", json={"name": "TestItem", "price": 10, "quantity": 1})
        if resp.status_code == 201:
             print("Item added.")
        else:
             print(f"Failed to add item: {resp.text}")

        # Try to delete non-empty slot
        print("Attempting to delete non-empty slot (should fail)...")
        resp = await client.delete(f"/slots/{slot_id}")
        if resp.status_code == 400:
            print(f"Deletion blocked as expected: {resp.status_code} - {resp.text}")
        else:
            print(f"ERROR: Deletion allowed? Status: {resp.status_code}")

        # Cleanup: Remove item then delete slot
        print("Cleaning up...")
        await client.delete(f"/slots/{slot_id}/items")
        await client.delete(f"/slots/{slot_id}")
        print("Cleanup done.")

async def test_concurrency():
    print("\n--- Testing Purchase Concurrency ---")
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Setup: Create slot and 1 item
        resp = await client.post("/slots", json={"code": "C1", "capacity": 10})
        if resp.status_code != 201:
             # Try to find existing
             slots = (await client.get("/slots")).json()
             slot = next((s for s in slots if s["code"] == "C1"), None)
             if slot:
                 slot_id = slot["id"]
                 # clear it
                 await client.delete(f"/slots/{slot_id}/items")
             else:
                 print("Could not setup slot C1")
                 return
        else:
            slot_id = resp.json()["id"]

        # Add exactly 1 item
        item_resp = await client.post(f"/slots/{slot_id}/items", json={"name": "RareItem", "price": 10, "quantity": 1})
        if item_resp.status_code != 201:
            print(f"Failed to setup item: {item_resp.text}")
            return
        
        item_id = item_resp.json()["id"]
        print(f"Setup complete. Item ID: {item_id}, Qty: 1")

        # Launch 5 concurrent purchase requests
        print("Launching 5 concurrent buy requests...")
        tasks = [client.post("/purchase", json={"item_id": item_id, "cash_inserted": 10}) for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        success_count = sum(1 for r in responses if r.status_code == 200)
        fail_count = sum(1 for r in responses if r.status_code == 400)
        
        print(f"Results: Successes={success_count}, Failures={fail_count}")
        
        if success_count == 1 and fail_count == 4:
            print("PASSED: Concurrency handled correctly.")
        else:
            print(f"FAILED: Expected 1 success, got {success_count}.")

        # check final quantity
        final_item = await client.get(f"/items/{item_id}")
        if final_item.status_code == 200:
             qty = final_item.json()["quantity"]
             print(f"Final Item Quantity: {qty}")
             if qty == 0:
                 print("PASSED: Final quantity is 0.")
             else:
                 print(f"FAILED: Final quantity is {qty} (expected 0).")
        
        # Cleanup
        await client.delete(f"/slots/{slot_id}")


async def test_atomicity():
    print("\n--- Testing Bulk Add Atomicity ---")
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Setup Slot
        resp = await client.post("/slots", json={"code": "A_ATOM", "capacity": 5}) # Small capacity
        if resp.status_code == 201:
            slot_id = resp.json()["id"]
        else:
            print("Failed to create slot.")
            return

        # Attempt to add 3 valid items + 1 big item that causes overflow
        # Current logic checks total first, so it should fail immediately.
        # But if we had loop-based check, we testing that PARTIAL adds don't happen.
        
        print("Attempting bulk add that exceeds capacity...")
        payload = {
            "items": [
                {"name": "I1", "price": 10, "quantity": 2},
                {"name": "I2", "price": 10, "quantity": 2},
                {"name": "I3", "price": 10, "quantity": 10}, # This pushes total to 14 > 5
            ]
        }
        resp = await client.post(f"/slots/{slot_id}/items/bulk", json=payload)
        
        print(f"Response: {resp.status_code}")
        if resp.status_code == 400:
            print("PASSED: Request rejected.")
        else:
            print(f"FAILED: Request accepted? {resp.status_code}")

        # Verify EMPTY slot
        slot_resp = await client.get("/slots")
        curr_slot = next(s for s in slot_resp.json() if s["id"] == slot_id)
        if curr_slot["current_item_count"] == 0:
             print("PASSED: Slot is empty (Atomic rollback/check confirmed).")
        else:
             print(f"FAILED: Slot has {curr_slot['current_item_count']} items.")

        # Cleanup
        await client.delete(f"/slots/{slot_id}")

if __name__ == "__main__":
    asyncio.run(test_slot_management())
    asyncio.run(test_atomicity())
    asyncio.run(test_concurrency())
