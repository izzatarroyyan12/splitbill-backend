from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
from models.bill import Bill
from database import get_db

bill_bp = Blueprint('bill', __name__)

@bill_bp.route('', methods=['POST'])
@jwt_required()
def create_bill():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['bill_name', 'total_amount', 'split_method', 'participants']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Add created_by field and timestamps
        data['created_by'] = current_user
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        
        # Create bill document
        bill = Bill(**data)
        
        # Insert into database
        db = get_db()
        result = db.bills.insert_one(bill.dict())
        
        # Get the created bill
        created_bill = db.bills.find_one({'_id': result.inserted_id})
        created_bill['_id'] = str(created_bill['_id'])
        
        return jsonify(created_bill), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bill_bp.route('', methods=['GET'])
@jwt_required()
def get_bills():
    try:
        current_user = get_jwt_identity()
        db = get_db()
        
        # Get all bills where user is a participant or creator
        bills = list(db.bills.find({
            '$or': [
                {'created_by': current_user},
                {'participants.user_id': current_user}
            ]
        }).sort('created_at', -1))  # Sort by creation date, newest first
        
        # Convert ObjectId to string for JSON serialization
        for bill in bills:
            bill['_id'] = str(bill['_id'])
            
        return jsonify(bills), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bill_bp.route('/<bill_id>', methods=['GET'])
@jwt_required()
def get_bill(bill_id):
    try:
        current_user = get_jwt_identity()
        db = get_db()
        
        # Find the bill
        bill = db.bills.find_one({'_id': ObjectId(bill_id)})
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
            
        # Check if user has access to this bill
        if bill['created_by'] != current_user and not any(
            p.get('user_id') == current_user for p in bill['participants']
        ):
            return jsonify({'error': 'Access denied'}), 403
            
        # Convert ObjectId to string
        bill['_id'] = str(bill['_id'])
        
        return jsonify(bill), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bill_bp.route('/<bill_id>/pay', methods=['POST'])
@jwt_required()
def pay_bill(bill_id):
    try:
        current_user = get_jwt_identity()
        db = get_db()
        
        # Find the bill
        bill = db.bills.find_one({'_id': ObjectId(bill_id)})
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
            
        # Find the participant
        participant = None
        for p in bill['participants']:
            if p.get('user_id') == current_user:
                participant = p
                break
                
        if not participant:
            return jsonify({'error': 'User is not a participant in this bill'}), 403
            
        if participant['status'] == 'paid':
            return jsonify({'error': 'Bill already paid'}), 400
            
        # Get user's current balance
        user = db.users.find_one({'_id': ObjectId(current_user)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Check if user has enough balance
        if user['balance'] < participant['amount_due']:
            return jsonify({'error': 'Insufficient balance'}), 400
            
        # Update user's balance
        db.users.update_one(
            {'_id': ObjectId(current_user)},
            {'$inc': {'balance': -participant['amount_due']}}
        )
            
        # Update participant status to paid
        db.bills.update_one(
            {
                '_id': ObjectId(bill_id),
                'participants.user_id': current_user
            },
            {
                '$set': {
                    'participants.$.status': 'paid',
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return jsonify({'message': 'Bill paid successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bill_bp.route('/<bill_id>/participants/<int:participant_index>/pay', methods=['POST'])
@jwt_required()
def mark_participant_as_paid(bill_id, participant_index):
    try:
        current_user = get_jwt_identity()
        db = get_db()
        
        # Find the bill
        bill = db.bills.find_one({'_id': ObjectId(bill_id)})
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
            
        # Check if user is the creator
        if bill['created_by'] != current_user:
            return jsonify({'error': 'Only the bill creator can mark participants as paid'}), 403
            
        # Check if participant index is valid
        if participant_index < 0 or participant_index >= len(bill['participants']):
            return jsonify({'error': 'Invalid participant index'}), 400
            
        # Get the participant
        participant = bill['participants'][participant_index]
        
        # Check if participant is external (no user_id)
        if participant.get('user_id'):
            return jsonify({'error': 'Cannot mark registered users as paid'}), 400
            
        if participant['status'] == 'paid':
            return jsonify({'error': 'Participant already marked as paid'}), 400
            
        # Update participant status to paid
        db.bills.update_one(
            {
                '_id': ObjectId(bill_id),
                'participants': {'$elemMatch': {'external_name': participant['external_name']}}
            },
            {
                '$set': {
                    'participants.$.status': 'paid',
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return jsonify({'message': 'Participant marked as paid successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400 