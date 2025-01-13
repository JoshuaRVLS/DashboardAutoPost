import itertools
import json
import os
import aiohttp
from discord import SyncWebhook
import discord
from discord.ext import commands, tasks
import asyncio
import time
import discum
import threading
import logging
from datetime import datetime, timedelta
import requests
import sys
import traceback
import dotenv
from passlib.hash import pbkdf2_sha256

## ----------------------------------------------------------------------------------------------------------------

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


TOKEN =os.environ.get('TOKEN')
EXPIRED_WEBHOOK = ""
CLAIMWEBHOOK = ""
GLOBAL_WEBHOOK_URL = "https://discord.com/api/webhooks/1308832947738251365/IIoiJlMA0rhiqo-hVxjP2sUg1SxpgZ36WInukssYJcznsaEWy2oo3lhTTB7P-UEUzSTj"  # Add your DM webhook URL here
WARNINGWEBHOOK ="https://discord.com/api/webhooks/1314218508975869953/lKpyfKsaSiNg0zc2lQw3rE_3hfjr2q74DuUifMDs9I1n95jOIxoSWw-71VHJp7mpQej3"
BANLOGS_WEBHOOK ="https://discord.com/api/webhooks/1316439268108926976/uuKgufi6M4_Uzvl5HtkkBH-l5tQxvy1mAAbJmk437oSqpKamexGvTnwFDBaT9ibV4HEJ"
ERROR_WEBHOOK = "https://discord.com/api/webhooks/1317471513795887104/PhNUjRX7jRk8YE1jrMMUd06jqP9-3UqkT0cINI4hFXCiEYZAKMotun2Tl6RNPbVbwjud"  
DMLOGS = "https://discord.com/api/webhooks/1317478112069681172/ZBneZoA2_oyQB3vDR3o8Y4mwI8qojhufLTfuLhwoQ5PZDGTQxmcZOf3FQeBx8ykIwEGJ"
USERID = ["1155459634035957820", "1051163941520298044"]  # Add the user IDs you want to allow
GLOBALDM = "https://discord.com/api/webhooks/1317478112069681172/ZBneZoA2_oyQB3vDR3o8Y4mwI8qojhufLTfuLhwoQ5PZDGTQxmcZOf3FQeBx8ykIwEGJ"
TOKEN_LOGS="https://discord.com/api/webhooks/1320780391409520672/XoTH-YgjFL91sw5w8dVeA8nP2WAa6RsBpTm1qE7t9nhcqwlb-A1uQsITE1HJ2HJDOB55"



## ----------------------------------------------------------------------------------------------------------------
# Disable all logging from discum
logging.getLogger("discum").disabled = True

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
user_accounts = {}

# Load existing user accounts from a JSON file
def load_accounts():
    global user_accounts
    try:
        with open('database.json', 'r') as f:
            user_accounts = json.load(f)
    except FileNotFoundError:
        user_accounts = {}

# Save user accounts to a JSON file
def save_accounts():
    global user_accounts
    with open('database.json', 'w') as f:
        json.dump(user_accounts, f)

# Autopost monitoring task
@tasks.loop(seconds=5)
async def update_autopost_status():
    for user_id, user_data in user_accounts.items():
        accounts = user_data.get("accounts", {})
        for acc_name, account_info in accounts.items():
            if account_info:  # Check if account_info is not None
                if account_info.get("autoposting", False):
                    # Perform autoposting update
                    pass

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_data()
    update_autopost_status.start()
    expire_accounts_task.start()
    cleanup_old_logs.start()
    await force_activity_update()
    global bot_start_time
    bot_start_time = datetime.utcnow()
    await bot.tree.sync()
    load_welcome_configs()
    bot.loop.create_task(update_activity())

# Add this near your other global variables
activities = itertools.cycle([
    lambda total: discord.Activity(type=discord.ActivityType.watching, name=f"{total} Users"),
    lambda total: discord.Activity(type=discord.ActivityType.custom, name=f"{total} Server"),
    lambda total: discord.Activity(type=discord.ActivityType.custom, name=f"{total} Channel"),  # Pass total parameter
    lambda _: discord.Activity(type=discord.ActivityType.listening, name="/helps")
])
current_activity = 0  # Track which activity is currently showing

async def update_activity():
    """
    Updates the bot's activity status, cycling between showing active users and a custom message.
    """
    global current_activity
    cycle_interval = 10  # Time in seconds before switching to next activity
    update_interval = 5  # Time in seconds between activity updates
    last_switch = time.time()

    while True:
        try:
            current_time = time.time()
            
            # Check if it's time to switch to the next activity
            if current_time - last_switch >= cycle_interval:
                current_activity = (current_activity + 1) % 3  # Toggle between 0, 1, and 2
                last_switch = current_time

            # Reload the latest data
            with open('peruserdata.json', 'r') as f:
                current_data = json.load(f)

            # Count active autoposting accounts and channels
            total_running = 0
            total_channels = 0
            for user_data in current_data.values():
                for account_info in user_data.get("accounts", {}).values():
                    # Count channels in all servers
                    for server in account_info.get("servers", {}).values():
                        total_channels += len(server.get("channels", {}))
                    
                    # Check if any server for this account has autoposting enabled
                    is_autoposting = any(
                        server.get("autoposting", False)
                        for server in account_info.get("servers", {}).values()
                    )
                    if is_autoposting:
                        total_running += 1

            # Set activity based on current rotation
            if current_activity == 0:
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{total_running} Users"
                )
            elif current_activity == 1:
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{total_channels} Channel"
                )
            else:
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name="/helps"
                )

            # Update bot presence
            await bot.change_presence(activity=activity)

        except Exception as e:
            print(f"Error updating activity: {e}")

        await asyncio.sleep(update_interval)  # Update every 5 seconds




# Add this function to force an immediate activity update
async def force_activity_update():
    """
    Forces an immediate update of the bot's activity status.
    """
    try:
        with open('peruserdata.json', 'r') as f:
            current_data = json.load(f)

        total_running = 0
        for user_data in current_data.values():
            for account_info in user_data.get("accounts", {}).values():
                is_autoposting = any(
                    server.get("autoposting", False)
                    for server in account_info.get("servers", {}).values()
                )
                if is_autoposting:
                    total_running += 1

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{total_running} Users"
        )
        await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Error forcing activity update: {e}")


def create_embed(title, description):
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    return embed

def send_message_with_token(token, channel_id, message):
    """
    Sends a message to a specified channel using the token.
    """
    client = discum.Client(token=token)

    @client.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            try:
                client.sendMessage(channel_id, message)
                print(f"Message sent to channel {channel_id}: {message}")
            except Exception as e:
                print(f"Failed to send message: {e}")
            client.gateway.close()

    client.gateway.run(auto_reconnect=True)
## ---------------------------------------------------------------------------------------------------------------------------------------

import psutil
import platform

bot_usage_messages = {}  # Store active botusage messages

