from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import os
from routes.auth import auth_bp
from routes.bill import bill_bp
from database import client, get_db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[os.getenv('RATE_LIMIT', '100 per minute')]
    )
    
    # Configure CORS
    CORS(app, 
        resources={r"/api/*": {
            "origins": [
                "http://localhost:3000",
                "https://splitbill-frontend-2v7w.vercel.app"
            ],  # Explicitly allow only these origins
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,  # Required for cookies, sessions, or authentication
            "max_age": 3600,
            "automatic_options": True,
            "vary_header": True
        }})


    # Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))  # 24 hours
    app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/livin')
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    
    # Initialize JWT
    jwt = JWTManager(app)

    # Register blueprints with proper URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(bill_bp, url_prefix='/api/bills')

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response

    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        try:
            # Check database connection
            db = get_db()
            db.command('ping')
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'environment': os.getenv('ENVIRONMENT', 'development')
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e)
            }), 500

    # Global error handler for CORS preflight
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            return response

    # Generic error handler
    @app.errorhandler(Exception)
    def handle_error(error):
        code = getattr(error, 'code', 500)
        message = getattr(error, 'description', str(error))
        if os.getenv('ENVIRONMENT') == 'production':
            # In production, don't expose internal error details
            message = 'An internal error occurred' if code == 500 else message
        return jsonify({
            'error': message,
            'status_code': code
        }), code

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 