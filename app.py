from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import timedelta
from pymongo import MongoClient
from bson import ObjectId
from routes.auth import auth_bp
from routes.bill import bill_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/livin')
jwt = JWTManager(app)

# MongoDB Configuration
client = MongoClient(app.config['MONGODB_URI'])
db = client[os.getenv('MONGODB_DB', 'splitbill')]

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(bill_bp, url_prefix='/api/bills')

# Helper function to convert ObjectId to string
def serialize_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@app.route('/')
def home():
    return {'message': 'Welcome to Livin API'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000))) 