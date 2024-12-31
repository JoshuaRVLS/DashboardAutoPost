from bot import user_accounts
from passlib.hash import pbkdf2_sha256 as sha256
from fastapi.responses import JSONResponse
from models.user import User

def getUser(user: User):
    for user_id, user_data in user_accounts.items():
        if user_data['username'] == user.username and sha256.verify(user.password, user_data['password']):
            user = user_accounts[user_id]
            user['userId'] = user_id
            print(user)
            return JSONResponse(user, status_code=200)
    return JSONResponse({ 'msg': 'Invalid username or password' }, status_code=401)