from flask import Blueprint, jsonify, current_app
from app import db
from app.models import Purchase, User
from flask_jwt_extended import jwt_required, get_jwt_identity

purchase_bp = Blueprint('purchase_bp', __name__)

@purchase_bp.route('/purchases', methods=['GET'])
@jwt_required()
def get_purchase_history():
    """
    Gets the purchase history for the currently authenticated user.
    Requires authentication.
    Orders purchases by date, most recent first.
    """
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(current_user_id_int)
    if not user: 
        return jsonify({"msg":"Authenticated user not found"}), 404
    
    try:
        purchases_query = Purchase.query.filter_by(user_id=current_user_id_int).order_by(Purchase.purchase_date.desc()).all()
        purchase_history_list = [purchase.to_dict() for purchase in purchases_query]
        return jsonify(purchase_history_list), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching purchase history for user {current_user_id_int}: {str(e)}")
        return jsonify({"msg": "Failed to retrieve purchase history due to a server error"}), 500

