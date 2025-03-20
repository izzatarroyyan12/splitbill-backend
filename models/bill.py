from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ItemSplit(BaseModel):
    user_id: Optional[str] = None
    external_name: Optional[str] = None
    quantity: int

class Item(BaseModel):
    name: str
    price_per_unit: float
    quantity: int
    split: Optional[List[ItemSplit]] = None

class Participant(BaseModel):
    user_id: Optional[str] = None
    external_name: Optional[str] = None
    amount_due: float
    status: str = "unpaid"  # "unpaid" or "paid"

class Bill(BaseModel):
    bill_name: str
    total_amount: float
    created_by: str
    split_method: str  # "equal" or "per_product"
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
                "split_method": "equal",
                "participants": [
                    {"user_id": "user_1", "amount_due": 50000, "status": "unpaid"},
                    {"user_id": "user_2", "amount_due": 50000, "status": "unpaid"},
                    {"external_name": "Charlie", "amount_due": 50000, "status": "unpaid"}
                ],
                "items": [
                    {
                        "name": "Bacon",
                        "price_per_unit": 10000,
                        "quantity": 10
                    },
                    {
                        "name": "Beef",
                        "price_per_unit": 20000,
                        "quantity": 3
                    },
                    {
                        "name": "Rice",
                        "price_per_unit": 5000,
                        "quantity": 5
                    }
                ]
            }
        } 