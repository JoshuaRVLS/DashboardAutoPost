from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from models.user import User, Code, Account
from bot import user_accounts, load_data, save_data, codes, load_users, load_codes, force_activity_update
from passlib.hash import pbkdf2_sha256 as sha256
from datetime import datetime, timedelta
import aiohttp
import discord

router = APIRouter(prefix='/users')

@router.post('/login')
async def getUser(user: User):
    user_accounts = load_users()
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
    codes = load_codes()
    user_accounts = load_users()
    print(code)
    print(codes)
    if code not in codes or codes[code]["claimed"]:
        return JSONResponse({"msg": "Code expired or claimed."}, 400)
    duration = codes[code]["duration"]
    expiry_date_utc = datetime.now() + timedelta(days=duration)
    expiry_date_wib = expiry_date_utc + timedelta(hours=7)
    if id in user_accounts:
                user_info = user_accounts[id]
                user_info['expired'] = False
                user_info["max_bots"] = codes[code]["max_bots"]
                current_expiry_wib = datetime.fromtimestamp(user_info["expiry"])
                user_info["expiry"] = max(current_expiry_wib, expiry_date_wib).timestamp()     
    codes[code]["claimed"] = True
    save_data()
    return JSONResponse({"msg": "Account renewed."}, 201)

@router.get('/{id}')
async def getUserByID(id: str):
     user_accounts = load_users()
     if not id in user_accounts:
          return JSONResponse({"msg": "User not found."}, 404)
     user = user_accounts[id]
     user['userId'] = id
     return JSONResponse(user, 200)

@router.post('/accounts')
async def createAccount(account: Account):
    user_accounts = load_users()
    user_id = str(account.id)
    
    # Initial checks
    if user_id not in user_accounts:
        return JSONResponse({"msg": "You must claim a code to register first."}, 400)
    

    user_info: dict = user_accounts[user_id]
    if len(user_info.get("accounts", {})) >= user_info["max_bots"]:
        return JSONResponse({"msg": "You have reached your maximum bot limit."}, 400)
    
    try:
        headers = {'Authorization': account.token, 'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    # Check for duplicate account names
                    for user in user_info.get('accounts').values():
                        if account.token == user.get('token'):
                            return JSONResponse({"msg": "Account is registered."}, 400)
                       

                    # Initialize account structure
                    user_info["accounts"][user_data['username']] = {
                        'token': account.token,
                        'status': 'offline',
                        'online_time': 0,
                        'messages_sent': 0,
                        'autoposting': False,
                        'server_id': None,
                        'channels': {},
                        'webhook': None,
                        'dm_monitoring': False,
                        'dm_webhook': None,
                        'bot_info': {
                            'username': user_data['username'],
                            'discriminator': user_data['discriminator'],
                            'id': user_data['id'],
                            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    }

                    save_data()
                    await force_activity_update()

                    return JSONResponse({"msg": f"Account added successfuly"}, 201)
                else:
                    return JSONResponse({"msg": "The provided token is invalid."}, 400)
    except Exception as e:
        print(e)
                

