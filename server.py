from fastapi import FastAPI
from routers import users
import uvicorn
import asyncio
from bot import run_bot
from bot import bot
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware




@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_bot())
    yield 
    await bot.close()

app = FastAPI(lifespan=lifespan)
app.include_router(users.router, prefix='/api/v1')

origins = [
    'http://localhost',
    'http://localhost:3000'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    
def start():
    uvicorn.run(app, host="0.0.0.0", port=8080)
    

if __name__ == "__main__":
    start()
    
    