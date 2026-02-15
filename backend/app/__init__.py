import os
from flask import Flask, send_from_directory, current_app as app_context # Renamed current_app import
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config # Import the Config class

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(config_class=Config):
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True is good
    app.config.from_object(config_class)

    # Ensure the instance folder exists (for SQLite DB, uploads, etc.)
    # app.instance_path is already an absolute path to the instance folder
    try:
        os.makedirs(app.instance_path, exist_ok=True) 
    except OSError as e:
        app.logger.error(f"Error creating instance folder '{app.instance_path}': {e}")

    # Ensure the upload folder exists using the absolute path from config
    upload_folder_abs = app.config.get('UPLOAD_FOLDER')
    if upload_folder_abs:
        try:
            os.makedirs(upload_folder_abs, exist_ok=True)
            app.logger.info(f"Upload folder is set to: {upload_folder_abs}")
        except OSError as e:
            app.logger.error(f"Error creating upload folder '{upload_folder_abs}': {e}")
    else:
        app.logger.warning("UPLOAD_FOLDER is not configured in app config.")


    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Configure CORS
    cors_origins_config = app.config.get('CORS_ORIGINS', '*')
    origins_list = []
    if isinstance(cors_origins_config, str):
        if cors_origins_config == '*':
            origins_list = "*" # Special value for allow all
        else:
            origins_list = [origin.strip() for origin in cors_origins_config.split(',')]
    elif isinstance(cors_origins_config, list): # If it's already a list
        origins_list = cors_origins_config
    
    CORS(app, 
         resources={r"/api/*": {"origins": origins_list}}, 
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True)
    )
    app.logger.info(f"CORS configured for API origins: {origins_list}")


    # Import and register blueprints for different parts of the API
    from app.routes.auth_routes import auth_bp
    from app.routes.product_routes import product_bp
    from app.routes.cart_routes import cart_bp
    from app.routes.purchase_routes import purchase_bp
    from app.routes.wishlist_routes import wishlist_bp 

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(product_bp, url_prefix='/api')
    app.register_blueprint(cart_bp, url_prefix='/api')
    app.register_blueprint(purchase_bp, url_prefix='/api')
    app.register_blueprint(wishlist_bp, url_prefix='/api')

    # Route to serve uploaded files
    # The URL path comes from config: FLASK_STATIC_UPLOADS_URL
    uploads_url_path_segment = app.config.get('FLASK_STATIC_UPLOADS_URL', '/uploads').strip('/')
    
    # This route must be defined within the create_app context
    @app.route(f'/{uploads_url_path_segment}/<path:filename>')
    def uploaded_file_route(filename): # Renamed to avoid conflict
        # Use app_context.config here as 'app' might not be the final app object in some contexts
        upload_dir = app_context.config.get('UPLOAD_FOLDER')
        
        if not upload_dir:
            app_context.logger.error("UPLOAD_FOLDER is not configured for serving files.")
            return "File serving misconfigured", 500
        
        # Ensure upload_dir is absolute for security and correctness with send_from_directory
        if not os.path.isabs(upload_dir):
             # This case should ideally be handled by Config making UPLOAD_FOLDER absolute
            app_context.logger.warning(f"UPLOAD_FOLDER '{upload_dir}' was not absolute. Resolving relative to app.root_path.")
            upload_dir = os.path.join(app_context.root_path, upload_dir)
            
        app_context.logger.debug(f"Attempting to serve file: {filename} from directory: {upload_dir}")
        return send_from_directory(upload_dir, filename)

    @app.route('/')
    def index():
        return f"Welcome to EcoFinds API! Uploaded files are served from /{uploads_url_path_segment}/<filename>"

    return app
