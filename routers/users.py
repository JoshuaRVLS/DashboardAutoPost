from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from models.user import User, Code
from bot import user_accounts, save_data, codes 
from passlib.hash import pbkdf2_sha256 as sha256
from datetime import datetime, timedelta

router = APIRouter(prefix='/users')

@router.post('/login')
async def getUser(user: User):
    for user_id, user_data in user_accounts.items():
        if user_data['username'] == user.username and sha256.verify(user.password, user_data['password']):
            user = user_accounts[user_id]
            user['userId'] = user_id
            print(user)
            return JSONResponse(user, status_code=200)
    return JSONResponse({ 'msg': 'Invalid username or password' }, status_code=401)
    

@router.patch('/renew/{id}')
async def renewUser(id: str, code: Code):
    code = code.value.strip()
    if code not in codes or codes[code]["claimed"]:
        return JSONResponse({"msg": "Code expired or claimed."})
    duration = codes[code]["duration"]
    expiry_date_utc = datetime.now() + timedelta(days=duration)
    expiry_date_wib = expiry_date_utc + timedelta(hours=7)
    if id in user_accounts:
                user_info = user_accounts[id]
                user_info["max_bots"] += codes[code]["max_bots"]
                current_expiry_wib = datetime.strptime(user_info["expiry"], "%d-%m-%Y | %H:%M:%S")
                user_info["expiry"] = max(current_expiry_wib, expiry_date_wib).strftime("%d-%m-%Y | %H:%M:%S")     
    codes[code]["claimed"] = True
    save_data()
    return JSONResponse({"msg": "Account renewed."})

@router.get('/{id}')
async def getUserByID(id: str):
     print(user_accounts)
     if not id in user_accounts:
          return JSONResponse({"msg": "User not found."}, 404)
     user = user_accounts[id]
     user['userId'] = id
     return JSONResponse(user, 200)