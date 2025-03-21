from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_db
from bson import ObjectId

class User(BaseModel):
    username: str
    email: EmailStr
    balance: float = 0.0
    hashed_password: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "balance": 100000.0
            }
        }
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[dict]:
        try:
            db = get_db()
            user = db.users.find_one({'_id': ObjectId(user_id)})
            return user
        except Exception as e:
            print(f"Error finding user by ID: {str(e)}")
            return None
    
    @staticmethod
    def find_by_username(username: str) -> Optional[dict]:
        try:
            db = get_db()
            user = db.users.find_one({'username': username})
            return user
        except Exception as e:
            print(f"Error finding user by username: {str(e)}")
            return None 