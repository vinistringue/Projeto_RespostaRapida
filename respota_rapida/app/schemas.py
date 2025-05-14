from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MatchPlayerCreate(BaseModel):
    name: str

    class Config:
        orm_mode = True

class MatchPlayerOut(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        orm_mode = True

class MatchOut(BaseModel):
    id: int
    player1_id: int
    player2_id: int
    start_time: datetime

    class Config:
        orm_mode = True
