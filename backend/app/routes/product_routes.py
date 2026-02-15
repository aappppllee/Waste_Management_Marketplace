from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Product, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid # For generating unique filenames
from werkzeug.utils import secure_filename # For sanitizing filenames
import json # For parsing existingImages from form data

product_bp = Blueprint('product_bp', __name__)

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_files_from_request(files_list_from_request):
    """
    Saves uploaded files from a FileStorage list and returns a list of their new unique filenames.
    """
    saved_filenames = []
    upload_folder = current_app.config.get('UPLOAD_FOLDER')

    if not upload_folder or not os.path.exists(upload_folder):
        current_app.logger.error(f"Upload folder '{upload_folder}' is not configured or does not exist.")
        # Depending on requirements, you might raise an error or return empty
        return [] 

    for file_storage in files_list_from_request:
        if file_storage and file_storage.filename and allowed_file(file_storage.filename):
            original_filename = secure_filename(file_storage.filename)
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            if not ext: # Should not happen if allowed_file passed, but good check
                current_app.logger.warning(f"File with no extension skipped: {original_filename}")
                continue
            
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(upload_folder, unique_filename)
            try:
                file_storage.save(file_path)
                saved_filenames.append(unique_filename)
                current_app.logger.info(f"Saved file: {unique_filename} at {file_path}")
            except Exception as e:
                current_app.logger.error(f"Error saving file {original_filename} to {file_path}: {str(e)}")
        elif file_storage and file_storage.filename: # File was provided but not allowed
            current_app.logger.warning(f"File type not allowed or no filename: {file_storage.filename}")
        elif file_storage and not file_storage.filename:
             current_app.logger.warning(f"Received a file storage object without a filename.")


    return saved_filenames


