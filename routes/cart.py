# routes/cart.py
from fastapi import APIRouter, Depends, HTTPException
from database import db
from routes.dependencies import get_current_user
from bson import ObjectId

cart_router = APIRouter()

# Get my cart
@cart_router.get("/cart")
def get_cart(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    cart = db.carts.find_one({"user": user_email})
    if not cart:
        return {"items": []}

    items = []
    for item in cart.get("items", []):
        prop = db.properties.find_one({"_id": ObjectId(item["propertyId"])})
        if prop:
            prop["_id"] = str(prop["_id"])
            items.append(prop)
    return {"items": items}

# Add to cart
@cart_router.post("/cart/{property_id}")
def add_to_cart(property_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    cart = db.carts.find_one({"user": user_email})
    if not cart:
        db.carts.insert_one({"user": user_email, "items": [{"propertyId": property_id}]})
    else:
        db.carts.update_one(
            {"user": user_email},
            {"$addToSet": {"items": {"propertyId": property_id}}}
        )

    return {"message": "Added to cart"}

# Remove from cart
@cart_router.delete("/cart/{property_id}")
def remove_from_cart(property_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    db.carts.update_one(
        {"user": user_email},
        {"$pull": {"items": {"propertyId": property_id}}}
    )
    return {"message": "Removed from cart"}
