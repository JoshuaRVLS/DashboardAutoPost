from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from models.user import User 
from passlib.hash import pbkdf2_sha256 as sha256
from controllers import users

router = APIRouter(prefix='/users')

@router.post('/login')
async def getUser(user: User):
    users.getUser(user)
    

@router.post('test')
async def test():
    pass