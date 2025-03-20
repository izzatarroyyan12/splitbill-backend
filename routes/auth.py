from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
import bcrypt
from bson import ObjectId
from database import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not all([username, password, email]):
            return jsonify({'error': 'Missing required fields'}), 400

        db = get_db()
        existing_user = db.users.find_one({'username': username})
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409

        # Hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        # Create new user
        user = {
            'username': username,
            'password': hashed_password,
            'email': email,
            'balance': 0
        }
        
        result = db.users.insert_one(user)
        user['_id'] = str(result.inserted_id)
        del user['password']  # Don't send password back

        return jsonify(user), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return jsonify({'error': 'Missing username or password'}), 400

        db = get_db()
        user = db.users.find_one({'username': username})

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'error': 'Invalid username or password'}), 401

        # Create access token
        access_token = create_access_token(identity=str(user['_id']))
        return jsonify({
            'access_token': access_token,
            'user': {
                '_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'balance': user['balance']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        current_user_id = get_jwt_identity()
        db = get_db()
        
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            '_id': str(user['_id']),
            'username': user['username'],
            'email': user['email'],
            'balance': user['balance']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/balance', methods=['POST'])
@jwt_required()
def add_balance():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        amount = data.get('amount')

        if not amount or not isinstance(amount, (int, float)) or amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        db = get_db()
        result = db.users.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$inc': {'balance': amount}}
        )

        if result.modified_count == 0:
            return jsonify({'error': 'Failed to update balance'}), 400

        updated_user = db.users.find_one({'_id': ObjectId(current_user_id)})
        return jsonify({
            'message': 'Balance updated successfully',
            'new_balance': updated_user['balance']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500 