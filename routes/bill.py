from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.bill import Bill, Item, ItemSplit, Participant
from models.user import User
from bson import ObjectId
from datetime import datetime
from database import get_db
import bcrypt

bill_bp = Blueprint('bill', __name__)

@bill_bp.route('/', methods=['GET', 'POST', 'OPTIONS'])
@jwt_required()
def handle_bills():
    if request.method == 'OPTIONS':
        return '', 200
    elif request.method == 'GET':
        return get_bills()
    elif request.method == 'POST':
        return create_bill()

@bill_bp.route('/<bill_id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def handle_bill(bill_id):
    if request.method == 'OPTIONS':
        return '', 200
    return get_bill(bill_id)

@bill_bp.route('/<bill_id>/pay', methods=['POST', 'OPTIONS'])
@jwt_required()
def handle_bill_payment(bill_id):
    if request.method == 'OPTIONS':
        return '', 200
    return pay_bill(bill_id)

@bill_bp.route('/<bill_id>/participants/<int:participant_index>/pay', methods=['POST', 'OPTIONS'])
@jwt_required()
def handle_participant_payment(bill_id, participant_index):
    if request.method == 'OPTIONS':
        return '', 200
    return mark_participant_as_paid(bill_id, participant_index)

def get_bills():
    try:
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Find bills where user is either creator or participant
        bills = db.bills.find({
            '$or': [
                {'created_by': current_user_id},
                {'participants.user_id': current_user_id}
            ]
        }).sort([('created_at', -1)])  # Use list of tuples for sort
        
        # Convert ObjectId to string for JSON serialization
        bills_list = []
        for bill in bills:
            bill['_id'] = str(bill['_id'])
            bills_list.append(bill)
        
        return jsonify(bills_list), 200
        
    except Exception as e:
        print('Error getting bills:', str(e))
        return jsonify({'error': str(e)}), 500

def create_bill():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        # Validate required fields
        required_fields = ['bill_name', 'split_method', 'participants', 'items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if data['split_method'] not in ['equal', 'per_product']:
            return jsonify({'error': 'Invalid split method. Must be either "equal" or "per_product"'}), 400
        
        # Get creator's username
        creator = User.find_by_id(current_user_id)
        if not creator:
            return jsonify({'error': 'Creator not found'}), 404
        
        # Calculate total from items
        total_amount = sum(
            item.get('price_per_unit', 0) * item.get('quantity', 0)
            for item in data.get('items', [])
        )
        
        # Validate items
        items = []
        for item in data.get('items', []):
            if not all(k in item for k in ['name', 'price_per_unit', 'quantity']):
                return jsonify({'error': 'Each item must have name, price_per_unit, and quantity'}), 400
            
            if item['price_per_unit'] <= 0 or item['quantity'] <= 0:
                return jsonify({'error': 'Price and quantity must be greater than 0'}), 400
            
            item_data = {
                'name': item['name'].strip(),
                'price_per_unit': float(item['price_per_unit']),
                'quantity': int(item['quantity']),
                'split': None
            }
            
            # Handle per-product split
            if data['split_method'] == 'per_product' and 'split' in item:
                total_split_quantity = sum(split.get('quantity', 0) for split in item['split'])
                if total_split_quantity != item['quantity']:
                    return jsonify({
                        'error': f'Split quantities for item "{item["name"]}" must sum up to the total quantity ({item["quantity"]})'
                    }), 400
                
                item_splits = []
                for split in item['split']:
                    if not split.get('external_name') or split.get('quantity', 0) <= 0:
                        return jsonify({'error': 'Invalid split data'}), 400
                    
                    # Try to find user by username
                    user = User.find_by_username(split['external_name'])
                    split_data = {
                        'external_name': split['external_name'],
                        'quantity': int(split['quantity'])
                    }
                    if user:
                        split_data.update({
                            'user_id': str(user['_id']),
                            'username': user['username']
                        })
                    item_splits.append(ItemSplit(**split_data))
                item_data['split'] = item_splits
            
            items.append(Item(**item_data))
        
        # Process participants and calculate amounts
        participants = []
        if data['split_method'] == 'equal':
            amount_per_person = total_amount / len(data['participants'])
            
            for participant in data['participants']:
                if not participant.get('external_name'):
                    return jsonify({'error': 'Each participant must have an external_name'}), 400
                
                # Try to find user by username
                user = User.find_by_username(participant['external_name'])
                
                participant_data = {
                    'external_name': participant['external_name'],
                    'amount_due': round(amount_per_person, 2),
                    'status': 'unpaid'  # Default status
                }
                
                if user:
                    participant_data.update({
                        'user_id': str(user['_id']),
                        'username': user['username']
                    })
                    # If this participant is the bill creator, mark as paid
                    if str(user['_id']) == current_user_id:
                        participant_data['status'] = 'paid'
                
                participants.append(Participant(**participant_data))
        else:  # per_product split
            # Calculate amount per participant based on their item splits
            participant_amounts = {}
            for item in items:
                if not item.split:
                    continue
                price_per_unit = item.price_per_unit
                for split in item.split:
                    external_name = split.external_name
                    if external_name not in participant_amounts:
                        participant_amounts[external_name] = 0
                    participant_amounts[external_name] += price_per_unit * split.quantity
            
            # Create participants list with calculated amounts
            for participant in data['participants']:
                external_name = participant['external_name']
                if external_name not in participant_amounts:
                    return jsonify({'error': f'Participant {external_name} has no items assigned'}), 400
                
                # Try to find user by username
                user = User.find_by_username(external_name)
                
                participant_data = {
                    'external_name': external_name,
                    'amount_due': round(participant_amounts[external_name], 2),
                    'status': 'unpaid'  # Default status
                }
                
                if user:
                    participant_data.update({
                        'user_id': str(user['_id']),
                        'username': user['username']
                    })
                    # If this participant is the bill creator, mark as paid
                    if str(user['_id']) == current_user_id:
                        participant_data['status'] = 'paid'
                
                participants.append(Participant(**participant_data))
        
        # Create and save the bill
        bill = Bill(
            bill_name=data['bill_name'].strip(),
            total_amount=total_amount,
            created_by=current_user_id,
            created_by_username=creator['username'],
            split_method=data['split_method'],
            participants=participants,
            items=items
        )
        
        if not bill.save():
            return jsonify({'error': 'Failed to save bill'}), 500
            
        return jsonify(bill.to_dict()), 201
        
    except Exception as e:
        print('Error creating bill:', str(e))  # Add logging
        return jsonify({'error': str(e)}), 500

@bill_bp.route('/<bill_id>/pay', methods=['POST'])
@jwt_required()
def pay_bill(bill_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        if not ObjectId.is_valid(bill_id):
            return jsonify({'error': 'Invalid bill ID format'}), 400

        db = get_db()
        
        # Start a session for transaction
        with db.client.start_session() as session:
            with session.start_transaction():
                # Find the bill
                bill = db.bills.find_one({'_id': ObjectId(bill_id)})
                if not bill:
                    return jsonify({'error': 'Bill not found'}), 404
                
                # Find the current user's participant entry
                participant = None
                participant_index = None
                for i, p in enumerate(bill['participants']):
                    if p.get('user_id') == current_user_id:
                        participant = p
                        participant_index = i
                        break
                
                if not participant:
                    return jsonify({'error': 'User is not a participant in this bill'}), 403
                
                if participant['status'] == 'paid':
                    return jsonify({'error': 'Already paid'}), 400
                
                # Get user and verify password
                user = db.users.find_one({'_id': ObjectId(current_user_id)})
                if not user or not bcrypt.checkpw(data.get('password', '').encode('utf-8'), user['password']):
                    return jsonify({'error': 'Invalid password'}), 401
                
                amount_due = float(participant['amount_due'])
                current_balance = float(user['balance'])
                
                # Verify amount matches what user owes
                if current_balance < amount_due:
                    return jsonify({
                        'error': 'Insufficient balance',
                        'amount_due': amount_due,
                        'current_balance': current_balance
                    }), 400
                
                # Update user's balance
                result = db.users.update_one(
                    {'_id': ObjectId(current_user_id)},
                    {'$inc': {'balance': -amount_due}},
                    session=session
                )
                
                if result.modified_count == 0:
                    raise Exception('Failed to update user balance')
                
                # Mark participant as paid
                result = db.bills.update_one(
                    {'_id': ObjectId(bill_id)},
                    {
                        '$set': {
                            f'participants.{participant_index}.status': 'paid',
                            'updated_at': datetime.utcnow()
                        }
                    },
                    session=session
                )
                
                if result.modified_count == 0:
                    raise Exception('Failed to update bill status')
                
                # Get updated user data
                updated_user = db.users.find_one(
                    {'_id': ObjectId(current_user_id)},
                    session=session
                )
                
                return jsonify({
                    'message': 'Payment successful',
                    'new_balance': updated_user['balance'],
                    'amount_paid': amount_due
                }), 200
        
    except Exception as e:
        print('Error processing payment:', str(e))  # Add logging
        return jsonify({'error': str(e)}), 500

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

@bill_bp.route('/<bill_id>/participants/<int:participant_index>/pay', methods=['POST'])
@jwt_required()
def mark_participant_as_paid(bill_id, participant_index):
    try:
        if not ObjectId.is_valid(bill_id):
            return jsonify({'error': 'Invalid bill ID format'}), 400

        current_user = get_jwt_identity()
        db = get_db()
        
        # Start a session for transaction
        with db.client.start_session() as session:
            with session.start_transaction():
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
                    return jsonify({'error': 'Cannot mark registered users as paid. They must pay through their own account.'}), 400
                
                if participant['status'] == 'paid':
                    return jsonify({'error': 'Participant already marked as paid'}), 400
                
                # Update participant status to paid
                result = db.bills.update_one(
                    {'_id': ObjectId(bill_id)},
                    {
                        '$set': {
                            f'participants.{participant_index}.status': 'paid',
                            'updated_at': datetime.utcnow()
                        }
                    },
                    session=session
                )
                
                if result.modified_count == 0:
                    raise Exception('Failed to update participant status')
                
                # Get updated bill
                updated_bill = db.bills.find_one(
                    {'_id': ObjectId(bill_id)},
                    session=session
                )
                
                return jsonify({
                    'message': 'Participant marked as paid successfully',
                    'participant_name': participant['external_name'],
                    'amount_paid': participant['amount_due']
                }), 200
                
    except Exception as e:
        print('Error marking participant as paid:', str(e))  # Add logging
        return jsonify({'error': str(e)}), 500 