@product_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    user = User.query.get(current_user_id_int)
    if not user:
        return jsonify({"msg": "Authenticated user not found"}), 404 

    if 'multipart/form-data' not in request.content_type:
        return jsonify({"msg": "Content-Type must be multipart/form-data"}), 415

    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')
    price_str = request.form.get('price')
    uploaded_files = request.files.getlist('images') # Key used by frontend FormData

    required_fields = {'title': title, 'description': description, 'category': category, 'price': price_str}
    missing_fields = [key for key, value in required_fields.items() if value is None or str(value).strip() == ""]
    if missing_fields:
        return jsonify({"msg": f"Missing required product fields: {', '.join(missing_fields)}"}), 400

    try:
        price = float(price_str)
        if price <= 0:
            return jsonify({"msg": "Price must be a positive number"}), 400
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid price format. Price must be a number."}), 400

    new_product = Product(
        title=title.strip(),
        description=description.strip(),
        category=category.strip(),
        price=price,
        seller_id=current_user_id_int
    )

    saved_filenames = []
    if uploaded_files:
        saved_filenames = save_files_from_request(uploaded_files)
    
    new_product.image_filenames_list = saved_filenames # Use the setter for filenames

    try:
        db.session.add(new_product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating product for user {current_user_id_int}: {str(e)}")
        return jsonify({"msg": "Failed to create product due to a server error"}), 500
        
    return jsonify(new_product.to_dict()), 201 # Return product with full image URLs

@product_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401

    product = Product.query.get_or_404(product_id, description="Product not found")

    if product.seller_id != current_user_id_int:
        return jsonify({"msg": "Not authorized to update this product"}), 403

    if 'multipart/form-data' not in request.content_type:
         return jsonify({"msg": "Content-Type must be multipart/form-data for product updates"}), 415

    if 'title' in request.form: product.title = request.form.get('title', product.title).strip()
    if 'description' in request.form: product.description = request.form.get('description', product.description).strip()
    if 'category' in request.form: product.category = request.form.get('category', product.category).strip()
    
    if 'price' in request.form:
        try:
            price = float(request.form.get('price'))
            if price <= 0: return jsonify({"msg": "Price must be a positive number"}), 400
            product.price = price
        except (ValueError, TypeError): return jsonify({"msg": "Invalid price format"}), 400

    # Image handling:
    # `existingImages`: JSON string array of full URLs of images to keep. We need to extract filenames.
    # `images`: New files to upload.
    
    final_filenames_to_keep = []
    existing_images_json_str = request.form.get('existingImages')
    if existing_images_json_str:
        try:
            existing_image_urls_to_keep = json.loads(existing_images_json_str)
            if isinstance(existing_image_urls_to_keep, list):
                for url_or_filename in existing_image_urls_to_keep:
                    if isinstance(url_or_filename, str):
                        # If it's a full URL from our server, extract filename
                        if current_app.config.get('FLASK_STATIC_UPLOADS_URL') in url_or_filename:
                            final_filenames_to_keep.append(os.path.basename(url_or_filename))
                        # If it's just a filename already (e.g., from an earlier placeholder or if frontend sends it)
                        elif not url_or_filename.startswith(('http://', 'https://')):
                             final_filenames_to_keep.append(secure_filename(url_or_filename))
                        # else: it's an external URL, we might choose to keep it as is if our model supported mixed types
                        # For now, we assume existingImages are filenames or derive them.
        except json.JSONDecodeError:
            current_app.logger.warning(f"Could not parse existingImages JSON: {existing_images_json_str}")
        except Exception as e:
            current_app.logger.error(f"Error processing existingImages for product {product_id}: {str(e)}")


    newly_uploaded_files = request.files.getlist('images')
    newly_saved_filenames = []
    if newly_uploaded_files:
        newly_saved_filenames = save_files_from_request(newly_uploaded_files)

    # Determine which old files to delete from storage
    current_db_filenames = product.image_filenames_list
    all_final_filenames = final_filenames_to_keep + newly_saved_filenames
    
    files_to_delete_from_storage = [fn for fn in current_db_filenames if fn not in all_final_filenames]
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    for filename_to_delete in files_to_delete_from_storage:
        if filename_to_delete: # Ensure not empty
            try:
                file_path = os.path.join(upload_folder, filename_to_delete)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.info(f"Deleted old image file during update: {filename_to_delete}")
            except Exception as e:
                current_app.logger.error(f"Error deleting old image file {filename_to_delete}: {str(e)}")

    product.image_filenames_list = all_final_filenames # Update product with the new list of filenames
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating product {product_id}: {str(e)}")
        return jsonify({"msg": "Failed to update product due to a server error"}), 500
        
    return jsonify(product.to_dict()), 200

# --- Other product routes (GET all, GET one, DELETE, GET my-listings) ---
# These should largely remain the same as the last correct version,
# ensuring they use int(current_user_id_str) for DB queries where needed.

@product_bp.route('/products', methods=['GET'])
def get_products():
    category_filter = request.args.get('category')
    search_query = request.args.get('q') 
    query = Product.query
    if category_filter and category_filter.lower() != 'all':
        query = query.filter(Product.category.ilike(category_filter))
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(db.or_(Product.title.ilike(search_term), Product.description.ilike(search_term)))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 8, type=int)
    paginated_products = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    products_list = [product.to_dict() for product in paginated_products.items]
    return jsonify({
        "products": products_list, "total_products": paginated_products.total,
        "current_page": paginated_products.page, "total_pages": paginated_products.pages,
        "has_next": paginated_products.has_next, "has_prev": paginated_products.has_prev
    }), 200

@product_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product_detail_route(product_id): # Renamed to avoid conflict
    product = Product.query.get_or_404(product_id, description="Product not found")
    return jsonify(product.to_dict()), 200

@product_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    current_user_id_str = get_jwt_identity() 
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    product = Product.query.get_or_404(product_id, description="Product not found")

    if product.seller_id != current_user_id_int:
        current_app.logger.warning(f"Auth fail: Product seller ID {product.seller_id} != Current user ID {current_user_id_int}")
        return jsonify({"msg": "Not authorized to delete this product"}), 403

    try:
        # Before deleting product, remove its images from filesystem
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        filenames_to_delete = product.image_filenames_list # Get filenames
        
        for filename in filenames_to_delete:
            if filename and not filename.startswith(('http://', 'https://')): # Only delete local files
                try:
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        current_app.logger.info(f"Deleted image file: {filename}")
                except Exception as e:
                    current_app.logger.error(f"Error deleting image file {filename}: {str(e)}")
        
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product {product_id} by user {current_user_id_int}: {str(e)}")
        return jsonify({"msg": "Failed to delete product due to a server error"}), 500
        
    return jsonify({"msg": "Product deleted successfully"}), 200

@product_bp.route('/my-listings', methods=['GET'])
@jwt_required()
def get_my_listings():
    current_user_id_str = get_jwt_identity()
    try:
        current_user_id_int = int(current_user_id_str)
    except ValueError:
        return jsonify({"msg": "Invalid user identity in token"}), 401
        
    user_products = Product.query.filter_by(seller_id=current_user_id_int).order_by(Product.created_at.desc()).all()
    return jsonify({"products": [product.to_dict() for product in user_products]}), 200
