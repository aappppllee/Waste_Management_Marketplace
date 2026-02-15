from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import CartItem, Product, User, Purchase, PurchaseItem # Ensure all are imported
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

cart_bp = Blueprint('cart_bp', __name__)

@cart_bp.route('/cart', methods=['GET'])
@jwt_required()
def get_cart_items():
    """
    Gets all items in the current user's shopping cart.
    Requires authentication.
    """
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user: 
        return jsonify({"msg":"Authenticated user not found"}), 404 # Should be rare if token is valid
    
    cart_items_query = CartItem.query.filter_by(user_id=current_user_id_int).all()
    return jsonify([item.to_dict() for item in cart_items_query]), 200

@cart_bp.route('/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    """
    Adds a product to the current user's cart or updates its quantity if already present.
    Requires authentication.
    Expects 'productId' (number) and optionally 'quantity' (number) in JSON body.
    """
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    user = User.query.get(current_user_id_int)
    if not user: 
        return jsonify({"msg":"Authenticated user not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"msg": "Request body is missing or not JSON"}), 400

    product_id = data.get('productId') # Frontend sends this as number (Product.id)
    quantity_req = data.get('quantity', 1) # Default to 1

    if product_id is None: # Check for None explicitly
        return jsonify({"msg": "productId is required"}), 400
    
    try:
        # Ensure product_id is an int for DB query
        product_id = int(product_id) 
        quantity = int(quantity_req)
        if quantity < 1:
            return jsonify({"msg": "Quantity must be at least 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid productId or quantity format. Must be integers."}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404
    
    if product.seller_id == current_user_id_int:
        return jsonify({"msg": "You cannot add your own product to the cart"}), 403

    cart_item = CartItem.query.filter_by(user_id=current_user_id_int, product_id=product_id).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user_id_int, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding to cart for user {current_user_id_int}, product {product_id}: {str(e)}")
        return jsonify({"msg": "Failed to add item to cart due to a server error"}), 500
        
    # For consistency, refetch the cart to send back the full updated cart state
    # This helps if multiple operations happen quickly or if totals are complex.
    # Alternatively, just return the created/updated cart_item.to_dict()
    updated_cart_items = CartItem.query.filter_by(user_id=current_user_id_int).all()
    return jsonify({
        "msg": "Item added/updated in cart",
        "item": cart_item.to_dict(), # The specific item affected
        "cart": [item.to_dict() for item in updated_cart_items] # The full updated cart
    }), 200 if cart_item.quantity > quantity else 201


@cart_bp.route('/cart/item/<int:product_id_in_cart>', methods=['PUT'])
@jwt_required()
def update_cart_item_quantity(product_id_in_cart):
    """
    Updates the quantity of a specific product in the current user's cart.
    product_id_in_cart is Product.id.
    """
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user: return jsonify({"msg":"Authenticated user not found"}), 404

    data = request.get_json()
    if not data or 'quantity' not in data:
        return jsonify({"msg": "Quantity is required in request body"}), 400
    
    try:
        quantity = int(data['quantity'])
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid quantity format. Must be an integer."}), 400

    cart_item = CartItem.query.filter_by(user_id=current_user_id_int, product_id=product_id_in_cart).first()
    if not cart_item:
        return jsonify({"msg": "Product not found in cart"}), 404

    if quantity < 1:
        db.session.delete(cart_item)
        msg = "Item removed from cart as quantity was less than 1."
    else:
        cart_item.quantity = quantity
        msg = "Cart item quantity updated."
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating cart item for user {current_user_id_int}, product {product_id_in_cart}: {str(e)}")
        return jsonify({"msg": "Failed to update cart item due to a server error"}), 500
        
    updated_cart_items = CartItem.query.filter_by(user_id=current_user_id_int).all()
    return jsonify({
        "msg": msg, 
        "item": cart_item.to_dict() if quantity >= 1 else None, # Send updated item if not deleted
        "cart": [item.to_dict() for item in updated_cart_items]
    }), 200


@cart_bp.route('/cart/item/<int:product_id_in_cart>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(product_id_in_cart):
    """
    Removes a specific product from the current user's cart.
    product_id_in_cart is Product.id.
    """
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user: return jsonify({"msg":"Authenticated user not found"}), 404

    cart_item = CartItem.query.filter_by(user_id=current_user_id_int, product_id=product_id_in_cart).first()
    if not cart_item:
        return jsonify({"msg": "Product not found in cart"}), 404

    try:
        db.session.delete(cart_item)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing from cart for user {current_user_id_int}, product {product_id_in_cart}: {str(e)}")
        return jsonify({"msg": "Failed to remove item from cart due to a server error"}), 500
        
    updated_cart_items = CartItem.query.filter_by(user_id=current_user_id_int).all()
    return jsonify({"msg": "Product removed from cart", "cart": [item.to_dict() for item in updated_cart_items]}), 200


@cart_bp.route('/cart/checkout', methods=['POST'])
@jwt_required()
def checkout():
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user: return jsonify({"msg":"Authenticated user not found"}), 404

    cart_items_to_checkout = CartItem.query.filter_by(user_id=current_user_id_int).all()
    if not cart_items_to_checkout:
        return jsonify({"msg": "Cart is empty. Nothing to checkout."}), 400

    total_amount = 0
    purchase_items_data_for_db = []

    for item in cart_items_to_checkout:
        if not item.product:
            current_app.logger.error(f"Product with ID {item.product_id} in cart for user {current_user_id_int} not found during checkout.")
            return jsonify({"msg": f"Critical error: Product with ID {item.product_id} in cart not found. Checkout aborted."}), 500
        
        item_total = item.product.price * item.quantity
        total_amount += item_total
        purchase_items_data_for_db.append({
            'product_id': item.product.id,
            'quantity': item.quantity,
            'price_at_purchase': item.product.price,
            'product_title': item.product.title,
            'product_image_filename': item.product.image_filenames_list[0] if item.product.image_filenames_list else None
        })

    new_purchase = Purchase(
        user_id=current_user_id_int, 
        total_amount=round(total_amount, 2), 
        purchase_date=datetime.now(timezone.utc)
    )
    db.session.add(new_purchase)
    
    try:
        # Flush to get new_purchase.id before creating PurchaseItems that depend on it
        db.session.flush() 

        for pi_data in purchase_items_data_for_db:
            purchase_item_entry = PurchaseItem(
                purchase_id=new_purchase.id, 
                product_id=pi_data['product_id'],
                quantity=pi_data['quantity'],
                price_at_purchase=pi_data['price_at_purchase'],
                product_title=pi_data['product_title'],
                _product_image_filename=pi_data['product_image_filename'] # Set the raw filename
            )
            db.session.add(purchase_item_entry)

        # Delete cart items after they are processed
        for item in cart_items_to_checkout:
            db.session.delete(item)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during checkout for user {current_user_id_int}: {str(e)}")
        return jsonify({"msg": "Checkout failed due to a server error"}), 500
        
    return jsonify({
        "msg": "Checkout successful!", 
        "purchaseId": new_purchase.id,
        "purchaseDetails": new_purchase.to_dict() # Send back the created purchase with full URLs
    }), 200
