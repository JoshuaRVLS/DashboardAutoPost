from pydantic import BaseModel 

class User(BaseModel):
    username: str 
    password: str

class Code(BaseModel):
    value: str

class Account(BaseModel):
    id: str
    token: str