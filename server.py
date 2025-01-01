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
    
@bot.hybrid_command(name='tes', description='Check bot latency, API ping, and uptime')
async def tes(ctx):
    # Start measuring API ping
    start_time = time.time()
    message = await ctx.send("Pinging...")
    end_time = time.time()
    
    # Calculate different ping types
    api_ping = round((end_time - start_time) * 1000)  # API ping
    websocket_ping = round(bot.latency * 1000)  # Websocket latency
    
    # Calculate uptime
    current_time = datetime.utcnow()
    uptime_delta = current_time - bot_start_time
    
    days = uptime_delta.days
    hours = uptime_delta.seconds // 3600
    minutes = (uptime_delta.seconds % 3600) // 60
    seconds = uptime_delta.seconds % 60
    
    # Create embed
    embed = discord.Embed(
        title="",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    # Add ping information
    embed.add_field(
        name="<:bott:1308056946263461989> Bot Latency",
        value=f"```{websocket_ping}ms```",
        inline=True
    )
    
    embed.add_field(
        name="<:Stats:1313673370797346869> API Latency",
        value=f"```{api_ping}ms```",
        inline=True
    )
    
    # Add uptime field
    embed.add_field(
        name="<:clock:1308057442730508348> Uptime",
        value=f"```{days}Days : {hours}Hours : {minutes}Minutes : {seconds}Seconds```",
        inline=False
    )
    
    # Add color indicators based on ping
    if websocket_ping < 100:
        embed.color = discord.Color.green()
        status = "Excellent"
    elif websocket_ping < 200:
        embed.color = discord.Color.green()
        status = "Good"
    elif websocket_ping < 300:
        embed.color = discord.Color.orange()
        status = "Moderate"
    else:
        embed.color = discord.Color.red()
        status = "Poor"
    
    # Add connection status
    embed.add_field(
        name="<:verified:1308057482085666837> Connection Status",
        value=f"```{status}```",
        inline=False
    )
    
    # Add footer with current time
    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    )
    
    # Update the message with the embed
    await message.edit(content=None, embed=embed)