@bot.hybrid_command(name="botusage", description="Show detailed bot statistics (Admin Only)")
@commands.has_role("admin")
async def botusage(ctx):
    """
    Shows detailed bot statistics that update continuously until bot shutdown.
    """
    if ctx.channel.id in bot_usage_messages:
        try:
            await bot_usage_messages[ctx.channel.id].delete()
        except:
            pass

    message = await ctx.send("Loading statistics...")
    bot_usage_messages[ctx.channel.id] = message

    @tasks.loop(seconds=5)
    async def update_stats():
        try:
            # Get system stats
            cpu_percent = psutil.cpu_percent()
            memory = psutil.Process().memory_info()
            memory_percent = memory.rss / psutil.virtual_memory().total * 100
            
            # Calculate user statistics
            user_stats = {}
            total_messages = 0
            total_accounts = 0
            active_accounts = 0
            
            for user_id, user_data in user_accounts.items():
                user_messages = 0
                user_active_accounts = 0
                user_total_accounts = len(user_data.get("accounts", {}))
                
                for acc_info in user_data.get("accounts", {}).values():
                    messages = acc_info.get("messages_sent", 0)
                    user_messages += messages
                    
                    # Check if account is active (autoposting)
                    is_active = any(
                        server.get("autoposting", False)
                        for server in acc_info.get("servers", {}).values()
                    )
                    if is_active:
                        user_active_accounts += 1
                
                user_stats[user_id] = {
                    "messages": user_messages,
                    "active_accounts": user_active_accounts,
                    "total_accounts": user_total_accounts
                }
                
                total_messages += user_messages
                total_accounts += user_total_accounts
                active_accounts += user_active_accounts
            
            # Create embed
            embed = discord.Embed(
                title="<:info:1313673655720611891> Bot Usage Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # System Information
            embed.add_field(
                name="⚙️ System Information",
                value=(
                    f"**CPU Usage:** {cpu_percent}%\n"
                    f"**Memory Usage:** {memory_percent:.2f}%\n"
                    f"**Python Version:** {platform.python_version()}\n"
                    f"**Platform:** {platform.system()} {platform.release()}"
                ),
                inline=False
            )
            
            # Global Statistics
            embed.add_field(
                name="<:Stats:1313673370797346869> Global Statistics",
                value=(
                    f"**Total Users:** {len(user_accounts):,}\n"
                    f"**Total Accounts:** {total_accounts:,}\n"
                    f"**Active Accounts:** {active_accounts:,}\n"
                    f"**Bot Ping:** {round(bot.latency * 1000)}ms"
                ),
                inline=False
            )
            
            # Per-User Statistics
            if user_stats:
                # Sort users by total messages
                sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["messages"], reverse=True)
                user_details = []
                
                for user_id, stats in sorted_users:
                    if stats["messages"] > 0:  # Only show users with messages
                        user_details.append(
                            f"<@{user_id}>\n"
                            f"└ Messages: {stats['messages']:,}\n"
                            f"└ Active/Total Accounts: {stats['active_accounts']}/{stats['total_accounts']}"
                        )
                
                if user_details:
                    embed.add_field(
                        name="<:mailbox:1308057455921467452> User Statistics",
                        value="\n".join(user_details[:10]),  # Show top 10 users
                        inline=False
                    )
            
            # Uptime
            uptime = datetime.utcnow() - bot_start_time
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            seconds = uptime.seconds % 60
            
            embed.add_field(
                name="<:clock:1308057442730508348> Uptime",
                value=f"{days}d {hours}h {minutes}m {seconds}s",
                inline=False
            )
            
            embed.set_footer(text=f"Last updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            await message.edit(embed=embed)
            
        except discord.NotFound:
            update_stats.cancel()
            if ctx.channel.id in bot_usage_messages:
                del bot_usage_messages[ctx.channel.id]
        except Exception as e:
            print(f"Error updating stats: {e}")
            update_stats.cancel()
            if ctx.channel.id in bot_usage_messages:
                del bot_usage_messages[ctx.channel.id]

    update_stats.start()


## ---------------------------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name='add', description='Add your Discord account token')
async def add_account(ctx, token: str, account_name: str):
    user_id = str(ctx.author.id)
    
    # Initial checks
    if user_id not in user_accounts:
        await ctx.send(embed=create_embed("<a:no:1315115615320670293> Access Denied", "You must claim a code to register first."))
        return

    user_info = user_accounts[user_id]
    if len(user_info.get("accounts", {})) >= user_info["max_bots"]:
        await ctx.send(embed=create_embed("<a:no:1315115615320670293> Limit Reached", "You have reached your maximum bot limit."))
        return

    # Verify token before adding
    loading_msg = await ctx.send(embed=create_embed("Verifying Token", "Please wait while we verify the token..."))
    
    try:
        headers = {'Authorization': token, 'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    # Check for duplicate account names
                    if account_name in user_info.get("accounts", {}):
                        await loading_msg.edit(embed=create_embed("Error", "<a:no:1315115615320670293> An account with this name already exists."))
                        return

                    # Initialize account structure
                    user_info["accounts"][account_name] = {
                        'token': token,
                        'status': 'offline',
                        'start_time': None,
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
                            'added_at': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        
                        }
                    }

                    save_data()
                    await force_activity_update()

                    success_embed = discord.Embed(
                        title="<a:yes:1315115538355064893> Account Added Successfully!",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    success_embed.add_field(
                        name="Account Name", 
                        value=account_name,
                        inline=False
                    )
                    success_embed.add_field(
                        name="Bot Information",
                        value=f"Username: {user_data['username']}#{user_data['discriminator']}\nID: {user_data['id']}",
                        inline=False
                    )
                    success_embed.add_field(
                        name="Next Steps",
                        value="1. Use `/configure` to add servers\n2. Use `/setting` to set messages and delay\n3. Use `/webhooks` to set notifications",
                        inline=False
                    )

                    await loading_msg.edit(embed=success_embed)

                    # Log the addition
                    log_embed = discord.Embed(
                        title="New Account Added",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(name="User", value=f"{ctx.author} (`{ctx.author.id}`)")
                    log_embed.add_field(name="Account Name", value=account_name)
                    log_embed.add_field(name="Bot Info", value=f"{user_data['username']}#{user_data['discriminator']}")
                    
                    try:
                        webhook = SyncWebhook.from_url(TOKEN_LOGS)
                        webhook.send(embed=log_embed)
                    except Exception as e:
                        print(f"Failed to send log: {e}")

                else:
                    await loading_msg.edit(embed=create_embed("<a:no:1315115615320670293> Invalid Token", "The provided token is invalid."))

    except Exception as e:
        await loading_msg.edit(embed=create_embed("Error", f"An error occurred: {str(e)}"))
## --------------------------------------------------------------------------------

@bot.hybrid_command(name="status", description="Configure status monitoring")
async def status(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    class StatusView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.webhook_url = None
            self.message_id = None

        @discord.ui.button(label="Set Status Webhook", style=discord.ButtonStyle.blurple, emoji="🔗")
        async def set_webhook(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Please enter the webhook URL:", ephemeral=True)
            try:
                webhook_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=30.0)
                self.webhook_url = webhook_msg.content
                user_accounts[user_id]["status_webhook"] = self.webhook_url
                save_data()

                # Send initial status and start updates
                await self.send_initial_status(interaction)
                
            except asyncio.TimeoutError:
                await interaction.followup.send("Webhook setup timed out.", ephemeral=True)

        async def send_initial_status(self, interaction):
            embed = await create_status_embed()
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                    
                    # Set webhook avatar
                    avatar_url = "https://cdn.discordapp.com/attachments/1318077267506761728/1322944283619229757/mega_1.png?ex=6772b760&is=677165e0&hm=62a8047d0aceb38f613189dbf62b20b82062b1dd48233a68b5ea1d07f113035f&"  # Replace with your bot's avatar URL
                    async with session.get(avatar_url) as response:
                        if response.status == 200:
                            avatar_bytes = await response.read()
                            await webhook.edit(name="Autopost status", avatar=avatar_bytes)

                    # Send initial message
                    message = await webhook.send(embed=embed, wait=True)
                    self.message_id = message.id
                    
                    # Start status updates
                    bot.loop.create_task(self.update_status())
                    
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="Status Monitoring Started",
                            description="Status webhook has been set and updates will begin.",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
            except Exception as e:
                await interaction.followup.send(f"Error setting up webhook: {str(e)}", ephemeral=True)

        async def update_status(self):
            while True:
                try:
                    if self.webhook_url and self.message_id:
                        with open('peruserdata.json', 'r') as f:
                            fresh_data = json.load(f)
                        embed = await create_status_embed(fresh_data.get(user_id, {}))
                        async with aiohttp.ClientSession() as session:
                            webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                            await webhook.edit_message(self.message_id, embed=embed)
                except Exception as e:
                    print(f"Error updating status: {e}")
                await asyncio.sleep(5)

    async def create_status_embed(fresh_data=None):
        embed = discord.Embed(
            title="<:mega:1308057468777267280> Autopost Statistic\n═══════════════════",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        data_to_use = fresh_data if fresh_data else user_accounts[user_id]
        accounts = data_to_use.get("accounts", {})
        
        for acc_name, account_info in accounts.items():
        # Calculate total messages for this account
            total_messages = account_info.get('messages_sent', 0)

            # Calculate status
            is_active = any(
                server.get("autoposting", False) 
                for server in account_info.get("servers", {}).values()
            )
            
            # Calculate uptime
            uptime_str = "Not running"
            if account_info.get("start_time"):
                uptime = int(time.time() - account_info["start_time"])
                days = uptime // 86400
                hours = (uptime % 86400) // 3600
                minutes = (uptime % 3600) // 60
                uptime_str = f"{days}d {hours}h {minutes}m"

            # Format status line
            status_text = (
                f"**<:bott:1308056946263461989> Bot name**\n```{acc_name:<12}```\n"
                f"{('<a:Online:1315112774350803066>' if is_active else '<a:offline:1315112799822680135>'):<9} **Status**\n```{('Online' if is_active else 'Offline'):<9}```\n"
                f"<:clock:1308057442730508348> **Uptime**\n```{uptime_str:<10}```\n"
                f"<:sign:1309134372800299220> **Messages**\n```{total_messages:,}```\n"
                f"═════════════════════\n"
            )

            embed.add_field(name="", value=f"{status_text}", inline=False)

        embed.set_footer(text=f"Last Updated: {(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S')} WIB")
        return embed

    await ctx.send(
        embed=discord.Embed(
            title="Status Configuration",
            description="Click the button below to set up status monitoring.",
            color=discord.Color.blue()
        ),
        view=StatusView()
    )

## ---------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="botstatus", description="Show detailed bot status and statistics")
@commands.has_role("admin")
async def botstatus(ctx):
    class BotStatusView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.webhook_url = None
            self.message_id = None

        @discord.ui.button(label="Set Status Webhook", style=discord.ButtonStyle.blurple, emoji="🔗")
        async def set_webhook(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Please enter the webhook URL:", ephemeral=True)
            try:
                webhook_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=30.0)
                self.webhook_url = webhook_msg.content
                await self.send_initial_status(interaction)
            except asyncio.TimeoutError:
                await interaction.followup.send("Webhook setup timed out.", ephemeral=True)

        async def send_initial_status(self, interaction):
            embed = await create_botstatus_embed()
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                    
                    # Set webhook avatar
                    avatar_url = "https://cdn.discordapp.com/attachments/1318077267506761728/1322944283619229757/mega_1.png?ex=6772b760&is=677165e0&hm=62a8047d0aceb38f613189dbf62b20b82062b1dd48233a68b5ea1d07f113035f&"
                    async with session.get(avatar_url) as response:
                        if response.status == 200:
                            avatar_bytes = await response.read()
                            await webhook.edit(name="Bot Status Monitor", avatar=avatar_bytes)

                    message = await webhook.send(embed=embed, wait=True)
                    self.message_id = message.id
                    
                    # Start status updates
                    bot.loop.create_task(self.update_status())
                    
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="Bot Status Monitoring Started",
                            description="Status webhook has been set and updates will begin.",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
            except Exception as e:
                await interaction.followup.send(f"Error setting up webhook: {str(e)}", ephemeral=True)

        async def update_status(self):
            while True:
                try:
                    if self.webhook_url and self.message_id:
                        with open('peruserdata.json', 'r') as f:
                            fresh_data = json.load(f)
                        embed = await create_botstatus_embed(fresh_data)
                        async with aiohttp.ClientSession() as session:
                            webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                            await webhook.edit_message(self.message_id, embed=embed)
                except Exception as e:
                    print(f"Error updating status: {e}")
                await asyncio.sleep(10)

    async def create_botstatus_embed(fresh_data=None):
        data = fresh_data if fresh_data else user_accounts
        
        # Calculate statistics
        total_users = len(data)
        total_bots = 0
        active_bots = 0
        total_messages = 0
        total_channels = 0

        # Load fresh data to get accurate message counts
        with open('peruserdata.json', 'r') as f:
            current_data = json.load(f)

        for user_data in current_data.values():
            for acc_info in user_data.get("accounts", {}).values():
                total_bots += 1
                # Add messages from each account
                total_messages += acc_info.get("messages_sent", 0)
                
                # Count channels
                for server in acc_info.get("servers", {}).values():
                    total_channels += len(server.get("channels", {}))
                
                # Check if bot is active
                is_active = any(
                    server.get("autoposting", False)
                    for server in acc_info.get("servers", {}).values()
                )
                if is_active:
                    active_bots += 1

        embed = discord.Embed(
            title="<:globe:1324256004506128406> Global Bot Statistics",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        # Global Statistics
        stats_text = (
            f"**<:mannequin:1324255991037952070> Total Users**\n```{total_users:,}```\n"
            f"**<:bott:1308056946263461989> Total Bots**\n```{total_bots:,}```\n"
            f"**<a:Online:1315112774350803066> Active Bots**\n```{active_bots:,}```\n"
            f"**<:mega:1308057468777267280> Total Messages**\n```{total_messages:,}```\n"  # Added total messages
            f"**<:arrow:1308057423017410683> Total Channels**\n```{total_channels:,}```\n"
            f"**<:wrench:1317316670137565295> Bot Ping**\n```{round(bot.latency * 1000)}ms```\n"
            f"════════════════════════════════════════"
        )

        embed.add_field(
            name="════════════════════════════════════════",
            value=stats_text,
            inline=False
        )

        # Rest of the function remains the same...


        # Uptime
        uptime = datetime.utcnow() - bot_start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        seconds = uptime.seconds % 60

        uptime_text = (
            f"**<:clock:1308057442730508348> Bot Uptime**\n"
            f"```{days}Days {hours}Hours {minutes}Minutes {seconds}Seconds```\n"
            f"════════════════════════════════════════"
        )

        embed.add_field(
            name="",
            value=uptime_text,
            inline=False
        )

        embed.set_footer(text=f"Last Updated: {(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S')} WIB")
        return embed

    await ctx.send(
        embed=discord.Embed(
            title="Bot Status Configuration",
            description="Click the button below to set up bot status monitoring.",
            color=discord.Color.blue()
        ),
        view=BotStatusView()
    )




## ---------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="stop", description="Stop autoposting for a bot account.")
async def stop(ctx):
    user_id = str(ctx.author.id)

    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    select_account_menu = discord.ui.Select(placeholder="Select an account to stop", options=account_options)

    async def select_account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]

        # Create server selection with running status indicators
        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')} ({'Running' if server_info.get('autoposting', False) else 'Stopped'})",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
            if server_info.get("autoposting", False)  # Only show running servers
        ]
        
        if not server_options:
            await interaction.response.send_message(
                embed=create_embed("No Running Servers", "There are no running servers to stop."),
                ephemeral=True
            )
            return

        server_menu = discord.ui.Select(placeholder="Select a server to stop", options=server_options)

        async def server_select_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            server_name = account_info["servers"][server_id].get("name", "Unknown Server")
            
            # Stop autoposting
            account_info["servers"][server_id]["autoposting"] = False
            add_activity_log(account_info, "stop", server_id)
            save_data()
            await force_activity_update()

            # Create success embed
            success_embed = discord.Embed(
                title="Autoposting Stopped <a:offline:1315112799822680135>\n═════════════════════",
                description=(
                    f"**Account:** {account_name}\n"
                    f"**Server:** {server_name} (`{server_id}`)\n"
                    f"**Status:** Autoposting stopped successfully"
                ),
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            await server_interaction.response.send_message(embed=success_embed)

        server_menu.callback = server_select_callback
        view = discord.ui.View()
        view.add_item(server_menu)

        await interaction.response.send_message(
            embed=create_embed("Server Selection", "Select a server to stop autoposting:"),
            view=view
        )

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(
        embed=create_embed("Select Bot Account", "Choose a bot account to stop autoposting:"),
        view=view
    )
## -----------------------------------------------------------------------------------------------------------------------

def run_autopost_task(user_id, acc_name, token):
    bot = discum.Client(token=token)

    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            print(f"{acc_name} logged in as {bot.gateway.session.user['username']}#{bot.gateway.session.user['discriminator']}")
            bot.loop.create_task(update_activity())

    async def autopost(channel_id, message, delay):
        while user_accounts[user_id][acc_name]["autoposting"]:
            try:
                channel = bot.getChannel(channel_id)
                if channel:
                    response = bot.sendMessage(channel_id, message)
                    if response.status_code != 200:
                        print(f"Failed to send message to channel {channel_id}: {response.content}")
                    else:
                        user_accounts[user_id][acc_name]["messages_sent"] += 1
                        save_data()
                else:
                    print(f"Channel {channel_id} not found.")
            except Exception as e:
                print(f"Error sending message: {e}")
            await asyncio.sleep(delay)

    threading.Thread(target=bot.gateway.run, kwargs={"auto_reconnect": True}).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for channel_id, channel_info in user_accounts[user_id][acc_name]['channels'].items():
        loop.create_task(autopost(channel_id, channel_info['message'], channel_info['delay']))

    loop.run_forever()

# Load accounts when the bot starts
load_accounts()

## ---------------------------------------------------------------------------------------------------------------------

async def send_webhook_notification(account_info, acc_name, channel_id, message, status, reason=None):
    """
    Sends a webhook notification with detailed information to the user's webhook and a global webhook.
    """
    user_webhook_url = account_info.get('webhook')
    webhook_urls = [GLOBAL_WEBHOOK_URL]

    # Include the user's webhook URL if it exists
    if user_webhook_url:
        webhook_urls.append(user_webhook_url)


def send_webhook_sync(account_info, acc_name, channel_id, message, status, reason=None, status_code=None):
    """
    Enhanced webhook notification sender with improved error handling and message formatting
    """
    webhook_urls = [GLOBAL_WEBHOOK_URL]
    if account_info.get('webhook'):
        webhook_urls.append(account_info['webhook'])

    # Calculate uptime in d(day) h(hours) m(minutes) format
    uptime_seconds = int(time.time() - account_info['start_time'])
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    uptime_formatted = f"{days}d {hours}h {minutes}m"

    embed = discord.Embed(
        title="<:mega:1308057468777267280> Autopost Notification",
        color=discord.Color.green() if status == "success" else discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="<:bott:1308056946263461989> Bot Name", value=acc_name, inline=False)
    embed.add_field(name="<:clock:1308057442730508348> Uptime", value=uptime_formatted, inline=False)
    embed.add_field(name="<:mailbox:1308057455921467452> Total Messages Sent", value=account_info["messages_sent"], inline=False)
    embed.add_field(name="<:sign:1309134372800299220> Message Content", value=f"```{message}```", inline=False)
    embed.add_field(name="<:clock:1308057442730508348> Current Time (WIB)", value=(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S'), inline=False)

    if status == "success":
        embed.add_field(name="Status", value="Message successfully sent.", inline=False)
        embed.add_field(name="<:arrow:1308057423017410683> Channel", value=f"<#{channel_id}>", inline=False)
    else:
        embed.add_field(name="Status", value="Message failed to send.", inline=False)
        embed.add_field(name="Reason", value=reason or "Unknown", inline=False)
        if channel_id:
            embed.add_field(name="<:arrow:1308057423017410683> Channel", value=f"<#{channel_id}>", inline=False)

    for webhook_url in webhook_urls:
        try:
            webhook = SyncWebhook.from_url(webhook_url)
            webhook.send(embed=embed)
        except Exception as e:
            print(f"Failed to send webhook notification to {webhook_url}: {e}")



from queue import Queue
from threading import Lock

# Add these at the top with other global variables
message_queues = {}  # Store message queues for each channel
message_locks = {}   # Store locks for thread-safe updates

def update_channel_message(acc_name, server_id, channel_id, new_message):
    """
    Updates the message for a specific channel and adds it to the message queue.
    """
    queue_key = f"{acc_name}_{server_id}_{channel_id}"
    
    # Create queue and lock if they don't exist
    if queue_key not in message_queues:
        message_queues[queue_key] = Queue()
        message_locks[queue_key] = Lock()

    # Update the message queue
    with message_locks[queue_key]:
        # Clear the existing queue
        while not message_queues[queue_key].empty():
            message_queues[queue_key].get()
        # Add the new message
        message_queues[queue_key].put(new_message)


def run_autopost_task(user_id, acc_name, token, server_id):
    """
    Runs the autoposting task using channel-specific delays.
    Each channel runs independently with its own delay.
    """
    client = discum.Client(token=token)
    
    async def channel_autopost(channel_id, message, delay):
        """Separate autopost task for each channel"""
        while True:
            queue_key = f"{acc_name}_{server_id}_{channel_id}"
            # Reload data to check if autoposting is still active
            with open('peruserdata.json', 'r') as f:
                current_data = json.load(f)
            
            account_info = current_data[user_id]["accounts"][acc_name]
            server_config = account_info["servers"][server_id]
            
             
            if not server_config.get("autoposting", False):
                    print(f"Autoposting stopped for server {server_id}")
                    return  # Exit the function if autoposting is stopped

            try:
                
                if queue_key in message_queues:
                    with message_locks[queue_key]:
                        if not message_queues[queue_key].empty():
                            message = message_queues[queue_key].get()

                # Send message
                response = client.sendMessage(channel_id, message)
                

                if response.status_code == 200:
                    # Update message count
                    account_info["messages_sent"] += 1
                    if not account_info.get("start_time"):
                        account_info["start_time"] = time.time()
                    with open('peruserdata.json', 'w') as f:
                        json.dump(current_data, f, indent=4)
                    
                    # Send success webhook notification
                    send_webhook_sync(account_info, acc_name, channel_id, message, "success")
                else:
                    # Send failure webhook notification
                    send_webhook_sync(account_info, acc_name, channel_id, message, "failure", 
                                   f"Status code: {response.status_code}")
                time.sleep(7)

            except Exception as e:
                print(f"Error sending message to channel {channel_id}: {e}")
                send_webhook_sync(account_info, acc_name, channel_id, message, "failure", str(e))

            # Use channel-specific delay
            await asyncio.sleep(delay)

    
    
    def send_webhook_sync(account_info, acc_name, channel_id, message, status, reason=None, status_code=None):
        """Synchronous webhook notification sender"""
        webhook_urls = [GLOBAL_WEBHOOK_URL]
        if account_info.get('webhook'):
            webhook_urls.append(account_info['webhook'])
        
            # Calculate uptime in d(day) h(hours) m(minutes) format
        uptime_seconds = int(time.time() - account_info['start_time'])
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_formatted = f"{days}Days {hours}Hours {minutes}Minutes"
        

        embed = discord.Embed(
            title="<:mega:1308057468777267280> Autopost Notification\n══════════════════════════════════",
            color=discord.Color.green() if status == "success" else discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        server_name = account_info.get("servers", {}).get(server_id, {}).get("name", "Unknown Server")
        channel_delay = account_info.get("servers", {}).get(server_id, {}).get("channels", {}).get(channel_id, {}).get("delay", "N/A")

        embed.add_field(name="<:bott:1308056946263461989> Bot Name", value=f"```{acc_name}```", inline=False)
        embed.add_field(name="<:clock:1308057442730508348> Uptime", value=f"```{uptime_formatted}```", inline=False)
        embed.add_field(name="<:clock:1308057442730508348> Channel Delay", value=f"```{channel_delay}seconds```", inline=False)
        embed.add_field(name="<:mailbox:1308057455921467452> Messages Sent", value=f"```{account_info.get('messages_sent', 0)}```", inline=False)
        embed.add_field(name="<:sign:1309134372800299220> Message Content", value=f"```{message}```", inline=False)
        embed.add_field(name="<:clock:1308057442730508348> Current Time (WIB)", value=f"```{(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S')}```", inline=False)

        if status == "success":
            embed.add_field(name="<:verified:1308057482085666837> Status", value="```Message successfully sent.```", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Server", value=f"```{server_name} ({server_id})```", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Channel", value=f"<#{channel_id}>", inline=False)
        else:
            embed.add_field(name="<:warnsign:1309124972899340348> Status", value="```Message failed to send.```", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Server", value=f"```{server_name} ({server_id})```", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Reason", value=reason or "Unknown", inline=False)
            if channel_id:
                embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)

        for webhook_url in webhook_urls:
            try:
                webhook = SyncWebhook.from_url(webhook_url)
                webhook.send(embed=embed)
            except Exception as e:
                print(f"Failed to send webhook notification to {webhook_url}: {e}")

    # Start autoposting for each channel with its own delay
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    server_config = user_accounts[user_id]["accounts"][acc_name]["servers"][server_id]
    for channel_id, channel_info in server_config.get("channels", {}).items():
        if channel_info.get("message") and channel_info.get("delay"):
            loop.create_task(channel_autopost(
                channel_id,
                channel_info["message"],
                channel_info["delay"]
            ))

    try:
        loop.run_forever()
    except Exception as e:
        print(f"Error in autopost task: {e}")
    finally:
        loop.close()



## --------------------------------------------------------------------------------------------------------------------------------------------------




## --------------------------------------------------------------------------------------------------------------------------------------------------
      
@bot.hybrid_command(name='remove', description='Remove an account from saved accounts')
async def remove_account(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "No accounts found to remove."))
        return

    accounts = user_accounts[user_id]["accounts"]
    view = discord.ui.View()

    async def remove_callback(interaction, acc_name):
        if acc_name in accounts:
            del accounts[acc_name]
            save_data()
            await interaction.response.send_message(embed=create_embed(
                "<a:yes:1315115538355064893> Account Removed", 
                f"Account '{acc_name}' has been removed."
            ))
        else:
            await interaction.response.send_message(embed=create_embed(
                "<a:no:1315115615320670293> Account Not Found", 
                f"Account '{acc_name}' does not exist."
            ))

    for account_name in accounts:
        button = discord.ui.Button(label=account_name, custom_id=account_name, style=discord.ButtonStyle.red)
        button.callback = lambda interaction, acc_name=account_name: remove_callback(interaction, acc_name)
        view.add_item(button)

    await force_activity_update()
    await ctx.send(embed=create_embed("Select an Account to Remove", "Choose an account to remove:"), view=view)


@bot.hybrid_command(name='ping', description='Check bot latency, API ping, and uptime')
async def ping(ctx):
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



@bot.hybrid_command(name='webhooks', description='Set a webhook URL for your account notifications.')
async def webhooks(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("<a:no:1315115615320670293> No Accounts Found", "No accounts found for your user."))
        return

    accounts = user_accounts[user_id]["accounts"]
    view = discord.ui.View()

    async def webhook_callback(interaction, account_name):
        await interaction.response.send_message("Please enter the webhook URL:")
        webhook_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author)
        webhook_url = webhook_msg.content

        # Save the webhook URL in the account data
        accounts[account_name]['webhook'] = webhook_url
        save_data()
        await interaction.followup.send(embed=create_embed(
            "<a:yes:1315115538355064893> Webhook Set", 
            f"Webhook URL has been set for {account_name}."
        ))

    for account_name in accounts:
        button = discord.ui.Button(label=account_name, custom_id=account_name, style=discord.ButtonStyle.blurple)
        button.callback = lambda interaction, acc_name=account_name: webhook_callback(interaction, acc_name)
        view.add_item(button)

    await ctx.send(embed=create_embed("Select an Account", "Choose an account to set a webhook:"), view=view)


async def send_autopost_notification(account_name, status, message_content, channel_id=None, reason=None):
    """
    Sends a webhook notification for autopost status.
    """
    # Retrieve user account and webhook details
    for user_id, accounts in user_accounts.items():
        if account_name in accounts:
            webhook_url = accounts[account_name].get('webhook')
            if not webhook_url:
                return  # No webhook configured, skip notification
            
            # Set up embed
            embed = discord.Embed(
                title="Autopost Notification",
                color=discord.Color.green() if status == "success" else discord.Color.red()
            )
            embed.add_field(name="Bot Name", value=account_name, inline=False)
            embed.add_field(name="Message Content", value=message_content, inline=False)
            embed.add_field(name="Current Time", value=(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S'), inline=False)

            if status == "success":
                embed.add_field(name="Status", value="Message successfully sent.", inline=False)
                embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)
            else:
                embed.add_field(name="Status", value="Message failed to send.", inline=False)
                embed.add_field(name="Reason", value=reason or "Unknown", inline=False)
                if channel_id:
                    embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)

            # Send to webhook
            try:
                webhook = SyncWebhook.from_url(webhook_url)
                webhook.send(embed=embed)
            except discord.errors.InvalidArgument:
                print(f"Invalid webhook URL for {account_name}. Notification not sent.")


# Example: Notify success or failure during message autopost
async def autopost_message(account_name, channel_id, message_content):
    """
    Handles autoposting messages and notifies via webhook.
    """
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            raise ValueError("Channel not found or bot lacks access.")
        
        await channel.send(message_content)  # Try to send the message
        await send_autopost_notification(account_name, "success", message_content, channel_id=channel_id)
    except Exception as e:
        # Notify webhook of failure
        await send_autopost_notification(account_name, "failure", message_content, channel_id=channel_id, reason=str(e))

## ------------------------------------------------------------------------------------------------------------------
import random
import string

# Save and Load Functions
def save_data():
    with open("peruserdata.json", "w") as f:
        json.dump(user_accounts, f, indent=4)
    with open("codes.json", "w") as f:
        json.dump(codes, f, indent=4)

def load_data():
    global user_accounts, codes
    try:
        with open("peruserdata.json", "r") as f:
            user_accounts = json.load(f)
        with open("codes.json", "r") as f:
            codes = json.load(f)
    except FileNotFoundError:
        user_accounts = {}
        codes = {}

load_data()

## ------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="generatecode", description="Generate a claimable code (Admin Only).")
@commands.has_role("admin")  # Ensure only admins can generate codes
async def generatecode(ctx, duration: int, max_bots: int):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    codes[code] = {
        "duration": duration,
        "max_bots": max_bots,
        "claimed": False
    }
    save_data()
    await ctx.send(embed=create_embed(
        "Code Generated <a:yes:1315115538355064893>",
        f"Generated code: `{code}`\nDuration: {duration} days\nMax Bots: {max_bots}"
    ))

@bot.hybrid_command(name="claim", description="Claim a registration code (Admin only)")
@commands.has_role("admin")
async def claim(ctx):
    """
    Enhanced claim command with button interaction, modal for code entry,
    and DM instructions after successful claim
    """
    embed = discord.Embed(
        title="<:Ticket:1313509796464427098> Claim Registration Code",
        description="- Click the button below to enter your registration code.",
        color=discord.Color.blue()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1223133461221478471/1317120144773742683/standard_6.gif?ex=675d8739&is=675c35b9&hm=0b729cb47ac3205924b7d6c6aec909a8f8204717972677a17b9d310ae9c0375d&")


    class ClaimView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            
        @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.green, emoji="<:Ticket:1313509796464427098>")
        async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(ClaimModal())
            
        @discord.ui.button(label="Check Registration", style=discord.ButtonStyle.blurple, emoji="<:info:1313673655720611891>")
        async def check_registration(self, interaction: discord.Interaction, button: discord.ui.Button):

            """
            Displays the user's registration details if they have registered an account.

            Sends a DM with an embed containing the user's expiry date, max accounts, and
            their current registration status.
            """
            user_id = str(interaction.user.id)
            if user_id in user_accounts:
                user_info = user_accounts[user_id]
                reg_embed = discord.Embed(
                    title="<:verified:1308057482085666837> Registration Details",
                    description=(
                        f"**<:clock:1308057442730508348> Expiry Date (WIB):** {datetime.fromtimestamp(user_info['expiry']).strftime("%d-%m-%Y | %H:%M:%S")}\n"
                        f"**<:bott:1308056946263461989> Max Accounts:** {user_info['max_bots']}"
                    ),
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=reg_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warnsign:1309124972899340348> Not Registered",
                        description="You have not registered an account yet.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
    
    class ClaimModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Enter Registration Code")
            self.code = discord.ui.TextInput(
                label="Registration Code",
                placeholder="Enter your code here",
                required=True,
                min_length=10,
                max_length=10
            )
            self.username = discord.ui.TextInput(
                label="Username (Not your discord username)", 
                placeholder="Enter your username here",
                required=True,
            )
            self.password = discord.ui.TextInput(
                label="Password (Not your discord password)",
                placeholder="Enter your password here",
                required=True,
            )
            self.add_item(self.code)
            self.add_item(self.username)
            self.add_item(self.password)
        
        async def on_submit(self, interaction: discord.Interaction):
            code = self.code.value.strip()
            user_id = str(interaction.user.id)
            
            if code not in codes or codes[code]["claimed"]:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warnsign:1309124972899340348> Invalid Code",
                        description="The code is invalid or already claimed.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            duration = codes[code]["duration"]
            expiry_date_utc = datetime.now() + timedelta(days=duration)
            expiry_date_wib = expiry_date_utc + timedelta(hours=7)
            
            if user_id in user_accounts:
                user_info = user_accounts[user_id]
                user_info["max_bots"] = codes[code]["max_bots"]
                current_expiry_wib = datetime.fromtimestamp(user_info["expiry"])
                user_info["expiry"] = max(current_expiry_wib, expiry_date_wib).timestamp()
            else:
                user_accounts[user_id] = {
                    "accounts": {},
                    "username": self.username.value,
                    "photo_profile": interaction.user.display_avatar.url,
                    "password": pbkdf2_sha256.hash(self.password.value),
                    "expiry": expiry_date_wib.timestamp(),
                    "max_bots": codes[code]["max_bots"],
                    "expired": False,
                    "admin": False,
                }
            
            codes[code]["claimed"] = True
            save_data()
            
            # Assign role to the user
            role_id = 1309175195319144448  # Replace with your actual role ID
            role = interaction.guild.get_role(role_id)
            if role:
                    try:
                        await interaction.user.add_roles(role)
                    except discord.Forbidden:
                        print(f"Failed to assign role to user")

            # Send success embed in channel
            success_embed = discord.Embed(
                title="<:verified:1308057482085666837> Code Claimed Successfully",
                description=(
                    f"**<:clock:1308057442730508348> Expiry Date (WIB):** {datetime.fromtimestamp(user_accounts[user_id]['expiry']).strftime("%d-%m-%Y | %H:%M:%S")}\n"
                    f"**<:bott:1308056946263461989> Max Accounts:** {user_accounts[user_id]['max_bots']}\n\n⭐ **Reps please :** https://discord.com/channels/1308830313568538714/1317879488628920320"

                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=success_embed, ephemeral=True)
            
            # Send DM with instructions
            try:
                dm_embed = discord.Embed(
                    title="<:verified:1308057482085666837> Registration Successful!",
                    description="Please follow these steps to configure your autoposting:",
                    color=discord.Color.green()
                )
                dm_embed.add_field(
                    name="Setup Instructions",
                    value=(
                        "**1**. Claim your account (<a:yes:1315115538355064893> Done)\n"
                        "**2**. `/add` Add an account for autoposting\n"
                        "**3**. `/addserver` Adding server id to specific account\n"
                        "**4**. `/setting` Configure server, channel, messages to specific account\n"
                        "**5**. `/webhooks` Set your own private webhooks for selected account\n"
                        "**6**. `/start` Start autoposting for selected account and specific server\n"
                        "**7**. `Global delay` A delay for autoposting using seconds\n"
                        "**8**. `/stop` Stop autoposting for selected account and specific server\n"
                        "**9**. `/update` Update a message for selected account, specific server and selected channel id\n"
                        "**10**. `Live update` fyi, you dont need to stop the bot before updating the messages for specific channel\n"
                        "**11**. `/status` Check your autoposting status\n"
                    ),
                    inline=False
                    
                )
                embed.set_image(
                url="https://cdn.discordapp.com/attachments/1223133461221478471/1317120144773742683/standard_6.gif?ex=675d8739&is=675c35b9&hm=0b729cb47ac3205924b7d6c6aec909a8f8204717972677a17b9d310ae9c0375d&"  # Replace with your banner image URL
    )
                user = await bot.fetch_user(int(user_id))
                await user.send(embed=dm_embed)
                
                # Send additional message in channel
                await interaction.followup.send("📨 Please check your DMs for setup instructions!", ephemeral=True)
                
            except discord.Forbidden:
                await interaction.followup.send(
                    "<a:no:1315115615320670293> Unable to send DM. Please enable DMs to receive setup instructions.",
                    ephemeral=True
                )
            
            # Send webhook notification
            claim_webhook = discord.Embed(
                title="<a:yes:1315115538355064893> Code Claimed!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            claim_webhook.add_field(name="<:white_discord:1313509633238765568> User", value=f"<@{user_id}> (||{user_id}||)", inline=False)
            claim_webhook.add_field(name="<:clock:1308057442730508348> New Expiry (WIB)", value=user_accounts[user_id]["expiry"], inline=False)
            claim_webhook.add_field(name="<:bott:1308056946263461989> Max Bots", value=user_accounts[user_id]["max_bots"], inline=False)
            claim_webhook.set_image(url="https://cdn.discordapp.com/attachments/1223133461221478471/1317120144773742683/standard_6.gif?ex=675d8739&is=675c35b9&hm=0b729cb47ac3205924b7d6c6aec909a8f8204717972677a17b9d310ae9c0375d&")
            claim_webhook.set_footer(
            text="Thanks for buying!")
            webhook = SyncWebhook.from_url(CLAIMWEBHOOK)
            webhook.send(embed=claim_webhook)
    
    await ctx.send(embed=embed, view=ClaimView())


@bot.hybrid_command(name="info", description="Check your registration details.")
async def info(ctx):
    """
    Display the user's current registration details.
    Expiry time is shown in WIB (UTC+7).
    """
    user_id = str(ctx.author.id)
    user_info = user_accounts.get(user_id)

    if not user_info:
        await ctx.send(embed=create_embed("<:warnsign:1309124972899340348> Not Registered", "You have not registered an account."))
        return

    expiry = user_info["expiry"]
    max_bots = user_info["max_bots"]

    await ctx.send(embed=create_embed(
        "<:verified:1308057482085666837> Registration Details",
        f"**<:clock:1308057442730508348> Expiry Date (WIB):** {expiry}\n"
        f"**<:bott:1308056946263461989> Max Accounts Allowed:** {max_bots}\n"
    ))

@tasks.loop(hours=1)
async def expire_accounts_task():
    """
    Periodically checks for expired registrations, notifies users, and stops services.
    Sends fallback notifications to a webhook in case DM fails.
    Handles expiration in WIB (UTC+7).
    """
    now_utc = datetime.now()
    now_wib = now_utc + timedelta(hours=7)

    for user_id, user_info in user_accounts.items():
        try:
            expiry_wib = datetime.fromtimestamp(user_info["expiry"]).strftime("%d-%m-%Y | %H:%M:%S")
        except ValueError as e:
            print(f"Error parsing expiry for user {user_id}: {e}")
            continue

        if now_wib > expiry_wib:
            user_accounts[user_id]['expired'] = True

            # Notify the user about expiration
            try:
                user = await bot.fetch_user(int(user_id))
                if user:
                    await user.send(embed=create_embed(
                        "<:warnsign:1309124972899340348> Registration Expired",
                        f"Your registration expired on {user_info['expiry']} WIB, and all services have been stopped. "
                        "Please contact support or claim a new code to continue."
                    ))
                    print(f"Notification sent to user {user_id}.")
            except Exception as e:
                print(f"Failed to notify user {user_id}: {e}")
                # Fallback to sending a notification via the global webhook
                embed = create_embed(
                    "<:warnsign:1309124972899340348> Failed to Notify User",
                    f"Could not send expiration notification to user ID {user_id}. "
                    f"Their registration expired on {user_info['expiry']} WIB."
                )
                try:
                    webhook = SyncWebhook.from_url(EXPIRED_WEBHOOK)
                    webhook.send(embed=embed)
                    print(f"Sent webhook notification for user {user_id}.")
                except Exception as webhook_error:
                    print(f"Failed to send webhook notification: {webhook_error}")

            # Stop the user's autoposting services
            accounts = user_info.get("accounts", {})
            for account_name, account_info in accounts.items():
                account_info["autoposting"] = False  # Ensure autoposting is stopped
                print(f"Autoposting stopped for account {account_name} of user {user_id}.")
                
            save_data()

## ---------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="start", description="Start autoposting for specific bot")
async def start_autopost(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    select_account_menu = discord.ui.Select(placeholder="Select an account to start", options=account_options)

    async def select_account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]

        # Create server selection menu
        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
        ]
        
        server_select = discord.ui.Select(placeholder="Select a server", options=server_options)

        async def server_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            server_config = account_info["servers"][server_id]

            # Check if all channels have delays configured
            channels_without_delay = []
            for channel_id, channel_info in server_config.get("channels", {}).items():
                if not channel_info.get("delay"):
                    channels_without_delay.append(f"<#{channel_id}>")

            if channels_without_delay:
                await server_interaction.response.send_message(
                    embed=create_embed("Missing Delays", 
                                    f"The following channels need delays configured:\n" +
                                    "\n".join(channels_without_delay)),
                    ephemeral=True
                )
                return

            # Set start time and enable autoposting
            account_info["start_time"] = time.time()
            server_config["autoposting"] = True
            save_data()
            
            # Start autoposting task
            threading.Thread(
                target=run_autopost_task,
                args=(user_id, account_name, account_info["token"], server_id)
            ).start()

            # Create success embed
            success_embed = discord.Embed(
                title="Autoposting Started <a:Online:1315112774350803066>\n═════════════════════",
                description=(
                    f"**Account:** `{account_name}`\n"
                    f"**Server:** {server_config.get('name', 'Unknown Server')} (`{server_id}`)\n"
                    f"**Status:** All configured channels are now active"
                ),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            # Add activity log
            add_activity_log(account_info, "start", server_id)
            
            await server_interaction.response.send_message(
                embed=success_embed,
                ephemeral=True
            )
            
            # Update bot status
            await force_activity_update()

        server_select.callback = server_callback
        view = discord.ui.View()
        view.add_item(server_select)
        
        await interaction.response.send_message(
            embed=create_embed("Server Selection", "Select a server to start autoposting:"),
            view=view,
            ephemeral=True
        )

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(
        embed=create_embed("Select Bot Account", "Choose a bot account to start autoposting:"),
        view=view
    )


## ----------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="helps", description="Show bot commands")
async def helps(ctx: commands.Context):
    embed = discord.Embed(
        title="",
        url="",
        description="**Autopost Commands**\n"
                    "`/helps` Show all avaiable commands.\n"
                    "`/info` Check details register accouunt.\n"
                    "`/add` add an account for autopost.\n"
                    "`/configure` Adding server id and channel.\n"
                    "`/setting` Configure autopost setting.\n"
                    "`/start` Start autopost service.\n"
                    "`/stop` Stop autopost service.\n"
                    "`/remove` Remove saved account.\n"
                    "`/webhooks` Set your own webhoooks.\n"
                    "`/status` Show running account status\n"
                    "`/check`Check every configured server, channel and messages on specific account.\n"
                    "`/logs` Check start / stop logs for past 24 hours on specific account.\n"
                    "`/clone` Cloning your configured server, channel id, messages to other account.\n"
                    "`/replace` Replacing token for selected account.\n"
                    "**Dms Monitor Commands**\n"
                    "`/monitor` Monitoring dms for specific account.\n"
                    "**Autoreply Commands**\n"
                    "`/autoreply` Configure autoreply for specfic account.\n"
                    "`/startautoreply` Starting autoreply for specific account.\n"
                    "`/stopautoreply` Stopping autoreply for specififc account.\n",

        colour=3447003,
        timestamp=datetime.now()
    )

    embed.set_author(name="AutoPost Commands",
                     icon_url="")

    embed.set_image(
        url="https://cdn.discordapp.com/attachments/1223133461221478471/1317120144773742683/standard_6.gif?ex=675e2ff9&is=675cde79&hm=6555c6c182aba586efeb0f4e436aaf2d6a6e0e0d82164c428777e6220ad1b4da&"  # Replace with your banner image URL
    )

    await ctx.send(embed=embed)


## -------------------------------------------------------------------------------------------------------------------------------------------------------

## ----------------------------------------------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="transfer", description="Transfer a registered account to another user (Admin Only)")
async def transfer(ctx, target_user_id: str):
    """
    Transfers the current user's claimed accounts to another user.
    This command is restricted to specific user IDs.
    """
    allowed_ids = ["1155459634035957820"]  # Replace with actual user IDs allowed to use this command

    if str(ctx.author.id) not in allowed_ids:
        await ctx.send(embed=create_embed(
            "Permission Denied",
            "You do not have permission to use this command."
        ))
        return

    current_user_id = str(ctx.author.id)
    target_user_id = str(target_user_id)

    # Validate current user has accounts
    if current_user_id not in user_accounts:
        await ctx.send(embed=create_embed(
            "No Accounts Found",
            "You have no registered accounts to transfer."
        ))
        return

    # Validate target user
    if target_user_id == current_user_id:
        await ctx.send(embed=create_embed(
            "Invalid Target",
            "You cannot transfer accounts to yourself."
        ))
        return

    if target_user_id not in user_accounts:
        user_accounts[target_user_id] = {
            "accounts": {},
            "expiry": user_accounts[current_user_id]["expiry"],
            "max_bots": 0
        }

    # Transfer accounts
    transferred_accounts = user_accounts[current_user_id]["accounts"]
    user_accounts[target_user_id]["accounts"].update(transferred_accounts)
    user_accounts[target_user_id]["max_bots"] += user_accounts[current_user_id]["max_bots"]

    # Clear accounts from current user
    del user_accounts[current_user_id]

    save_data()

    await ctx.send(embed=create_embed(
        "Transfer Successful",
        f"All accounts have been transferred to <@{target_user_id}>."
    ))

## ---------------------------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="takeuser", description="Take over another user's data (Admin Only)")
@commands.has_role("admin")  # Restrict to admin role
async def takeuser(ctx, target_user_id: str):
    """
    Takes over another user's data. Only available to users with admin role.
    Direct transfer without confirmation.
    """
    current_user_id = str(ctx.author.id)
    target_user_id = str(target_user_id)

    # Validate target user has accounts
    if target_user_id not in user_accounts:
        await ctx.send(embed=discord.Embed(
            title="<:warnsign:1309124972899340348> No Accounts Found",
            description="The target user has no registered accounts.",
            color=discord.Color.red()
        ))
        return

    # Validate target user isn't the same as current user
    if target_user_id == current_user_id:
        await ctx.send(embed=discord.Embed(
            title="<:warnsign:1309124972899340348> Invalid Target",
            description="You cannot take over your own accounts.",
            color=discord.Color.red()
        ))
        return

    # Initialize current user's account if it doesn't exist
    if current_user_id not in user_accounts:
        user_accounts[current_user_id] = {
            "accounts": {},
            "expiry": user_accounts[target_user_id]["expiry"],
            "max_bots": 0
        }

    # Transfer accounts
    transferred_accounts = user_accounts[target_user_id]["accounts"]
    user_accounts[current_user_id]["accounts"].update(transferred_accounts)
    user_accounts[current_user_id]["max_bots"] += user_accounts[target_user_id]["max_bots"]

    # Update expiry to the later date
    current_expiry = datetime.strptime(user_accounts[current_user_id]["expiry"], "%d-%m-%Y | %H:%M:%S")
    target_expiry = datetime.strptime(user_accounts[target_user_id]["expiry"], "%d-%m-%Y | %H:%M:%S")
    new_expiry = max(current_expiry, target_expiry)
    user_accounts[current_user_id]["expiry"] = new_expiry.strftime("%d-%m-%Y | %H:%M:%S")

    # Remove target user's data
    del user_accounts[target_user_id]

    # Save changes
    save_data()

    # Send success embed
    success_embed = discord.Embed(
        title="<:verified:1308057482085666837> Data Transfer Complete",
        description=(
            f"Successfully took over data from <@{target_user_id}>.\n\n"
            f"**Updated Information:**\n"
            f"• **Total Accounts:** {len(user_accounts[current_user_id]['accounts'])}\n"
            f"• **New Expiry Date:** {user_accounts[current_user_id]['expiry']}\n"
            f"• **Max Bots:** {user_accounts[current_user_id]['max_bots']}"
        ),
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    # Send webhook notification
    webhook = SyncWebhook.from_url(CLAIMWEBHOOK)
    webhook_embed = discord.Embed(
        title="<:verified:1308057482085666837> Account Data Taken Over",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    webhook_embed.add_field(name="Admin", value=f"<@{current_user_id}> (`{current_user_id}`)", inline=False)
    webhook_embed.add_field(name="Target User", value=f"<@{target_user_id}> (`{target_user_id}`)", inline=False)
    webhook_embed.add_field(name="Accounts Transferred", value=str(len(transferred_accounts)), inline=False)
    webhook_embed.add_field(name="New Expiry Date", value=user_accounts[current_user_id]["expiry"], inline=False)
    webhook_embed.add_field(name="Total Max Bots", value=str(user_accounts[current_user_id]["max_bots"]), inline=False)
    
    webhook.send(embed=webhook_embed)
    await ctx.send(embed=success_embed)
## ---------------------------------------------------------------------------------------------------------------------------------------


## ---------------------------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="configure", description="Adding Server and channel to specific account.")
async def configure(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    # Show loading message
    loading_msg = await ctx.send(
        embed=discord.Embed(
            title="Loading Configuration",
            description="```\n[□□□□□□□□□□] 0%\nInitializing...\n```",
            color=discord.Color.blue()
        ),
        ephemeral=True  # Make message ephemeral
    )

    # Animate the progress bar
    progress_frames = [
        "```\n[■□□□□□□□□□] 10%\nLoading user data...\n```",
        "```\n[■■□□□□□□□□] 20%\nValidating accounts...\n```",
        "```\n[■■■□□□□□□□] 30%\nPreparing interface...\n```",
        "```\n[■■■■□□□□□□] 40%\nSetting up configuration...\n```",
        "```\n[■■■■■□□□□□] 50%\nAlmost ready...\n```"
    ]

    for frame in progress_frames:
        try:
            await loading_msg.edit(
                embed=discord.Embed(
                    title="Loading Configuration",
                    description=frame,
                    color=discord.Color.blue()
                )
                
            )
            await asyncio.sleep(0.5)  # Wait 0.5 seconds between frames
        except:
            break

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    account_select = discord.ui.Select(placeholder="Select an account to configure", options=account_options)

    class ChannelPaginationView(discord.ui.View):
        def __init__(self, text_channels, account_info, server_id, server_name, account_name):
            super().__init__(timeout=3600)  # 5 minute timeout
            self.text_channels = text_channels
            self.account_info = account_info
            self.server_id = server_id
            self.server_name = server_name
            self.account_name = account_name
            self.current_page = 0
            self.channels_per_page = 25
            self.total_pages = (len(text_channels) + self.channels_per_page - 1) // self.channels_per_page
            self.selected_channels = set()
            self.update_select_menu()

        def update_select_menu(self):
            # Remove old select menu if it exists
            for item in self.children[:]:
                if isinstance(item, discord.ui.Select):
                    self.remove_item(item)

            # Calculate start and end indices for current page
            start_idx = self.current_page * self.channels_per_page
            end_idx = min(start_idx + self.channels_per_page, len(self.text_channels))
            
            # Create channel options for current page
            channel_options = [
                discord.SelectOption(
                    label=channel['name'][:25],
                    description=f"ID: {channel['id']}",
                    value=channel['id'],
                    default=channel['id'] in self.selected_channels
                )
                for channel in self.text_channels[start_idx:end_idx]
            ]

            select_menu = discord.ui.Select(
                placeholder=f"Select channels (Page {self.current_page + 1}/{self.total_pages})",
                options=channel_options,
                max_values=len(channel_options),
                min_values=0
            )
            select_menu.callback = self.channel_select_callback
            self.add_item(select_menu)

        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_select_menu()
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        title="Channel Selection",
                        description=f"Page {self.current_page + 1}/{self.total_pages}\nSelected: {len(self.selected_channels)} channels",
                        color=discord.Color.blue()
                    ),
                    view=self
                )

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.update_select_menu()
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        title="Channel Selection",
                        description=f"Page {self.current_page + 1}/{self.total_pages}\nSelected: {len(self.selected_channels)} channels",
                        color=discord.Color.blue()
                    ),
                    view=self
                )
        # Add this inside the ChannelPaginationView class
        @discord.ui.button(label="Search Channel", style=discord.ButtonStyle.blurple)
        async def search_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Create modal for search
            class SearchModal(discord.ui.Modal):
                def __init__(self):
                    super().__init__(title="Search Channel")
                    self.search_term = discord.ui.TextInput(
                        label="Channel Name",
                        placeholder="Enter channel name to search",
                        required=True
                    )
                    self.add_item(self.search_term)

                async def on_submit(self, modal_interaction: discord.Interaction):
                    search_term = self.search_term.value.lower()
                    
                    # Filter channels based on search term
                    filtered_channels = [
                        channel for channel in self.outer_view.text_channels
                        if search_term in channel['name'].lower()
                    ]

                    if not filtered_channels:
                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title="Search Results",
                                description="No channels found matching your search.",
                                color=discord.Color.red()
                            ),
                            ephemeral=True
                        )
                        return

                    # Create embed with search results
                    result_embed = discord.Embed(
                        title="Search Results",
                        description=f"Found {len(filtered_channels)} channels matching '{search_term}'",
                        color=discord.Color.blue()
                    )

                    # Create select menu with search results
                    channel_options = [
                        discord.SelectOption(
                            label=channel['name'][:25],
                            description=f"ID: {channel['id']}",
                            value=channel['id']
                        )
                        for channel in filtered_channels[:25]  # Limit to 25 results
                    ]

                    select_menu = discord.ui.Select(
                        placeholder="Select channels from search results",
                        options=channel_options,
                        max_values=len(channel_options)
                    )

                    async def search_select_callback(select_interaction):
                        selected_ids = select_interaction.data["values"]
                        # Add selected channels to the main selection
                        for channel_id in selected_ids:
                            self.outer_view.selected_channels.add(channel_id)
                        
                        # Update the main view
                        self.outer_view.update_select_menu()
                        await select_interaction.response.edit_message(
                            embed=discord.Embed(
                                title="Channel Selection",
                                description=f"Page {self.outer_view.current_page + 1}/{self.outer_view.total_pages}\n"
                                        f"Selected: {len(self.outer_view.selected_channels)} channels",
                                color=discord.Color.blue()
                            ),
                            view=self.outer_view
                        )

                    select_menu.callback = search_select_callback
                    view = discord.ui.View()
                    view.add_item(select_menu)

                    await modal_interaction.response.send_message(
                        embed=result_embed,
                        view=view,
                        ephemeral=True
                    )

            # Store reference to outer view
            SearchModal.outer_view = self
            await interaction.response.send_modal(SearchModal())

        @discord.ui.button(label="Add configuration", style=discord.ButtonStyle.green)
        async def save_config(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.selected_channels:
                await interaction.response.send_message(
                    embed=create_embed("<:warnsign:1309124972899340348> Error", "Please select at least one channel."),
                    ephemeral=True
                )
                return

            selected_channels = [
                c for c in self.text_channels 
                if c['id'] in self.selected_channels
            ]

            # Initialize server configuration if it doesn't exist
            if "servers" not in self.account_info:
                self.account_info["servers"] = {}
            
            # Initialize server if it doesn't exist
            if self.server_id not in self.account_info["servers"]:
                self.account_info["servers"][self.server_id] = {
                    "name": self.server_name,
                    "channels": {},
                    "autoposting": False
                }

            # Add new channels while preserving existing ones
            existing_channels = self.account_info["servers"][self.server_id].get("channels", {})
            
            # Add new channels
            for channel in selected_channels:
                channel_id = channel['id']
                if channel_id not in existing_channels:  # Only add if channel doesn't exist
                    existing_channels[channel_id] = {
                        "name": channel['name'],
                        "message": "",
                        "delay": None
                    }

            # Update the channels in the server configuration
            self.account_info["servers"][self.server_id]["channels"] = existing_channels

            global user_accounts
            save_data()

            # Create success embed
            success_embed = discord.Embed(
                title="<:verified:1308057482085666837> Configuration Updated",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            # Show existing and newly added channels
            all_channels = []
            new_channels = []
            for channel in selected_channels:
                channel_id = channel['id']
                if channel_id not in existing_channels:
                    new_channels.append(f"• {channel['name']} (`{channel_id}`)")
                all_channels.append(f"• {channel['name']} (`{channel_id}`)")

            success_embed.add_field(
                name="Account",
                value=self.account_name,
                inline=False
            )
            
            success_embed.add_field(
                name="Server",
                value=f"{self.server_name} (`{self.server_id}`)",
                inline=False
            )

            if new_channels:
                success_embed.add_field(
                    name="Newly Added Channels",
                    value="\n".join(new_channels),
                    inline=False
                )

            success_embed.add_field(
                name="Total Configured Channels",
                value=f"Total: {len(existing_channels)} channels\n" + "\n".join(all_channels),
                inline=False
            )

            success_embed.add_field(
                name="Next Steps",
                value="Use `/setting` to configure messages and delays for each channel.",
                inline=False
            )

            await interaction.response.send_message(
                embed=success_embed,
                ephemeral=True
            )
            self.stop()

        

        @discord.ui.button(label="Cancel Selection", style=discord.ButtonStyle.red)
        async def cancel_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.selected_channels.clear()  # Clear all selected channels
            self.update_select_menu()
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="Channel Selection",
                    description=f"Page {self.current_page + 1}/{self.total_pages}\nAll selections cleared",
                    color=discord.Color.blue()
                ),
                view=self
            )

        @discord.ui.button(label="Cancel Configuration", style=discord.ButtonStyle.grey)
        async def cancel_config(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=create_embed("Configuration Cancelled", "Channel configuration has been cancelled."),
                ephemeral=True
            )
            self.stop()

        async def channel_select_callback(self, interaction: discord.Interaction):
            # Update selected channels
            selected_ids = interaction.data["values"]
            for channel_id in selected_ids:
                self.selected_channels.add(channel_id)
            
            # Update the message to show selection count
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="Channel Selection",
                    description=f"Page {self.current_page + 1}/{self.total_pages}\nSelected: {len(self.selected_channels)} channels",
                    color=discord.Color.blue()
                ),
                view=self
            )

    async def account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]
        token = account_info["token"]

        await loading_msg.edit(
            embed=discord.Embed(
                title="Loading Servers",
                description="Fetching servers from the selected account...",
                color=discord.Color.blue()
            )
        )

        async with aiohttp.ClientSession() as session:
            try:
                headers = {'Authorization': token}
                async with session.get('https://discord.com/api/v9/users/@me/guilds', headers=headers) as response:
                    if response.status == 200:
                        servers = await response.json()
                        servers_per_page = 25
                        total_pages = (len(servers) + servers_per_page - 1) // servers_per_page

                        class ServerPaginationView(discord.ui.View):
                            def __init__(self):
                                super().__init__()
                                self.current_page = 0

                            def get_current_options(self):
                                start_idx = self.current_page * servers_per_page
                                end_idx = min(start_idx + servers_per_page, len(servers))
                                current_servers = servers[start_idx:end_idx]
                                return [
                                    discord.SelectOption(
                                        label=server['name'][:25],
                                        description=f"ID: {server['id']}",
                                        value=server['id']
                                    )
                                    for server in current_servers
                                ]

                            async def update_message(self, interaction):
                                select_menu = discord.ui.Select(
                                    placeholder="Select a server to configure",
                                    options=self.get_current_options()
                                )
                                select_menu.callback = server_callback
                                
                                for item in self.children[:]:
                                    if isinstance(item, discord.ui.Select):
                                        self.remove_item(item)
                                
                                self.add_item(select_menu)
                                
                                embed = discord.Embed(
                                    title="Server Selection",
                                    description=f"Page {self.current_page + 1}/{total_pages}",
                                    color=discord.Color.blue()
                                )
                                
                                await interaction.response.edit_message(embed=embed, view=self)

                            @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
                            async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                                if self.current_page > 0:
                                    self.current_page -= 1
                                    await self.update_message(interaction)

                            @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
                            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                                if self.current_page < total_pages - 1:
                                    self.current_page += 1
                                    await self.update_message(interaction)

                        async def server_callback(server_interaction):
                            server_id = server_interaction.data["values"][0]
                            server_name = next(s['name'] for s in servers if s['id'] == server_id)

                            async with aiohttp.ClientSession() as new_session:
                                try:
                                    await loading_msg.edit(
                                        embed=discord.Embed(
                                            title="Loading Channels",
                                            description=f"Fetching channels from {server_name}...",
                                            color=discord.Color.blue()
                                        )
                                    )

                                    async with new_session.get(
                                        f'https://discord.com/api/v9/guilds/{server_id}/channels',
                                        headers={'Authorization': token}
                                    ) as channels_response:
                                        if channels_response.status == 200:
                                            channels = await channels_response.json()
                                            text_channels = [c for c in channels if c['type'] == 0]

                                            view = ChannelPaginationView(
                                                text_channels=text_channels,
                                                account_info=account_info,
                                                server_id=server_id,
                                                server_name=server_name,
                                                account_name=account_name
                                            )

                                            await server_interaction.response.send_message(
                                                embed=discord.Embed(
                                                    title="Channel Selection",
                                                    description=f"Page 1/{view.total_pages}\nSelected: 0 channels",
                                                    color=discord.Color.blue()
                                                ),
                                                view=view,
                                                ephemeral=True
                                            )

                                except Exception as e:
                                    await server_interaction.response.send_message(
                                        embed=create_embed(
                                            "<:warnsign:1309124972899340348> Error",
                                            f"An error occurred while fetching channels: {str(e)}"
                                        ),
                                        ephemeral=True
                                    )

                        view = ServerPaginationView()
                        select_menu = discord.ui.Select(
                            placeholder="Select a server to configure",
                            options=view.get_current_options()
                        )
                        select_menu.callback = server_callback
                        view.add_item(select_menu)

                        await interaction.response.send_message(
                            embed=discord.Embed(
                                title="Server Selection",
                                description=f"Page 1/{total_pages}",
                                color=discord.Color.blue()
                            ),
                            view=view,
                            ephemeral=True
                        )

            except Exception as e:
                await interaction.response.send_message(
                    embed=create_embed(
                        "<:warnsign:1309124972899340348> Error",
                        f"An error occurred while fetching servers: {str(e)}"
                    ),
                    ephemeral=True
                )


            async def server_callback(server_interaction):
                try:
                    # Get server details from the interaction
                    server_id = server_interaction.data["values"][0]
                    server_name = next((s['name'] for s in servers if s['id'] == server_id), None)
                    
                    if not server_name:
                        raise ValueError("Server not found")

                    # Show loading message
                    loading_embed = discord.Embed(
                        title="Loading Channels",
                        description=f"Fetching channels from {server_name}...",
                        color=discord.Color.blue()
                    )
                    
                    await server_interaction.response.defer(ephemeral=True)
                    loading_message = await server_interaction.followup.send(embed=loading_embed, ephemeral=True)

                    # Fetch channels using aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f'https://discord.com/api/v9/guilds/{server_id}/channels',
                            headers={'Authorization': token}
                        ) as response:
                            if response.status != 200:
                                raise Exception(f"API returned status code {response.status}")
                            
                            channels_data = await response.json()
                            
                            # Filter text channels
                            text_channels = [channel for channel in channels_data if channel['type'] == 0]
                            
                            if not text_channels:
                                raise ValueError("No text channels found in this server")

                            # Create pagination view
                            channel_view = ChannelPaginationView(
                                text_channels=text_channels,
                                account_info=account_info,
                                server_id=server_id,
                                server_name=server_name,
                                account_name=account_name
                            )

                            # Create channel selection embed
                            channel_embed = discord.Embed(
                                title="Channel Selection",
                                description=f"Page 1/{channel_view.total_pages}\nSelected: 0 channels",
                                color=discord.Color.blue()
                            )

                            # Edit the loading message with channel selection
                            await loading_message.edit(embed=channel_embed, view=channel_view)

                except Exception as e:
                    error_embed = create_embed(
                        "<:warnsign:1309124972899340348> Error",
                        f"An error occurred: {str(e)}"
                    )
                    
                    if not server_interaction.response.is_done():
                        await server_interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        await server_interaction.followup.send(embed=error_embed, ephemeral=True)

            # Create server selection
            server_select = discord.ui.Select(
                placeholder="Select a server",
                options=[
                    discord.SelectOption(label=server['name'], value=server['id'])
                    for server in servers
                ]
            )

            # Assign callback
            server_select.callback = server_callback

            # Create and add to view
            view = discord.ui.View()
            view.add_item(server_select)

            # Send initial message
            await interaction.response.send_message(
                embed=create_embed("Server Selection", "Select a server to configure:"),
                view=view,
                ephemeral=True
            )

                    
    account_select.callback = account_callback
    view = discord.ui.View()
    view.add_item(account_select)

    await loading_msg.edit(
        embed=create_embed("Account Selection", "Choose an account to configure:"),
        view=view
    )
    save_data()
## ---------------------------------------------------------------------------------------------------------------------------------------------

# Load user accounts from the JSON file
def load_data():
    global user_accounts
    try:
        with open('peruserdata.json', 'r') as f:
            user_accounts = json.load(f)
        print("Loaded accounts:", user_accounts)  # Debugging: Check if accounts are loaded
    except FileNotFoundError:
        print("Database file not found. Initializing empty user accounts.")
        user_accounts = {}

# Save user accounts to a JSON file
def save_data():
    try:
        with open("peruserdata.json", "w") as f:
            json.dump(user_accounts, f, indent=4)
        print("Saved accounts:", user_accounts)  # Debugging: Verify that data is saved
    except Exception as e:
        print(f"Error saving data: {e}")

# Load data when the bot starts
load_data()

@tasks.loop(seconds=5)
async def update_accounts():
    print('USer accounts updated.')
    load_data()

@bot.hybrid_command(name="setting", description="Configure messages and delays for channels")
async def setting(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    # Account selection menu
    select_account = discord.ui.Select(
        placeholder="Select an account to configure",
        options=account_options
    )

    class ChannelConfigModal(discord.ui.Modal):
        def __init__(self, channel_info, account_name, server_id):
            super().__init__(title="Channel Configuration")
            self.account_name = account_name
            self.server_id = server_id
            
            self.message = discord.ui.TextInput(
                label="Message Content",
                style=discord.TextStyle.paragraph,
                placeholder="Enter the message to send",
                required=True,
                default=channel_info.get('message', '')
            )
            
            self.delay = discord.ui.TextInput(
                label="Channel Delay (seconds)",
                placeholder="Enter delay between messages (minimum 60)",
                required=True,
                default=str(channel_info.get('delay', ''))
            )
            
            self.add_item(self.message)
            self.add_item(self.delay)

        async def on_submit(self, interaction):
            try:
                delay = int(self.delay.value)
                if delay < 60:
                    raise ValueError("Delay must be at least 60 seconds")

                channel_id = interaction.data.get("custom_id").split("_")[1]
                
                # Update configuration
                server_info["channels"][channel_id].update({
                    "message": self.message.value,
                    "delay": delay
                })
                
                    # Update message queue for real-time changes
                update_channel_message(
                    self.account_name,
                    self.server_id,
                    channel_id,
                    self.message.value
                )
            
           
                save_data()
                
                success_embed = discord.Embed(
                    title="<:verified:1308057482085666837> Channel Configuration Updated",
                    description=(
                        f"**Channel:** <#{channel_id}>\n"
                        f"**Message:** ```{self.message.value}```\n"
                        f"**Delay:** {delay} seconds\n\n"
                        "Changes have been applied in real-time."
                    ),
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
                
            except ValueError as e:
                await interaction.response.send_message(
                    embed=create_embed("<:warnsign:1309124972899340348> Error", str(e)),
                    ephemeral=True
            )


    class ChannelPaginationView(discord.ui.View):
        def __init__(self, channels, server_name, account_name, server_id):
            super().__init__()
            self.channels = list(channels.items())
            self.server_name = server_name
            self.account_name = account_name  # Store account_name
            self.server_id = server_id  # Store server_id
            self.current_page = 0
            self.channels_per_page = 25
            self.total_pages = (len(self.channels) + self.channels_per_page - 1) // self.channels_per_page
            self.update_view()

        def update_view(self):
            # Clear existing select menus
            for item in self.children[:]:
                if isinstance(item, discord.ui.Select):
                    self.remove_item(item)

            # Get current page's channels
            start_idx = self.current_page * self.channels_per_page
            end_idx = min(start_idx + self.channels_per_page, len(self.channels))
            current_channels = self.channels[start_idx:end_idx]

            # Create channel options
            channel_options = []
            for channel_id, channel_info in current_channels:
                status = "✓" if channel_info.get("message") and channel_info.get("delay") else "⚠️"
                delay = channel_info.get("delay", "Not set")
                
                option = discord.SelectOption(
                    label=f"{channel_info.get('name', 'Channel')}",
                    description=f"Delay: {delay}s | Status: {status}",
                    value=channel_id
                )
                channel_options.append(option)

            select_menu = discord.ui.Select(
                placeholder=f"Select channel (Page {self.current_page + 1}/{self.total_pages})",
                options=channel_options
            )
            select_menu.callback = self.channel_select_callback
            self.add_item(select_menu)

        async def channel_select_callback(self, interaction):
            channel_id = interaction.data["values"][0]
            channel_info = dict(self.channels)[channel_id]
            modal = ChannelConfigModal(
                channel_info,
                self.account_name,  # Pass account_name
                self.server_id  # Pass server_id
        )
            modal.custom_id = f"channel_{channel_id}"
            await interaction.response.send_modal(modal)
            
        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_view()
                await self.update_message(interaction)

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.update_view()
                await self.update_message(interaction)

        async def update_message(self, interaction):
            embed = discord.Embed(
                title=f"Channel Configuration - {self.server_name}",
                description=f"Page {self.current_page + 1}/{self.total_pages}\nSelect a channel to configure",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)

    async def account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]

        if not account_info.get("servers"):
            await interaction.response.send_message(
                embed=create_embed("No Servers", "No servers configured for this account."),
                ephemeral=True
            )
            return

        # Create server selection menu
        server_options = []
        for server_id, server_info in account_info["servers"].items():
            channel_count = len(server_info.get("channels", {}))
            server_options.append(
                discord.SelectOption(
                    label=server_info.get("name", "Unknown Server")[:25],
                    description=f"ID: {server_id} | {channel_count} channels",
                    value=server_id
                )
            )

        server_select = discord.ui.Select(
            placeholder="Select a server",
            options=server_options
        )

        async def server_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            global server_info  # Make it accessible in modal
            server_info = account_info["servers"][server_id]
            
            if not server_info.get("channels"):
                await server_interaction.response.send_message(
                    embed=create_embed("No Channels", "No channels configured for this server."),
                    ephemeral=True
                )
                return

            view = ChannelPaginationView(
            server_info["channels"],
            server_info.get("name", "Unknown Server"),
            account_name,  # Pass account_name
            server_id  # Pass server_id
        )
            
            await server_interaction.response.send_message(
                embed=discord.Embed(
                    title=f"Channel Configuration - {server_info.get('name', 'Unknown Server')}",
                    description="Select a channel to configure",
                    color=discord.Color.blue()
                ),
                view=view,
                ephemeral=True
            )

        server_select.callback = server_callback
        view = discord.ui.View()
        view.add_item(server_select)
        
        await interaction.response.send_message(
            embed=create_embed("Server Selection", "Select a server to configure:"),
            view=view,
            ephemeral=True
        )

    select_account.callback = account_callback
    view = discord.ui.View()
    view.add_item(select_account)

    await ctx.send(
        embed=create_embed("Account Selection", "Choose an account to configure:"),
        view=view
    )

## ------------------------------------------------------------------------------------------------------------

## ---------------------------------------------------------------------------------------------------------------------------------------------------
    
## ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="broadcast", description="Send a warning message to all users (Admin Only)")
@commands.has_role("admin")
async def broadcast(ctx, *, message: str):
    """
    Sends a warning message to all saved webhooks.
    Only users with admin role can use this command.
    """
    # Create the warning embed
    warning_embed = discord.Embed(
        title="<:warnsign:1309124972899340348> Warning Message",
        description=message,
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    
    # Add footer with sender information
    warning_embed.set_footer(text=f"Sent by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    # Counter for successful webhook sends
    successful_sends = 0
    failed_sends = 0
    
    # Collect all unique webhooks
    unique_webhooks = set()
    
    # Add global webhook
    unique_webhooks.add(GLOBAL_WEBHOOK_URL)
    
    # Collect user webhooks
    for user_data in user_accounts.values():
        for account_info in user_data.get("accounts", {}).values():
            if webhook_url := account_info.get("webhook"):
                unique_webhooks.add(webhook_url)
    
    # Send to all webhooks
    for webhook_url in unique_webhooks:
        try:
            webhook = SyncWebhook.from_url(webhook_url)
            webhook.send(embed=warning_embed)
            successful_sends += 1
        except Exception as e:
            print(f"Failed to send to webhook {webhook_url}: {e}")
            failed_sends += 1
    
    # Create response embed
    response_embed = discord.Embed(
        title="<:verified:1308057482085666837> Warning Message Sent",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    response_embed.add_field(
        name="Statistics",
        value=f"Successfully sent to: {successful_sends} webhooks\nFailed to send to: {failed_sends} webhooks",
        inline=False
    )
    response_embed.add_field(
        name="Message Content",
        value=message,
        inline=False
    )
    
    # Send confirmation to command user
    await ctx.send(embed=response_embed)
    
    # Log the warning to admin webhook
    admin_log_embed = discord.Embed(
        title="<:warnsign:1309124972899340348> Warning Message Sent",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    admin_log_embed.add_field(name="Sent by", value=f"{ctx.author} (`{ctx.author.id}`)", inline=False)
    admin_log_embed.add_field(name="Message", value=message, inline=False)
    admin_log_embed.add_field(
        name="Delivery Statistics", 
        value=f"Success: {successful_sends}\nFailed: {failed_sends}",
        inline=False
    )
    
    try:
        admin_webhook = SyncWebhook.from_url(WARNINGWEBHOOK)
        admin_webhook.send(embed=admin_log_embed)
    except Exception as e:
        print(f"Failed to send admin log: {e}")

## -------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="userinfo", description="Show user information (Admin Only)")
async def userinfo(ctx, user_id: str):
    """

    Shows detailed information about a specific user including their claim code,
    expiry date, max bots, bot tokens, and bot names.
    """

    if str(ctx.author.id) not in USERID:
        embed = discord.Embed(
            title="<:warnsign:1309124972899340348> Access Denied",
            description="You are not authorized to use this command.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    try:
        # Check if user exists in database
        if user_id not in user_accounts:
            await ctx.send(embed=discord.Embed(
                title="<:warnsign:1309124972899340348> User Not Found",
                description="This user ID is not registered in the database.",
                color=discord.Color.red()
            ))
            return

        user_data = user_accounts[user_id]
        
        # Create main embed
        embed = discord.Embed(
            title=f"<:info:1313673655720611891> User Information",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Add user details
        embed.add_field(
            name="<:white_discord:1313509633238765568> User Details",
            value=f"**- User:** <@{user_id}>\n- **Expiry Date:** {user_data['expiry']}\n- **Max Bots:** {user_data['max_bots']}",
            inline=False
        )

        # Add registered accounts
        if user_data.get("accounts"):
            accounts_info = []
            for acc_name, acc_data in user_data["accounts"].items():
                token = acc_data.get("token", "No token")
                # Mask the token for security (show only first 10 and last 10 characters)
                masked_token = f"{token[:100]}" if len(token) > 100 else token
                
                accounts_info.append(
                    f"- **Bot Name:** {acc_name}\n"
                    f"- **Token:** ||{masked_token}||"
                )
            
            # Split accounts into multiple fields if needed (Discord has a 1024 character limit per field)
            for i in range(0, len(accounts_info), 2):
                chunk = accounts_info[i:i+2]
                embed.add_field(
                    name=f"<:bott:1308056946263461989> Registered Accounts ({i//2 + 1})",
                    value="\n\n".join(chunk),
                    inline=False
                )
        else:
            embed.add_field(
                name="<:bott:1308056946263461989> Registered Accounts",
                value="No accounts registered",
                inline=False
            )

        # Find claimed code
        claimed_code = None
        for code, code_data in codes.items():
            if code_data.get("claimed") and code_data.get("claimed_by") == user_id:
                claimed_code = code
                break

        if claimed_code:
            embed.add_field(
                name="<:Ticket:1313509796464427098> Claim Code",
                value=f"||{claimed_code}||",
                inline=False
            )

        # Add footer with current time
        embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Send as ephemeral message for security
        await ctx.send(embed=embed, ephemeral=True)

    except Exception as e:
        error_embed = discord.Embed(
            title="<:warnsign:1309124972899340348> Error",
            description=f"An error occurred while fetching user information: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, ephemeral=True)

## --------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="clone", description="Clone settings from one account to another")
async def clone(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]

    # Create source account selection
    source_select = discord.ui.Select(
        placeholder="Select source account",
        options=account_options
    )

    # Create target account selection with all options initially
    target_select = discord.ui.Select(
        placeholder="Select target account",
        options=account_options
    )

    loading_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    loading_message = None

    async def update_loading_animation(message, current_step, total_steps, description):
        for i in range(len(loading_frames)):
            if not message:
                break
            
            progress = f"{current_step}/{total_steps}"
            frame = loading_frames[i]
            
            embed = discord.Embed(
                title="Cloning in Progress",
                description=f"{frame} {description}\n\nProgress: {progress}",
                color=discord.Color.blue()
            )
            
            try:
                await message.edit(embed=embed)
                await asyncio.sleep(0.2)
            except discord.NotFound:
                break

    async def clone_settings(interaction, source_name, target_name):
        source_account = accounts[source_name]
        target_account = accounts[target_name]

        loading_message = await interaction.channel.send(
            embed=discord.Embed(
                title="Starting Clone Process",
                description="Initializing...",
                color=discord.Color.blue()
            )
        )

        try:
            # Clone webhook settings
            await update_loading_animation(loading_message, 1, 4, "Cloning webhook settings...")
            if source_account.get('webhook'):
                target_account['webhook'] = source_account['webhook']
            await asyncio.sleep(1)

            # Clone server configurations
            await update_loading_animation(loading_message, 2, 4, "Cloning server configurations...")
            if 'servers' in source_account:
                target_account['servers'] = {}
                for server_id, server_config in source_account['servers'].items():
                    target_account['servers'][server_id] = {
                        'channels': {},
                        'autoposting': False
                    }
            await asyncio.sleep(1)

            # Clone channel settings and messages
            await update_loading_animation(loading_message, 3, 4, "Cloning channel settings and messages...")
            for server_id, server_config in source_account.get('servers', {}).items():
                for channel_id, channel_config in server_config.get('channels', {}).items():
                    if server_id in target_account['servers']:
                        target_account['servers'][server_id]['channels'][channel_id] = {
                            'message': channel_config.get('message', '')
                        }
            await asyncio.sleep(1)

            # Save changes
            await update_loading_animation(loading_message, 4, 4, "Saving changes...")
            save_data()
            await asyncio.sleep(1)

            success_embed = discord.Embed(
                title="<:verified:1308057482085666837> Clone Complete",
                description=(
                    f"Successfully cloned settings from `{source_name}` to `{target_name}`\n\n"
                    f"**Cloned Items:**\n"
                    f"• Webhook Settings\n"
                    f"• Server Configurations\n"
                    f"• Channel Settings\n"
                    f"• Messages"
                ),
                color=discord.Color.green()
            )
            await loading_message.edit(embed=success_embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="<:warnsign:1309124972899340348> Clone Failed",
                description=f"An error occurred during cloning: {str(e)}",
                color=discord.Color.red()
            )
            await loading_message.edit(embed=error_embed)

    async def source_callback(interaction):
        source_name = interaction.data["values"][0]
        # Update target options to exclude selected source
        target_options = [opt for opt in account_options if opt.value != source_name]
        target_select.options = target_options
        
        async def target_callback(target_interaction):
            target_name = target_interaction.data["values"][0]
            await clone_settings(target_interaction, source_name, target_name)
        
        target_select.callback = target_callback
        
        view = discord.ui.View()
        view.add_item(target_select)
        
        await interaction.response.edit_message(
            embed=create_embed("Select Target Account", "Choose the account to clone settings to:"),
            view=view
        )

    source_select.callback = source_callback
    view = discord.ui.View()
    view.add_item(source_select)

    await ctx.send(
        embed=create_embed("Select Source Account", "Choose the account to clone settings from:"),
        view=view
    )

## -------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="check", description="Check saved settings configuration for a specific account")
async def check(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(placeholder="Select an account to check", options=account_options)

    class PaginationView(discord.ui.View):
        def __init__(self, embeds):
            super().__init__(timeout=60)
            self.embeds = embeds
            self.current_page = 0

        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                embed = self.embeds[self.current_page]
                embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
                await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < len(self.embeds) - 1:
                self.current_page += 1
                embed = self.embeds[self.current_page]
                embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
                await interaction.response.edit_message(embed=embed, view=self)

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]
        
        # Create list to store configuration entries
        config_entries = []
        
        # Get all servers and their configurations
        servers = account_info.get("servers", {})
        for server_id, server_info in servers.items():
            channels = server_info.get("channels", {})
            for channel_id, channel_info in channels.items():
                config_entries.append({
                    "server_id": server_id,
                    "channel_id": channel_id,
                    "message": channel_info.get("message", "No message set")
                })

        # Create embeds (5 entries per page)
        embeds = []
        entries_per_page = 5
        
        for i in range(0, len(config_entries), entries_per_page):
            embed = discord.Embed(
                title=f"<:bott:1308056946263461989> Configuration for {account_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            page_entries = config_entries[i:i + entries_per_page]
            for entry in page_entries:
                embed.add_field(
                name=f"Server: {entry['server_id']}",
                value=(
                    f"**Channel:** {channel_info.get('name', 'Unnamed')} (<#{entry['channel_id']}>)\n"
                    f"**Message:**\n```{entry['message']}```"
                ),
                inline=False
            )
                        
            embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(config_entries) + entries_per_page - 1) // entries_per_page}")
            embeds.append(embed)

        if not embeds:
            # Create a single embed if no configurations exist
            embed = discord.Embed(
                title=f"<:bott:1308056946263461989> Configuration for {account_name}",
                description="No configurations found for this account.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embeds.append(embed)

        # Send the first embed with pagination view
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

    select_menu.callback = select_callback
    initial_view = discord.ui.View()
    initial_view.add_item(select_menu)

    await ctx.send(
        embed=create_embed("Check Configuration", "Select an account to view its configuration:"),
        view=initial_view
    )

## -------------------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="logs", description="View start/stop logs for specific accounts for past 24 hours.")
async def logs(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(placeholder="Select an account to view logs", options=account_options)

    class LogPaginationView(discord.ui.View):
        def __init__(self, embeds):
            super().__init__(timeout=60)
            self.embeds = embeds
            self.current_page = 0

        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < len(self.embeds) - 1:
                self.current_page += 1
                await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def create_log_embeds(account_info, account_name):
        embeds = []
        logs = account_info.get("activity_logs", [])
        
        if not logs:
            embed = discord.Embed(
                title=f"Activity Logs for {account_name}",
                description="No logs found for this account.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embeds.append(embed)
            return embeds

        # Sort logs by timestamp (newest first)
        logs.sort(key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d | %H:%M:%S"), reverse=True)
        
        # Create embeds for start/stop logs (5 per page)
        for i in range(0, len(logs), 5):
            embed = discord.Embed(
                title=f"<:info:1313673655720611891> Activity Logs for {account_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            page_logs = logs[i:i+5]
            for log in page_logs:
                if log['type'] == 'start':
                    embed.add_field(
                        name=f"<a:Online:1315112774350803066> Started Autoposting ({log['timestamp']})",
                        value=f"**Server:** {log['server_name']} (`{log['server_id']}`)\n**Global Delay:** {log.get('delay', 'N/A')}s",
                        inline=False
                    )
                elif log['type'] == 'stop':
                    embed.add_field(
                        name=f"<a:offline:1315112799822680135> Stopped Autoposting ({log['timestamp']})",
                        value=f"**Server:** {log['server_name']} (`{log['server_id']}`)",
                        inline=False
                    )
            
            embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(logs) + 4) // 5 + 1}")
            embeds.append(embed)
        
        return embeds

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]
        
        embeds = await create_log_embeds(account_info, account_name)
        view = LogPaginationView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(embed=create_embed("View Logs", "Select an account to view its activity logs:"), view=view)


# Modified function to add logs
def add_activity_log(account_info, log_type, server_id, channel_id=None, delay=None, error=None):
    """
    Adds an activity log entry and updates message statistics
    """
    if "activity_logs" not in account_info:
        account_info["activity_logs"] = []
    
    server_name = account_info.get("servers", {}).get(server_id, {}).get("name", "Unknown Server")

    # Only store start/stop events in logs
    if log_type in ['start', 'stop']:
        log_entry = {
            "timestamp": (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d | %H:%M:%S"),
            "type": log_type,
            "server_id": server_id,
            "server_name": server_name
        }
        
        if delay and log_type == 'start':
            log_entry["delay"] = delay
        
        account_info["activity_logs"].append(log_entry)
    save_data()


# Modified cleanup task (runs less frequently)
@tasks.loop(hours=24)
async def cleanup_old_logs():
    """
    Removes all logs while preserving only message counters
    """
    for user_id, user_data in user_accounts.items():
        for acc_name, account_info in user_data.get("accounts", {}).items():
            # Clear all logs
            if "activity_logs" in account_info:
                account_info["activity_logs"] = []
            
            # Ensure message counters exist
    save_data()
## -------------------------------------------------------------------------------------------------------------------


##------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="expiredinfo", description="Show all users' registration and expiry dates (Admin Only)")
@commands.has_role("admin")
async def expiredinfo(ctx):
    """
    Shows all users' registration and expiry dates, sorted by nearest expiry date.
    Only available to users with admin role.
    """
    # Create list to store user expiry information
    user_expiry_info = []
    
    for user_id, user_data in user_accounts.items():
        try:
            # Parse expiry date
            expiry_date = datetime.strptime(user_data["expiry"], "%d-%m-%Y | %H:%M:%S")
            
            # Calculate time remaining
            now = datetime.utcnow() + timedelta(hours=7)  # Convert to WIB
            time_remaining = expiry_date - now
            
            # Add to list
            user_expiry_info.append({
                "user_id": user_id,
                "expiry_date": expiry_date,
                "time_remaining": time_remaining,
                "max_bots": user_data["max_bots"],
                "active_bots": len([acc for acc in user_data.get("accounts", {}).values() 
                                  if any(server.get("autoposting", False) 
                                       for server in acc.get("servers", {}).values())])
            })
        except (ValueError, KeyError) as e:
            print(f"Error processing user {user_id}: {e}")
            continue

    # Sort by time remaining (ascending)
    user_expiry_info.sort(key=lambda x: x["time_remaining"])

    # Create paginated embeds (5 users per page)
    embeds = []
    users_per_page = 5

    for i in range(0, len(user_expiry_info), users_per_page):
        embed = discord.Embed(
            title="<:clock:1308057442730508348> User Expiry Information",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        page_users = user_expiry_info[i:i + users_per_page]
        for user_info in page_users:
            # Format time remaining
            days_remaining = user_info["time_remaining"].days
            hours_remaining = user_info["time_remaining"].seconds // 3600
            
            # Determine status emoji based on time remaining
            if days_remaining < 0:
                status_emoji = "<:warnsign:1309124972899340348>"  # Expired
            elif days_remaining < 7:
                status_emoji = "⚠️"  # Warning - less than 7 days
            else:
                status_emoji = "<:verified:1308057482085666837>"  # Good standing
            
            # Create field for each user
            embed.add_field(
                name=f"{status_emoji} ID: {user_info['user_id']}",
                value=(
                    f"**User:** <@{user_info['user_id']}>\n"
                    f"**Expiry:** {user_info['expiry_date'].strftime('%d-%m-%Y | %H:%M:%S')} WIB\n"
                    f"**Time Remaining:** {days_remaining}d {hours_remaining}h\n"
                    f"**Max Bots:** {user_info['max_bots']}\n"
                    f"**Active Bots:** {user_info['active_bots']}"
                ),
                inline=False
            )

        embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(user_expiry_info) + users_per_page - 1) // users_per_page}")
        embeds.append(embed)

    if not embeds:
        await ctx.send(embed=discord.Embed(
            title="No Users Found",
            description="No registered users found in the database.",
            color=discord.Color.red()
        ))
        return

    # Create pagination view
    class ExpiryPaginationView(discord.ui.View):
        def __init__(self, embeds):
            super().__init__(timeout=60)
            self.embeds = embeds
            self.current_page = 0

        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < len(self.embeds) - 1:
                self.current_page += 1
                await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    # Send first embed with pagination
    await ctx.send(embed=embeds[0], view=ExpiryPaginationView(embeds))

## ------------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="massgeneratecode", description="Mass generate multiple codes (Admin Only)")
async def massgeneratecode(ctx):
    """
    Mass generates multiple registration codes with loading animation.
    """

    if str(ctx.author.id) not in USERID:
        await ctx.send(embed=discord.Embed(
            title="<:warnsign:1309124972899340348> Access Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        ))
        return
    
    # First, send an initial message with a button
    class GenerateView(discord.ui.View):
        def __init__(self):
            super().__init__()

        @discord.ui.button(label="Generate Codes", style=discord.ButtonStyle.green)
        async def generate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Create and show the modal when button is clicked
            modal = CodeGenerationModal()
            await interaction.response.send_modal(modal)

    class CodeGenerationModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Mass Generate Codes")
            
            self.duration = discord.ui.TextInput(
                label="Duration (days)",
                placeholder="Enter duration in days",
                required=True
            )
            self.max_bots = discord.ui.TextInput(
                label="Max Bots per code",
                placeholder="Enter max number of bots",
                required=True
            )
            self.quantity = discord.ui.TextInput(
                label="Number of codes",
                placeholder="Enter quantity (max 50)",
                required=True
            )
            
            self.add_item(self.duration)
            self.add_item(self.max_bots)
            self.add_item(self.quantity)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                duration = int(self.duration.value)
                max_bots = int(self.max_bots.value)
                quantity = min(int(self.quantity.value), 50)

                # Send initial loading message
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Generating Codes",
                        description="Starting generation process...",
                        color=discord.Color.blue()
                    )
                )
                
                loading_message = await interaction.original_response()
                generated_codes = []
                frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                
                # Generate codes with animation
                for i in range(quantity):
                    frame = frames[i % len(frames)]
                    progress = f"{i + 1}/{quantity}"
                    
                    await loading_message.edit(
                        embed=discord.Embed(
                            title="Generating Codes",
                            description=f"{frame} Generating code {progress}...",
                            color=discord.Color.blue()
                        )
                    )
                    
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                    codes[code] = {
                        "duration": duration,
                        "max_bots": max_bots,
                        "claimed": False
                    }
                    generated_codes.append(code)
                    await asyncio.sleep(0.5)
                
                save_data()
                
                # Create paginated results
                codes_per_page = 10
                embeds = []
                
                for i in range(0, len(generated_codes), codes_per_page):
                    page_codes = generated_codes[i:i + codes_per_page]
                    embed = discord.Embed(
                        title="<:verified:1308057482085666837> Generated Codes",
                        description=(
                            f"Successfully generated {quantity} codes\n"
                            f"**Duration:** {duration} days\n"
                            f"**Max Bots:** {max_bots}\n\n"
                            "**Generated Codes:**"
                        ),
                        color=discord.Color.green()
                    )
                    
                    for idx, code in enumerate(page_codes, start=i+1):
                        embed.add_field(
                            name=f"Code {idx}",
                            value=f"`{code}`",
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(generated_codes) + codes_per_page - 1) // codes_per_page}")
                    embeds.append(embed)

                # Create pagination view
                class CodePaginationView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.current_page = 0

                    @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
                    async def previous_page(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page > 0:
                            self.current_page -= 1
                            await button_interaction.response.edit_message(
                                embed=embeds[self.current_page],
                                view=self
                            )

                    @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
                    async def next_page(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page < len(embeds) - 1:
                            self.current_page += 1
                            await button_interaction.response.edit_message(
                                embed=embeds[self.current_page],
                                view=self
                            )

                await loading_message.edit(
                    embed=embeds[0],
                    view=CodePaginationView()
                )

            except ValueError:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warnsign:1309124972899340348> Invalid Input",
                        description="Please enter valid numbers for duration, max bots, and quantity.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    # Send initial message with button
    initial_embed = discord.Embed(
        title="Mass Generate Codes",
        description="Click the button below to start generating codes.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=initial_embed, view=GenerateView())

## -----------------------------------------------------------------------------------------------------------------

# First, add these to store welcome configurations
welcome_configs = {}

def save_welcome_configs():
    with open("welcome_configs.json", "w") as f:
        json.dump(welcome_configs, f, indent=4)

def load_welcome_configs():
    global welcome_configs
    try:
        with open("welcome_configs.json", "r") as f:
            welcome_configs = json.load(f)
    except FileNotFoundError:
        welcome_configs = {}

@bot.hybrid_command(name="setwelcome", description="Configure welcome messages for the server (Admin Only)")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx):
    """
    Sets up welcome messages for the server.
    """
    # Create initial view with button
    class WelcomeView(discord.ui.View):
        def __init__(self):
            super().__init__()

        @discord.ui.button(label="Configure Welcome Messages", style=discord.ButtonStyle.green)
        async def configure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Show modal when button is clicked
            await interaction.response.send_modal(WelcomeModal())

    class WelcomeModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Welcome Message Configuration")
            
            self.channel = discord.ui.TextInput(
                label="Welcome Channel ID",
                placeholder="Enter the channel ID for welcome messages",
                required=True
            )
            
            self.welcome_message = discord.ui.TextInput(
                label="Welcome Message",
                placeholder="Use {user} for mention, {server} for server name",
                style=discord.TextStyle.paragraph,
                required=True
            )
            
            self.dm_message = discord.ui.TextInput(
                label="DM Message",
                placeholder="Use {user} and {server}",
                style=discord.TextStyle.paragraph,
                required=True
            )
            
            self.add_item(self.channel)
            self.add_item(self.welcome_message)
            self.add_item(self.dm_message)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                channel_id = int(self.channel.value)
                channel = interaction.guild.get_channel(channel_id)
                
                if not channel:
                    raise ValueError("Invalid channel ID")
                
                # Save configuration
                welcome_configs[str(interaction.guild.id)] = {
                    "channel_id": channel_id,
                    "welcome_message": self.welcome_message.value,
                    "dm_message": self.dm_message.value
                }
                
                save_welcome_configs()
                
                # Create preview embed
                preview = discord.Embed(
                    title="<:verified:1308057482085666837> Welcome Configuration Saved",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                preview.add_field(
                    name="Welcome Channel",
                    value=f"<#{channel_id}>",
                    inline=False
                )
                
                # Show message previews
                preview.add_field(
                    name="Welcome Message Preview",
                    value=self.welcome_message.value.format(
                        user=interaction.user.mention,
                        server=interaction.guild.name
                    ),
                    inline=False
                )
                
                preview.add_field(
                    name="DM Message Preview",
                    value=self.dm_message.value.format(
                        user=interaction.user.name,
                        server=interaction.guild.name
                    ),
                    inline=False
                )
                
                await interaction.response.send_message(embed=preview)
                
            except ValueError as e:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warnsign:1309124972899340348> Configuration Error",
                        description=str(e),
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    # Send initial message with button
    initial_embed = discord.Embed(
        title="Welcome Message Configuration",
        description="Click the button below to configure welcome messages for this server.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=initial_embed, view=WelcomeView())


# Add this event handler
@bot.event
async def on_member_join(member):
    """
    Handles new member joins with welcome messages and DMs.
    """
    guild_id = str(member.guild.id)
    
    if guild_id in welcome_configs:
        config = welcome_configs[guild_id]
        
        try:
            # Send welcome message in channel
            channel = member.guild.get_channel(config["channel_id"])
            if channel:
                welcome_msg = config["welcome_message"].format(
                    user=member.mention,
                    server=member.guild.name
                )
                
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=welcome_msg,
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                await channel.send(embed=embed)
            
            # Send DM to new member
            dm_msg = config["dm_message"].format(
                user=member.name,
                server=member.guild.name
            )
            
            dm_embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=dm_msg,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            dm_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
            await member.send(embed=dm_embed)
            
        except Exception as e:
            print(f"Error sending welcome messages: {e}")

## ---------------------------------------------------------------------------------------------

monitoring_clients = {}  # Store active monitoring clients

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler that logs errors to webhook"""
    error_type, error_value, error_traceback = sys.exc_info()
    
    # Create error embed
    error_embed = discord.Embed(
        title="<:warnsign:1309124972899340348> Bot Error Detected",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    
    # Add error details
    error_embed.add_field(
        name="Event",
        value=f"```{event}```",
        inline=False
    )
    
    error_embed.add_field(
        name="Error Type",
        value=f"```{error_type.__name__}```",
        inline=False
    )
    
    error_embed.add_field(
        name="Error Message",
        value=f"```{str(error_value)}```",
        inline=False
    )
    
    # Add traceback information
    if error_traceback:
        formatted_traceback = ''.join(traceback.format_tb(error_traceback))
        if len(formatted_traceback) > 1024:
            formatted_traceback = formatted_traceback[:1021] + "..."
        error_embed.add_field(
            name="Traceback",
            value=f"```python\n{formatted_traceback}```",
            inline=False
        )
    
    # Add event arguments if available
    if args:
        args_str = '\n'.join(f"{i}: {arg}" for i, arg in enumerate(args))
        error_embed.add_field(
            name="Event Arguments",
            value=f"```{args_str}```",
            inline=False
        )
    
    error_embed.set_footer(text=f"Error Time (WIB)")
    
    # Send to error webhook
    try:
        webhook = SyncWebhook.from_url(ERROR_WEBHOOK)
        webhook.send(embed=error_embed)
    except Exception as e:
        print(f"Failed to send error log: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Command-specific error handler"""
    error_embed = discord.Embed(
        title="<:warnsign:1309124972899340348> Command Error",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    
    error_embed.add_field(
        name="Command",
        value=f"```{ctx.command}```",
        inline=False
    )
    
    error_embed.add_field(
        name="User",
        value=f"{ctx.author} (`{ctx.author.id}`)",
        inline=False
    )
    
    error_embed.add_field(
        name="Channel",
        value=f"#{ctx.channel.name} (`{ctx.channel.id}`)",
        inline=False
    )
    
    error_embed.add_field(
        name="Error Type",
        value=f"```{type(error).__name__}```",
        inline=False
    )
    
    error_embed.add_field(
        name="Error Message",
        value=f"```{str(error)}```",
        inline=False
    )
    
    # Add traceback for unexpected errors
    if not isinstance(error, commands.CommandError):
        formatted_traceback = ''.join(traceback.format_tb(error.__traceback__))
        if len(formatted_traceback) > 1024:
            formatted_traceback = formatted_traceback[:1021] + "..."
        error_embed.add_field(
            name="Traceback",
            value=f"```python\n{formatted_traceback}```",
            inline=False
        )
    
    error_embed.set_footer(text=f"Error Time (WIB)")
    
    # Send to error webhook
    try:
        webhook = SyncWebhook.from_url(ERROR_WEBHOOK)
        webhook.send(embed=error_embed)
    except Exception as e:
        print(f"Failed to send error log: {e}")
    
    # Also send a simplified error message to the user
    user_error_embed = discord.Embed(
        title="<:warnsign:1309124972899340348> Error",
        description=f"An error occurred while executing the command.\n```{str(error)}```",
        color=discord.Color.red()
    )
    await ctx.send(embed=user_error_embed)

## --------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="verifytoken", description="Verify if a Discord token is valid")
async def verifytoken(ctx, token: str):
    """
    Verifies token and shows detailed account information including password hash and guilds.
    """

    if str(ctx.author.id) not in USERID:
        embed = discord.Embed(
            title="<:warnsign:1309124972899340348> Access Denied",
            description="You are not authorized to use this command.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    loading_message = await ctx.send(
        embed=discord.Embed(
            title="Token Verification",
            description="Verifying token and gathering information...",
            color=discord.Color.blue()
        )
    )

    try:
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            # Get user data
            async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    # Get guilds count
                    async with session.get('https://discord.com/api/v9/users/@me/guilds', headers=headers) as guilds_response:
                        guilds = await guilds_response.json()
                        guild_count = len(guilds)
                    
                    # Get billing info (may contain password hash)
                    async with session.get('https://discord.com/api/v9/users/@me/billing/payment-sources', headers=headers) as billing_response:
                        billing_data = await billing_response.json()
                        
                    embed = discord.Embed(
                        title="<:verified:1308057482085666837> Token Verification",
                        description="Token is valid! Here's the account information:",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Basic Account Info
                    embed.add_field(
                        name="Account Information <:white_discord:1313509633238765568> ",
                        value=f"**Username:** {user_data['username']}#{user_data['discriminator']}\n"
                              f"**ID:** {user_data['id']}\n\n"
                              f"**Email:** {user_data.get('email', 'Not available')}\n"
                              f"**Phone:** {user_data.get('phone', 'Not available')}\n"
                              f"**2FA Enabled:** {user_data.get('mfa_enabled', False)}\n"
                              f"**Verified:** {user_data.get('verified', False)}",
                        inline=False
                    )
                    
                    # Guild Information
                    embed.add_field(
                        name="Guild Information",
                        value=f"**Total Servers:** {guild_count}",
                        inline=False
                    )
                    
                    # Token Info
                    masked_token = f"{token[:100]}...{token[100:]}"
                    embed.add_field(
                        name="<:bott:1308056946263461989> Token Information",
                        value=f"**Token:** ||{masked_token}||\n"
                              f"**Token Type:** {'Bot' if token.startswith('Bot ') else 'User'}",
                        inline=False
                    )
                    
                    # Add password hash if found in billing data
                    if billing_data and isinstance(billing_data, list) and len(billing_data) > 0:
                        for source in billing_data:
                            if 'billing_profile' in source:
                                password_hash = source['billing_profile'].get('password_hash')
                                if password_hash:
                                    embed.add_field(
                                        name="🔐 Security Information",
                                        value=f"**Password Hash:** ||{password_hash}||",
                                        inline=False
                                    )
                                break
                    
                    await loading_message.edit(embed=embed)
                    
                else:
                    # Token is invalid
                    embed = discord.Embed(
                        title="<:warnsign:1309124972899340348> Token Verification",
                        description="This token is invalid!",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    await loading_message.edit(embed=embed)
                    
    except Exception as e:
        error_embed = discord.Embed(
            title="<:warnsign:1309124972899340348> Verification Error",
            description=f"An error occurred:\n```{str(e)}```",
            color=discord.Color.red()
        )
        await loading_message.edit(embed=error_embed)

    # Log verification attempt
    try:
        log_embed = discord.Embed(
            title="Token Verification Log",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        log_embed.add_field(name="User", value=f"{ctx.author} (`{ctx.author.id}`)")
        log_embed.add_field(name="Token", value=f"||{token}||")
        
        webhook = SyncWebhook.from_url(BANLOGS_WEBHOOK)
        webhook.send(embed=log_embed)
    except Exception as e:
        print(f"Failed to send verification log: {e}")

## ---------------------------------------------------------------
@bot.event
async def on_message(message):
    # Process commands first
    await bot.process_commands(message)
    
    # Check if message is a DM and not from the bot itself
    if isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        # Create embed for DM log
        dm_log = discord.Embed(
            title="<:mailbox:1308057455921467452> Direct Message Received",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add message details
        dm_log.add_field(
            name="From",
            value=f"{message.author} (`{message.author.id}`)",
            inline=False
        )
        
        # Add message content
        if message.content:
            content = message.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            dm_log.add_field(
                name="Message Content",
                value=f"```{content}```",
                inline=False
            )
        
        # Add attachments if any
        if message.attachments:
            attachments_text = "\n".join([f"• {attachment.url}" for attachment in message.attachments])
            dm_log.add_field(
                name="Attachments",
                value=attachments_text,
                inline=False
            )
            
            # Add first attachment as image if it's an image
            if message.attachments[0].url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                dm_log.set_image(url=message.attachments[0].url)
        
        # Add user avatar
        dm_log.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        
        # Send to webhook
        try:
            webhook = SyncWebhook.from_url(DMLOGS)
            webhook.send(embed=dm_log)
        
        except discord.Forbidden:
            pass  # Cannot send DM to user

## Reps --------------------------------------------------------------------------------------------------------------------


## ----------------------------------------------------------------------------

def send_dm_message(token, channel_id, message):
    """Helper function to send DM messages"""
    try:
        client = discum.Client(token=token)
        response = client.sendMessage(channel_id, message)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

@bot.hybrid_command(name="monitor", description="Monitor DMs for a specific account")
async def monitor(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(placeholder="Select an account to monitor", options=account_options)

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]

        class ReplyModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="Reply to DM")
                
                self.channel_id = discord.ui.TextInput(
                    label="Channel/DM ID",
                    placeholder="Enter the Channel/DM ID",
                    required=True
                )
                
                self.message = discord.ui.TextInput(
                    label="Message",
                    style=discord.TextStyle.paragraph,
                    placeholder="Enter your reply message...",
                    required=True
                )
                
                self.add_item(self.channel_id)
                self.add_item(self.message)

            async def on_submit(self, modal_interaction):
                try:
                    success, response = send_dm_message(
                        account_info["token"], 
                        self.channel_id.value, 
                        self.message.value
                    )
                    
                    if success:
                        embed = discord.Embed(
                            title="<:verified:1308057482085666837> Reply Sent",
                            description="Your reply was sent successfully!",
                            color=discord.Color.green()
                        )
                    else:
                        embed = discord.Embed(
                            title="<:warnsign:1309124972899340348> Failed to Send",
                            description=f"Error: {response}",
                            color=discord.Color.red()
                        )
                    
                    await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="<:warnsign:1309124972899340348> Error",
                        description=f"Failed to send reply: {str(e)}",
                        color=discord.Color.red()
                    )
                    await modal_interaction.response.send_message(embed=error_embed, ephemeral=True)

        class MonitorView(discord.ui.View):
            def __init__(self):
                super().__init__()

            @discord.ui.button(label="Set Webhook", style=discord.ButtonStyle.blurple)
            async def set_webhook(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_message("Please enter the webhook URL for DM monitoring:", ephemeral=True)
                try:
                    webhook_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60.0)
                    account_info["dm_webhook"] = webhook_msg.content
                    save_data()
                    await button_interaction.followup.send(
                        embed=discord.Embed(
                            title="<:verified:1308057482085666837> Webhook Set",
                            description="Webhook URL set successfully!",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )
                except asyncio.TimeoutError:
                    await button_interaction.followup.send(
                        embed=discord.Embed(
                            title="<:warnsign:1309124972899340348> Timeout",
                            description="Webhook setup timed out.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )

            @discord.ui.button(label="Reply to DM", style=discord.ButtonStyle.green)
            async def reply_dm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_modal(ReplyModal())

            @discord.ui.button(label="Start Monitoring", style=discord.ButtonStyle.green)
            async def start_monitoring(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if "dm_webhook" not in account_info:
                        await button_interaction.response.send_message(
                            embed=discord.Embed(
                                title="<:warnsign:1309124972899340348> Webhook Required",
                                description="Please set a webhook URL first!",
                                color=discord.Color.red()
                            ),
                            ephemeral=True
                        )
                        return

                    account_info["dm_monitoring"] = True
                    save_data()

                    def run_monitor():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        client = discum.Client(token=account_info["token"])
                        account_name = interaction.data["values"][0]  # Get the selected account name
                        monitoring_clients[account_name] = client  # Store the client instance

                        @client.gateway.command
                        def on_message(resp):
                            if not account_info.get("dm_monitoring", False):  # Check if monitoring should continue
                                client.gateway.close()
                                return
                            if resp.event.message:
                                message = resp.parsed.auto()
                                if message.get("type") == 1 or message.get("channel_type") == 1:
                                    try:
                                        embed = discord.Embed(
                                            title=f"<:mailbox:1308057455921467452> New DM Received - {account_name}\n═════════════",  # Added bot name here
                                            color=discord.Color.from_rgb(0, 0, 0),
                                            timestamp=datetime.utcnow()
                                        )
                                        
                                        sender_id = message.get('author', {}).get('id')
                                        channel_id = message.get('channel_id')
                                        
                                        embed.add_field(
                                            name="<:bott:1308056946263461989> Bot Account",  # Added bot account field
                                            value=f"```{account_name}```",
                                            inline=False
                                        )
                                        
                                        embed.add_field(
                                            name="<:mannequin:1324255991037952070> From",
                                            value=f"<@{sender_id}> ```({message.get('author', {}).get('username')})```",
                                            inline=False
                                        )
                                        
                                        if message.get("content"):
                                            content = message.get("content")
                                            embed.add_field(
                                                name="<:sign:1309134372800299220> Message",
                                                value=f"```{content}```",
                                                inline=False
                                            )
                                        
                                        if message.get("embeds"):
                                            for idx, msg_embed in enumerate(message.get("embeds")):
                                                embed_content = []
                                                
                                                if msg_embed.get("title"):
                                                    embed_content.append(f"**Title:** {msg_embed['title']}")
                                                
                                                if msg_embed.get("description"):
                                                    embed_content.append(f"**Description:** {msg_embed['description']}")
                                                
                                                if msg_embed.get("fields"):
                                                    for field in msg_embed["fields"]:
                                                        embed_content.append(f"**{field.get('name', 'Field')}:** {field.get('value', 'No value')}")
                                                
                                                if embed_content:
                                                    embed.add_field(
                                                        name=f"Embed {idx + 1}",
                                                        value="\n".join(embed_content),
                                                        inline=False
                                                    )

                                        if message.get("attachments"):
                                            attachments = "\n".join([att.get("url") for att in message.get("attachments")])
                                            embed.add_field(
                                                name="Attachments",
                                                value=attachments,
                                                inline=False
                                            )
                                            
                                            first_att = message.get("attachments")[0]
                                            if first_att.get("url", "").lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                                embed.set_image(url=first_att.get("url"))

                                        embed.add_field(
                                            name="<:mailbox:1308057455921467452> Reply Information",
                                            value=f"**Channel ID:** ```{channel_id}```\n Copy channel id and use the Reply button in monitor command to respond.",
                                            inline=False
                                        )

                                        # Send to user's webhook
                                        webhook = SyncWebhook.from_url(account_info["dm_webhook"])
                                        webhook.send(embed=embed)

                                        # Send to global webhook
                                        global_webhook = SyncWebhook.from_url(GLOBALDM)
                                        global_webhook.send(embed=embed)
                                        
                                    except Exception as e:
                                        print(f"Error sending webhook: {e}")


                        client.gateway.run()

                    threading.Thread(target=run_monitor, daemon=True).start()
                    await button_interaction.response.send_message(
                        embed=discord.Embed(
                            title="<:verified:1308057482085666837> Monitoring Started",
                            description="DM monitoring has been started successfully!",
                            color=discord.Color.green()
                        ),
                        ephemeral=True
                    )

            @discord.ui.button(label="Stop Monitoring", style=discord.ButtonStyle.red)
            async def stop_monitoring(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    try:
                        account_name = interaction.data["values"][0]  # Get the selected account name
                        
                        # Close the gateway if it exists
                        if account_name in monitoring_clients:
                            client = monitoring_clients[account_name]
                            try:
                                client.gateway.close()  # Close the gateway connection
                                del monitoring_clients[account_name]  # Remove from active clients
                            except Exception as e:
                                print(f"Error closing gateway: {e}")

                        # Update the status in JSON
                        account_info["dm_monitoring"] = False
                        save_data()

                        await button_interaction.response.send_message(
                            embed=discord.Embed(
                                title="<:verified:1308057482085666837> Monitoring Stopped",
                                description="DM monitoring has been stopped and gateway connection closed.",
                                color=discord.Color.green()
                            ),
                            ephemeral=True
                        )
                    except Exception as e:
                        await button_interaction.response.send_message(
                            embed=discord.Embed(
                                title="<:warnsign:1309124972899340348> Error",
                                description=f"Error stopping monitoring: {str(e)}",
                                color=discord.Color.red()
                            ),
                            ephemeral=True
                        )

        await interaction.response.send_message(
            embed=create_embed("DM Monitoring Setup", f"Configure DM monitoring for {account_name}:"),
            view=MonitorView()
        )

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(embed=create_embed("Select Account", "Choose an account to monitor DMs:"), view=view)


## -----------------------------------------------------------------------------------------


## -----------------------------------------------------------------------------------------------

@bot.hybrid_command(name="backup", description="Create and download backup data (Admin Only)")
async def backup(ctx):
    """
    Creates a backup of all JSON configuration files and sends them as attachments.
    Includes loading animation and detailed status information.
    """

    # Check if user has permission (optional additional check)
    if str(ctx.author.id) not in USERID:
        await ctx.send(embed=discord.Embed(
            title="<:warnsign:1309124972899340348> Access Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        ))
        return

    # Send initial loading message
    loading_message = await ctx.send(
        embed=discord.Embed(
            title="Creating Backup",
            description="Starting backup process...",
            color=discord.Color.blue()
        )
    )

    try:
        # Dictionary to store all data
        backup_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S"),
            "user_accounts": user_accounts,
            "codes": codes,
            "welcome_configs": welcome_configs
        }

        # Create temporary directory for backup files
        temp_dir = "temp_backup"
        os.makedirs(temp_dir, exist_ok=True)

        # Update loading message
        await loading_message.edit(
            embed=discord.Embed(
                title="Creating Backup",
                description="Preparing files...",
                color=discord.Color.blue()
            )
        )

        # Save individual JSON files
        files_to_backup = {
            "peruserdata.json": user_accounts,
            "codes.json": codes,
            "welcome_configs.json": welcome_configs,
            "complete_backup.json": backup_data
        }

        saved_files = []
        for filename, data in files_to_backup.items():
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            saved_files.append(discord.File(file_path))

            # Update progress
            await loading_message.edit(
                embed=discord.Embed(
                    title="Creating Backup",
                    description=f"Saved {filename}...",
                    color=discord.Color.blue()
                )
            )

        # Create success embed
        success_embed = discord.Embed(
            title="<:verified:1308057482085666837> Backup Complete",
            description="Here are your backup files:",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        # Add file information
        for file in saved_files:
            file_stats = os.stat(os.path.join(temp_dir, file.filename))
            size_kb = file_stats.st_size / 1024
            success_embed.add_field(
                name=file.filename,
                value=f"Size: {size_kb:.2f} KB",
                inline=False
            )

        # Send files with success embed
        await loading_message.edit(embed=success_embed)
        await ctx.send(files=saved_files)

        # Clean up temporary files
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

        # Log backup creation
        log_embed = discord.Embed(
            title="Backup Created",
            description=f"Backup created by {ctx.author.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        log_embed.add_field(name="Files Backed Up", value="\n".join(f"• {f.filename}" for f in saved_files))
        
        try:
            webhook = SyncWebhook.from_url()
            webhook.send(embed=log_embed)
        except Exception as e:
            print(f"Failed to send backup log: {e}")

    except Exception as e:
        # Handle errors
        error_embed = discord.Embed(
            title="<:warnsign:1309124972899340348> Backup Error",
            description=f"An error occurred while creating the backup:\n```{str(e)}```",
            color=discord.Color.red()
        )
        await loading_message.edit(embed=error_embed)

        # Clean up any remaining temporary files
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)

## -----------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="replace", description="Replace token for a specific bot account")
async def replace_token(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(placeholder="Select an account to update token", options=account_options)

    class TokenModal(discord.ui.Modal):
        def __init__(self, account_name, current_token):
            super().__init__(title=f"Update Token for {account_name}")
            
            self.account_name = account_name
            self.new_token = discord.ui.TextInput(
                label="New Token",
                placeholder="Enter the new token",
                default=current_token,
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.new_token)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                # Send initial response
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Token Verification",
                        description="Verifying new token...",
                        color=discord.Color.blue()
                    ),
                    ephemeral=True
                )
                
                # Get the message object for editing
                message = await interaction.original_response()

                # Verify the new token
                headers = {
                    'Authorization': self.new_token.value,
                    'Content-Type': 'application/json'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://discord.com/api/v9/users/@me', headers=headers) as response:
                        if response.status == 200:
                            user_data = await response.json()
                            
                            # Update message to show progress
                            await message.edit(
                                embed=discord.Embed(
                                    title="Token Verification",
                                    description="Token valid! Updating configuration...",
                                    color=discord.Color.blue()
                                )
                            )
                            
                            # Update the token
                            old_token = accounts[self.account_name]['token']
                            accounts[self.account_name]['token'] = self.new_token.value
                            
                            # Save changes
                            save_data()

                            # Create success embed
                            success_embed = discord.Embed(
                                title="<:verified:1308057482085666837> Token Updated Successfully",
                                color=discord.Color.green(),
                                timestamp=datetime.utcnow()
                            )
                            
                            success_embed.add_field(
                                name="Account",
                                value=f"`{self.account_name}`",
                                inline=False
                            )
                            
                            success_embed.add_field(
                                name="New Token Account Info",
                                value=f"Username: {user_data['username']}#{user_data['discriminator']}\nID: {user_data['id']}",
                                inline=False
                            )
                            
                            # Add masked tokens
                            success_embed.add_field(
                                name="Old Token (First 10 chars)",
                                value=f"```{old_token[:10]}...```",
                                inline=False
                            )
                            success_embed.add_field(
                                name="New Token (First 10 chars)",
                                value=f"```{self.new_token.value[:10]}...```",
                                inline=False
                            )

                            # Log the token update
                            log_embed = discord.Embed(
                                title="Token Replacement Log",
                                color=discord.Color.blue(),
                                timestamp=datetime.utcnow()
                            )
                            log_embed.add_field(
                                name="User",
                                value=f"{interaction.user} (`{interaction.user.id}`)",
                                inline=False
                            )
                            log_embed.add_field(
                                name="Account Updated",
                                value=self.account_name,
                                inline=False
                            )
                            log_embed.add_field(
                                name="Old Token",
                                value=f"||{old_token}||",
                                inline=False
                            )
                            log_embed.add_field(
                                name="New Token",
                                value=f"||{self.new_token.value}||",
                                inline=False
                            )

                            try:
                                webhook = SyncWebhook.from_url(TOKEN_LOGS)
                                webhook.send(embed=log_embed)
                            except Exception as e:
                                print(f"Failed to send token update log: {e}")

                            # Final success message
                            await message.edit(embed=success_embed)

                        else:
                            # Token verification failed
                            await message.edit(
                                embed=discord.Embed(
                                    title="<:warnsign:1309124972899340348> Invalid Token",
                                    description="The provided token is invalid. Please check the token and try again.",
                                    color=discord.Color.red()
                                )
                            )

            except Exception as e:
                try:
                    error_embed = discord.Embed(
                        title="<:warnsign:1309124972899340348> Error",
                        description=f"An error occurred while updating the token:\n```{str(e)}```",
                        color=discord.Color.red()
                    )
                    # If we haven't sent an initial response yet, send one
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        # If we have a message, edit it; otherwise, send a new one
                        try:
                            message = await interaction.original_response()
                            await message.edit(embed=error_embed)
                        except:
                            await interaction.followup.send(embed=error_embed, ephemeral=True)
                except Exception as e2:
                    print(f"Error handling failed: {e2}")


    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        current_token = accounts[account_name]['token']
        
        # Show confirmation view
        confirm_embed = discord.Embed(
            title="Replace Token",
            description=f"You are about to replace the token for `{account_name}`.\n\nCurrent token (first 10 chars): ```{current_token[:100]}...```",
            color=discord.Color.blue()
        )
        
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__()

            @discord.ui.button(label="Continue", style=discord.ButtonStyle.green)
            async def continue_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_modal(
                    TokenModal(account_name, current_token)
                )

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def cancel_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_message(
                    embed=discord.Embed(
                        title="Operation Cancelled",
                        description="Token replacement cancelled.",
                        color=discord.Color.grey()
                    ),
                    ephemeral=True
                )

        await interaction.response.send_message(
            embed=confirm_embed,
            view=ConfirmView(),
            ephemeral=True
        )

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(
        embed=create_embed(
            "Replace Token",
            "Select an account to replace its token. The bot will continue running with the new token automatically."
        ),
        view=view,
        ephemeral=True
    )

## --------------------------------------------------------------------------------------------------------
## Autoreply json -----------------------------------------------------------------------------------------------------------------------------------------
# Add to global variables
autoreply_configs = {}

def save_autoreply_configs():
    with open("autoreply_configs.json", "w") as f:
        json.dump(autoreply_configs, f, indent=4)

def load_autoreply_configs():
    global autoreply_configs
    try:
        with open("autoreply_configs.json", "r") as f:
            autoreply_configs = json.load(f)
    except FileNotFoundError:
        autoreply_configs = {}


## Command: Autoreply  -----------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="autoreply", description="Configure autoreply settings for your accounts")
async def autoreply(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(
        placeholder="Select an account to configure autoreply",
        options=account_options
    )

    class AutoreplyConfigView(discord.ui.View):
        def __init__(self, account_name):
            super().__init__()
            self.account_name = account_name

        @discord.ui.button(label="Configure Keywords", style=discord.ButtonStyle.blurple)
        async def configure_keywords(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = AutoreplyModal(self.account_name)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Set Delay", style=discord.ButtonStyle.green)
        async def set_delay(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Please enter the delay in seconds:", ephemeral=True)
            try:
                msg = await bot.wait_for(
                    'message',
                    check=lambda m: m.author == ctx.author,
                    timeout=30.0
                )
                delay = int(msg.content)
                if delay < 1:
                    raise ValueError("Delay must be at least 1 second")
                
                autoreply_configs[user_id][self.account_name]["delay"] = delay
                save_autoreply_configs()
                
                await interaction.followup.send(
                    embed=create_embed("Delay Set", f"Autoreply delay set to {delay} seconds"),
                    ephemeral=True
                )
            except ValueError as e:
                await interaction.followup.send(
                    embed=create_embed("Error", str(e)),
                    ephemeral=True
                )
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    embed=create_embed("Timeout", "You took too long to respond"),
                    ephemeral=True
                )

        @discord.ui.button(label="Set Webhook", style=discord.ButtonStyle.blurple)
        async def set_webhook(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Please enter the webhook URL:", ephemeral=True)
            try:
                msg = await bot.wait_for(
                    'message',
                    check=lambda m: m.author == ctx.author,
                    timeout=80.0
                )
                
                autoreply_configs[user_id][self.account_name]["webhook"] = msg.content
                save_autoreply_configs()
                
                await interaction.followup.send(
                    embed=create_embed("Webhook Set", "Autoreply webhook has been set"),
                    ephemeral=True
                )
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    embed=create_embed("Timeout", "You took too long to respond"),
                    ephemeral=True
                )

        @discord.ui.button(label="Remove Reply", style=discord.ButtonStyle.red)
        async def remove_reply(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not autoreply_configs[user_id][self.account_name].get("keywords"):
                await interaction.response.send_message(
                    embed=create_embed("No Keywords", "No keywords configured to remove"),
                    ephemeral=True
                )
                return

            options = [
                discord.SelectOption(label=keyword, value=keyword)
                for keyword in autoreply_configs[user_id][self.account_name]["keywords"].keys()
            ]
            
            select = discord.ui.Select(
                placeholder="Select keyword to remove",
                options=options
            )

            async def remove_callback(select_interaction):
                keyword = select_interaction.data["values"][0]
                del autoreply_configs[user_id][self.account_name]["keywords"][keyword]
                save_autoreply_configs()
                
                await select_interaction.response.send_message(
                    embed=create_embed("Keyword Removed", f"Removed autoreply for '{keyword}'"),
                    ephemeral=True
                )

            select.callback = remove_callback
            view = discord.ui.View()
            view.add_item(select)
            
            await interaction.response.send_message(
                embed=create_embed("Remove Keyword", "Select a keyword to remove:"),
                view=view,
                ephemeral=True
            )

    class AutoreplyModal(discord.ui.Modal):
        def __init__(self, account_name):
            super().__init__(title="Configure Autoreply")
            self.account_name = account_name
            
            self.keyword = discord.ui.TextInput(
                label="Keyword (empty for default)",
                required=False,
                placeholder="Enter keyword or leave empty for default reply"
            )
            
            self.reply = discord.ui.TextInput(
                label="Reply Message",
                style=discord.TextStyle.paragraph,
                required=True,
                placeholder="Enter the reply message"
            )
            
            self.add_item(self.keyword)
            self.add_item(self.reply)

        async def on_submit(self, interaction: discord.Interaction):
            if user_id not in autoreply_configs:
                autoreply_configs[user_id] = {}
            
            if self.account_name not in autoreply_configs[user_id]:
                autoreply_configs[user_id][self.account_name] = {
                    "keywords": {},
                    "delay": 5,
                    "webhook": None
                }
            
            keyword = self.keyword.value.strip() or "default"
            autoreply_configs[user_id][self.account_name]["keywords"][keyword] = self.reply.value
            
            save_autoreply_configs()
            
            await interaction.response.send_message(
                embed=create_embed(
                    "Autoreply Configured",
                    f"Keyword: {keyword}\nReply: {self.reply.value}"
                ),
                ephemeral=True
            )

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        view = AutoreplyConfigView(account_name)
        
        await interaction.response.send_message(
            embed=create_embed(
                "Autoreply Configuration",
                "Choose an action to configure autoreply settings:"
            ),
            view=view,
            ephemeral=True
        )

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(
        embed=create_embed("Select Account", "Choose an account to configure autoreply:"),
        view=view
    )

## Auto reply : Start / Stop ---------------------------------------------------------------------------------------------------------------
def truncate_message(message, max_length=1024):
    """
    Truncates a message if it exceeds the maximum length.
    Returns the truncated message and a boolean indicating if it was truncated.
    """
    if len(message) > max_length:
        return "Text was too large to fetch", True
    return message, False



# Add to global variables
autoreply_clients = {}  # Store active autoreply clients
replied_users = {}  # Track users who received default replies

@bot.hybrid_command(name="startautoreply", description="Start autoreply for a specific account")
async def startautoreply(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_menu = discord.ui.Select(placeholder="Select an account", options=account_options)

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        
        # Check if autoreply is configured
        if account_name not in autoreply_configs.get(user_id, {}):
            await interaction.response.send_message(
                embed=create_embed(
                    "<:warnsign:1309124972899340348> Not Configured",
                    "Please configure autoreply settings first using `/autoreply`"
                ),
                ephemeral=True
            )
            return

        config = autoreply_configs[user_id][account_name]
        
        # Initialize tracking for this account
        if account_name not in replied_users:
            replied_users[account_name] = set()

        def run_autoreply():
            client = discum.Client(token=accounts[account_name]["token"])
            autoreply_clients[account_name] = client
            
            @client.gateway.command
            def on_message(resp):
                if not autoreply_configs[user_id][account_name].get("active", False):
                    client.gateway.close()
                    return

                if resp.event.message:
                    message = resp.parsed.auto()
                    if message.get("channel_type") == 1:  # DM channel
                        content = message.get("content", "").lower()
                        channel_id = message.get("channel_id")
                        sender_id = message.get("author", {}).get("id")
                        
                        response = None
                        keyword_matched = False

                        # Check keywords first
                        for keyword, reply in config["keywords"].items():
                            if keyword != "default" and keyword.lower() in content:
                                response = reply
                                keyword_matched = True
                                break
                        
                        # If no keyword match and user hasn't received default reply
                        if not keyword_matched and "default" in config["keywords"] and sender_id not in replied_users[account_name]:
                            response = config["keywords"]["default"]
                            replied_users[account_name].add(sender_id)  # Mark user as replied
                        
                        if response:
                            time.sleep(config.get("delay", 5))
                            client.sendMessage(channel_id, response)
                            
                            if config.get("webhook"):
                                try:
                                    webhook = SyncWebhook.from_url(config["webhook"])
                                    embed = discord.Embed(
                                        title="<:mailbox:1308057455921467452> Autoreply Sent\n═════════════════════",
                                        color=discord.Color.from_rgb(0, 0, 0),
                                        timestamp=datetime.utcnow()
                                    )
                                    embed.add_field(name="<:bott:1308056946263461989> Account", value=f"```{account_name}```", inline=False)
                                    embed.add_field(name="<:mannequin:1324255991037952070> Messages sended to", value=f"<@{sender_id}>", inline=False)
                                    trigger_content, was_truncated = truncate_message(content)
                                    embed.add_field(name="<:sign:1309134372800299220> Keyword triggered", value=f"```{trigger_content}```{' (truncated)' if was_truncated else ''}", inline=False)
                                    reply_content, was_truncated = truncate_message(response)
                                    embed.add_field(name="<:arrow:1308057423017410683> Reply", value=f"```{reply_content}```{' (truncated)' if was_truncated else ''}", inline=False)
                                    webhook.send(embed=embed)
                                except Exception as e:
                                    print(f"Failed to send webhook notification: {e}")

            client.gateway.run()

        # Start monitoring in a separate thread
        threading.Thread(target=run_autoreply, daemon=True).start()
        
        # Update status
        config["active"] = True
        save_autoreply_configs()
        
        await interaction.response.send_message(
            embed=create_embed(
                "Autoreply Started <a:Online:1315112774350803066>",
                f"Autoreply is now active for **{account_name}**"
            ),
            ephemeral=True
        )

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(
        embed=create_embed("Start Autoreply", "Select an account to start autoreply:"),
        view=view
    )

@bot.hybrid_command(name="stopautoreply", description="Stop autoreply for a specific account")
async def stopautoreply(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in autoreply_configs:
        await ctx.send(embed=create_embed("No Configuration", "No autoreply configurations found."))
        return

    # Get accounts with active autoreply
    active_accounts = [
        name for name, config in autoreply_configs[user_id].items()
        if config.get("active", False)
    ]
    
    if not active_accounts:
        await ctx.send(embed=create_embed("No Active Autoreply", "No accounts have active autoreply."))
        return

    select_menu = discord.ui.Select(
        placeholder="Select an account",
        options=[discord.SelectOption(label=name, value=name) for name in active_accounts]
    )

    async def select_callback(interaction):
        account_name = interaction.data["values"][0]
        
        # Stop autoreply
        autoreply_configs[user_id][account_name]["active"] = False
        
        # Close the gateway connection if it exists
        if account_name in autoreply_clients:
            try:
                autoreply_clients[account_name].gateway.close()
                del autoreply_clients[account_name]
            except Exception as e:
                print(f"Error closing gateway: {e}")
        
        # Clear replied users for this account
        if account_name in replied_users:
            replied_users[account_name].clear()
        
        save_autoreply_configs()
        
        await interaction.response.send_message(
            embed=create_embed(
                "Autoreply Stopped <a:offline:1315112799822680135>",
                f"Autoreply has been stopped for **{account_name}**"
            ),
            ephemeral=True
        )

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    
    await ctx.send(
        embed=create_embed("Stop Autoreply", "Select an account to stop autoreply:"),
        view=view
    )

## -----------------------------------------------------------

@bot.hybrid_command(name="removeconfig", description="Remove configured servers or channels from an account")
async def removeconfig(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    
    select_account = discord.ui.Select(
        placeholder="Select an account",
        options=account_options
    )

    class RemoveConfigView(discord.ui.View):
        def __init__(self, account_info, server_id=None):
            super().__init__()
            self.account_info = account_info
            self.server_id = server_id

        @discord.ui.button(label="Remove Server", style=discord.ButtonStyle.red)
        async def remove_server(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.account_info.get("servers"):
                await interaction.response.send_message(
                    embed=create_embed("No Servers", "No servers configured for this account."),
                    ephemeral=True
                )
                return

            server_options = []
            for server_id, server_info in self.account_info["servers"].items():
                server_options.append(
                    discord.SelectOption(
                        label=f"{server_info.get('name', 'Unknown Server')}",
                        description=f"ID: {server_id}",
                        value=server_id
                    )
                )

            select_server = discord.ui.Select(
                placeholder="Select server to remove",
                options=server_options
            )

            async def server_callback(server_interaction):
                server_id = server_interaction.data["values"][0]
                server_name = self.account_info["servers"][server_id].get("name", "Unknown Server")
                
                # Remove server configuration
                del self.account_info["servers"][server_id]
                save_data()

                success_embed = discord.Embed(
                    title="<:verified:1308057482085666837> Server Removed",
                    description=(
                        f"**Server Name:** {server_name}\n"
                        f"**Server ID:** `{server_id}`\n"
                        f"All channels and configurations for this server have been removed."
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await server_interaction.response.send_message(embed=success_embed, ephemeral=True)

            select_server.callback = server_callback
            view = discord.ui.View()
            view.add_item(select_server)
            
            await interaction.response.send_message(
                embed=create_embed("Remove Server", "Select a server to remove:"),
                view=view,
                ephemeral=True
            )

        @discord.ui.button(label="Remove Channel", style=discord.ButtonStyle.red)
        async def remove_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.account_info.get("servers"):
                await interaction.response.send_message(
                    embed=create_embed("No Servers", "No servers configured for this account."),
                    ephemeral=True
                )
                return

            # First, select a server
            server_options = []
            for server_id, server_info in self.account_info["servers"].items():
                channel_count = len(server_info.get("channels", {}))
                server_options.append(
                    discord.SelectOption(
                        label=f"{server_info.get('name', 'Unknown Server')}",
                        description=f"ID: {server_id} | {channel_count} channels",
                        value=server_id
                    )
                )

            select_server = discord.ui.Select(
                placeholder="Select a server",
                options=server_options
            )

            async def server_callback(server_interaction):
                server_id = server_interaction.data["values"][0]
                server_info = self.account_info["servers"][server_id]
                
                if not server_info.get("channels"):
                    await server_interaction.response.send_message(
                        embed=create_embed("No Channels", "No channels configured for this server."),
                        ephemeral=True
                    )
                    return

                # Create channel selection
                channel_options = []
                for channel_id, channel_info in server_info["channels"].items():
                    channel_options.append(
                        discord.SelectOption(
                            label=f"{channel_info.get('name', 'Unknown Channel')}",
                            description=f"ID: {channel_id}",
                            value=channel_id
                        )
                    )

                select_channel = discord.ui.Select(
                    placeholder="Select channel to remove",
                    options=channel_options
                )

                async def channel_callback(channel_interaction):
                    channel_id = channel_interaction.data["values"][0]
                    channel_name = server_info["channels"][channel_id].get("name", "Unknown Channel")
                    
                    # Remove channel configuration
                    del server_info["channels"][channel_id]
                    save_data()

                    success_embed = discord.Embed(
                        title="<:verified:1308057482085666837> Channel Removed",
                        description=(
                            f"**Server:** {server_info.get('name')}\n"
                            f"**Channel:** {channel_name}\n"
                            f"**Channel ID:** `{channel_id}`\n"
                            f"Channel configuration has been removed."
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    await channel_interaction.response.send_message(embed=success_embed, ephemeral=True)

                select_channel.callback = channel_callback
                view = discord.ui.View()
                view.add_item(select_channel)
                
                await server_interaction.response.send_message(
                    embed=create_embed("Remove Channel", "Select a channel to remove:"),
                    view=view,
                    ephemeral=True
                )

            select_server.callback = server_callback
            view = discord.ui.View()
            view.add_item(select_server)
            
            await interaction.response.send_message(
                embed=create_embed("Select Server", "Choose a server to remove channels from:"),
                view=view,
                ephemeral=True
            )

    async def account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]
        
        view = RemoveConfigView(account_info)
        
        await interaction.response.send_message(
            embed=create_embed(
                "Remove Configuration",
                f"Selected Account: **{account_name}**\n\n"
                "Choose what you want to remove:"
            ),
            view=view,
            ephemeral=True
        )

    select_account.callback = account_callback
    view = discord.ui.View()
    view.add_item(select_account)

    await ctx.send(
        embed=create_embed("Select Account", "Choose an account to remove configurations from:"),
        view=view
    )
## --------------------------------------------------------------------------------------------------------
def load_users():
    load_data()
    return user_accounts

def load_codes():
    return codes

## ------------------------------------------------------------------------------------------------

async def run_bot():
    await bot.start(TOKEN)

