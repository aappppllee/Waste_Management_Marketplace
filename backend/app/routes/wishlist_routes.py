from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import User, Product # wishlist_items table is used via User.wishlist relationship
from flask_jwt_extended import jwt_required, get_jwt_identity

wishlist_bp = Blueprint('wishlist_bp', __name__)

@wishlist_bp.route('/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    """Gets the current user's wishlist."""
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    user = User.query.get(current_user_id_int)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    # user.wishlist directly gives a list of Product objects due to the model relationship
    wishlist_products_data = [product.to_dict() for product in user.wishlist]
    return jsonify(wishlist_products_data), 200

@wishlist_bp.route('/wishlist/<int:product_id>', methods=['POST'])
@jwt_required()
def add_to_wishlist(product_id):
    """Adds a product to the current user's wishlist."""
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    user = User.query.get(current_user_id_int)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404

    if product in user.wishlist:
        return jsonify({"msg": "Product already in wishlist"}), 409 # Conflict

    if product.seller_id == current_user_id_int:
        return jsonify({"msg": "You cannot add your own product to your wishlist"}), 403

    user.wishlist.append(product)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding to wishlist for user {current_user_id_int}, product {product_id}: {str(e)}")
        return jsonify({"msg": "Could not add product to wishlist due to a server error"}), 500
        
    return jsonify({"msg": "Product added to wishlist", "productId": product.id}), 201

@wishlist_bp.route('/wishlist/<int:product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(product_id):
    """Removes a product from the current user's wishlist."""
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    product = Product.query.get(product_id)
    if not product:
        # If product doesn't exist, it can't be in the wishlist.
        # Depending on desired behavior, could be 404 or just a success if item isn't there.
        return jsonify({"msg": "Product not found, so it cannot be in wishlist"}), 404

    if product not in user.wishlist:
        return jsonify({"msg": "Product not in wishlist"}), 404 # Item not found in this specific list

    try:
        user.wishlist.remove(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing from wishlist for user {current_user_id_int}, product {product_id}: {str(e)}")
        return jsonify({"msg": "Could not remove product from wishlist due to a server error"}), 500
        
    return jsonify({"msg": "Product removed from wishlist", "productId": product.id}), 200
