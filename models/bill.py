from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from database import get_db
from bson import ObjectId

class ItemSplit(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    external_name: str
    quantity: int = Field(ge=0)

class Item(BaseModel):
    name: str
    price_per_unit: float = Field(ge=0)
    quantity: int = Field(ge=1)
    split: Optional[List[ItemSplit]] = None

class Participant(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    external_name: str
    amount_due: float = Field(ge=0)
    status: Literal["unpaid", "paid"] = "unpaid"

class Bill(BaseModel):
    bill_name: str
    total_amount: float = Field(ge=0)
    created_by: str
    created_by_username: str
    split_method: Literal["equal", "per_product"]
    participants: List[Participant]
    items: List[Item]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "bill_name": "Dinner at XYZ",
                "total_amount": 150000,
                "created_by": "user_1",
                "created_by_username": "john_doe",
                "split_method": "equal",
                "participants": [
                    {"user_id": "user_1", "username": "john_doe", "external_name": "John Doe", "amount_due": 50000, "status": "unpaid"},
                    {"user_id": "user_2", "username": "jane_doe", "external_name": "Jane Doe", "amount_due": 50000, "status": "unpaid"},
                    {"external_name": "Charlie", "amount_due": 50000, "status": "unpaid"}
                ],
                "items": [
                    {
                        "name": "Bacon",
                        "price_per_unit": 10000,
                        "quantity": 10,
                        "split": [
                            {"external_name": "John Doe", "quantity": 4},
                            {"external_name": "Jane Doe", "quantity": 3},
                            {"external_name": "Charlie", "quantity": 3}
                        ]
                    }
                ]
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": str(self._id) if hasattr(self, '_id') else None,
            "bill_name": self.bill_name,
            "total_amount": self.total_amount,
            "created_by": self.created_by,
            "created_by_username": self.created_by_username,
            "split_method": self.split_method,
            "participants": [p.dict() for p in self.participants],
            "items": [i.dict() for i in self.items],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def save(self) -> bool:
        try:
            db = get_db()
            data = self.dict(exclude={'_id'})
            if hasattr(self, '_id'):
                result = db.bills.update_one(
                    {'_id': self._id},
                    {'$set': data}
                )
                return result.modified_count > 0
            else:
                result = db.bills.insert_one(data)
                self._id = result.inserted_id
                return True
        except Exception as e:
            print(f"Error saving bill: {str(e)}")
            return False

    @staticmethod
    def find(query: Dict[str, Any]) -> List['Bill']:
        try:
            db = get_db()
            bills = []
            for bill_data in db.bills.find(query).sort('created_at', -1):
                bill_data['_id'] = str(bill_data['_id'])
                bills.append(bill_data)
            return bills
        except Exception as e:
            print(f"Error finding bills: {str(e)}")
            return []

    @staticmethod
    def find_by_id(bill_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = get_db()
            bill = db.bills.find_one({'_id': ObjectId(bill_id)})
            if bill:
                bill['_id'] = str(bill['_id'])
            return bill
        except Exception as e:
            print(f"Error finding bill by ID: {str(e)}")
            return None 