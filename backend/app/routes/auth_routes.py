from flask import Blueprint, request, jsonify, current_app
from app import db, bcrypt
from app.models import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from datetime import timedelta

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Request body is missing or not JSON"}), 400

    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    profile_image_url = data.get('profileImage') # Frontend might send a URL or nothing

    if not email or not username or not password:
        return jsonify({"msg": "Email, username, and password are required"}), 400

    if not isinstance(email, str) or not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"msg": "Invalid data types for email, username, or password"}), 400
    
    if len(password) < 6:
        return jsonify({"msg": "Password must be at least 6 characters long"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409

    # For profile_image, if it's a URL, store it. If it's meant to be an upload, that's handled separately.
    # This route assumes profileImage is a URL or null.
    new_user = User(email=email, username=username, profile_image=profile_image_url)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during registration for email {email}: {str(e)}")
        return jsonify({"msg": "Registration failed due to a server error"}), 500
    
    user_identity = str(new_user.id) # JWT identity must be string
    access_token = create_access_token(identity=user_identity, expires_delta=timedelta(hours=1))
    refresh_token = create_refresh_token(identity=user_identity, expires_delta=timedelta(days=30))
    
    return jsonify(
        access_token=access_token, 
        refresh_token=refresh_token,
        user=new_user.to_dict()
    ), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Request body is missing or not JSON"}), 400
        
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        user_identity = str(user.id) # JWT identity must be string
        access_token = create_access_token(identity=user_identity, expires_delta=timedelta(hours=1))
        refresh_token = create_refresh_token(identity=user_identity, expires_delta=timedelta(days=30))
        return jsonify(
            access_token=access_token,
            refresh_token=refresh_token, 
            user=user.to_dict()
        ), 200
    else:
        return jsonify({"msg": "Invalid email or password"}), 401

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token_endpoint():
    current_user_identity = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_identity, expires_delta=timedelta(hours=1))
    return jsonify(access_token=new_access_token), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required() 
def logout():
    # For JWT, actual logout (token invalidation) requires a blocklist (e.g., Redis).
    # This endpoint can be a placeholder or used to add token to blocklist if implemented.
    return jsonify({"msg": "Logout successful. Please clear your token client-side."}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    current_user_identity_str = get_jwt_identity()
    try:
        user_id = int(current_user_identity_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found for token identity"}), 404
    return jsonify(user.to_dict()), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_identity_str = get_jwt_identity()
    try:
        user_id = int(current_user_identity_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() # Profile updates are expected as JSON for now
    if not data:
        return jsonify({"msg": "Request body is missing or not JSON"}), 400
    
    # Handle username update
    if 'username' in data:
        new_username = data['username']
        if not isinstance(new_username, str) or not new_username.strip():
            return jsonify({"msg": "Username cannot be empty"}), 400
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            return jsonify({"msg": "Username already taken"}), 409
        user.username = new_username.strip()
    
    # Handle profileImage update (assuming it's a URL string from frontend for now)
    # If direct profile image upload is needed, this route would need to handle multipart/form-data
    if 'profileImage' in data:
        if data['profileImage'] is not None and not isinstance(data['profileImage'], str):
             return jsonify({"msg": "Invalid profile image URL format"}), 400
        user.profile_image = data['profileImage'] # Store as is (filename or URL)
            
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile for user ID {user.id}: {str(e)}")
        return jsonify({"msg": "Profile update failed due to a server error"}), 500
        
    return jsonify(user.to_dict()), 200
