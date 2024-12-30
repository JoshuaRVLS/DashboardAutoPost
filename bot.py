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
from passlib.hash import pbkdf2_sha256

## ----------------------------------------------------------------------------------------------------------------




TOKEN ="MTI5OTY2NzIyNDI4MTQ4MTIyNg.G5Cy0b.ltwEi0xGcRPNDaBAdkq5wGvfCusqWm1qhwvJZA"
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
                        value="1. Use `/addserver` to add servers\n2. Use `/setting` to configure channels\n3. Use `/webhooks` to set notifications",
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

@bot.hybrid_command(name="status", description="Show detailed status of running bots")
async def status(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("<a:no:1315115615320670293> No Accounts Found", "You have no registered accounts."))
        return

    # Create loading message
    loading_msg = await ctx.send(
        embed=discord.Embed(
            title="<:info:1313673655720611891> Fetching Status",
            description="Gathering information about your accounts...",
            color=discord.Color.blue()
        )
    )

    async def update_status():
        try:
            accounts = user_accounts[user_id]["accounts"]
            embeds = []
            current_embed = discord.Embed(
                title="<:info:1313673655720611891> Bot Status Overview",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Add global statistics
            total_messages = sum(acc.get("messages_sent", 0) for acc in accounts.values())
            total_servers = sum(len(acc.get("servers", {})) for acc in accounts.values())
            active_servers = sum(
                sum(1 for server in acc.get("servers", {}).values() if server.get("autoposting", False))
                for acc in accounts.values()
            )

            # Add account-specific information
            for acc_name, account_info in accounts.items():
                # Calculate account statistics
                running_servers = []
                total_channels = 0
                
                # Gather running servers and their details
                for server_id, server_info in account_info.get("servers", {}).items():
                    if server_info.get("autoposting", False):
                        server_name = server_info.get("name", "Unknown Server")
                        channel_count = len(server_info.get("channels", {}))
                        running_servers.append((server_id, server_name, channel_count))
                    total_channels += len(server_info.get("channels", {}))

                # Calculate uptime if available
                uptime_str = "Not running"
                if account_info.get("start_time"):
                    uptime = int(time.time() - account_info["start_time"])
                    days = uptime // 86400
                    hours = (uptime % 86400) // 3600
                    minutes = (uptime % 3600) // 60
                    uptime_str = f"{days}d {hours}h {minutes}m"

                # Create status indicator
                status = "<a:Online:1315112774350803066> Running" if running_servers else "<a:offline:1315112799822680135> Stopped"
                
                # Create base field value
                field_value = (
                    f"**Status:** {status}\n"
                    f"**Uptime:** {uptime_str}\n"
                    f"**Total Channels:** {total_channels}\n"
                    f"**DM Monitoring:** {'<a:yes:1315115538355064893>' if account_info.get('dm_monitoring', False) else '<a:no:1315115615320670293>'}\n"
                    f"**Webhook Set:** {'<a:yes:1315115538355064893>' if account_info.get('webhook') else '<a:no:1315115615320670293>'}\n\n"
                )

                # Add running servers information
                if running_servers:
                    field_value += "**Running Servers:**\n"
                    for server_id, server_name, channel_count in running_servers:
                        field_value += f"• {server_name} (`{server_id}`)\n"
                        field_value += f"  └ Channels: {channel_count}\n======================"
                else:
                    field_value += "**Running Servers:** None\n======================"

                # If field would make embed too long, create new embed
                if len(current_embed.fields) >= 5:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(
                        title="<:info:1313673655720611891> Bot Status Overview",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )

                current_embed.add_field(
                    name=f"======================\n<:bott:1308056946263461989> {acc_name}",
                    value=field_value,
                    inline=False
                )

            # Add the last embed
            embeds.append(current_embed)

            # Update footer with page information and auto-update notice
            for i, embed in enumerate(embeds):
                embed.set_footer(text=f"Page {i+1}/{len(embeds)} | Last updated at {datetime.utcnow().strftime('%Y-%m-%d | %H:%M:%S')} UTC")

            return embeds

        except Exception as e:
            error_embed = discord.Embed(
                title="<:warnsign:1309124972899340348> Error",
                description=f"An error occurred while fetching status:\n```{str(e)}```",
                color=discord.Color.red()
            )
            return [error_embed]

    class StatusView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.current_page = 0
            self.update_task = None

        @discord.ui.button(emoji="<:arrow1:1315137117575446609>", style=discord.ButtonStyle.blurple)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                embeds = await update_status()
                await interaction.response.edit_message(embed=embeds[self.current_page], view=self)

        @discord.ui.button(emoji="<:arrow:1308057423017410683>", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            embeds = await update_status()
            if self.current_page < len(embeds) - 1:
                self.current_page += 1
                await interaction.response.edit_message(embed=embeds[self.current_page], view=self)

    view = StatusView()

    # Create auto-update task
    async def auto_update():
        while True:
            try:
                embeds = await update_status()
                await loading_msg.edit(embed=embeds[view.current_page], view=view)
            except discord.NotFound:
                # Message was deleted or not found
                break
            except Exception as e:
                print(f"Error in auto-update: {e}")
            await asyncio.sleep(5)

    # Start initial status
    embeds = await update_status()
    await loading_msg.edit(embed=embeds[0], view=view)
    
    # Start auto-update task
    bot.loop.create_task(auto_update())


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

        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
        ]
        
        server_menu = discord.ui.Select(placeholder="Select a server to stop", options=server_options)

        async def server_select_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            server_name = account_info["servers"][server_id].get("name", "Unknown Server")
            account_info["servers"][server_id]["autoposting"] = False
            add_activity_log(account_info, "stop", server_id)
            save_data()
            await force_activity_update()
            await server_interaction.response.send_message(embed=create_embed("<a:offline:1315112799822680135> Autoposting Stopped", f"Stopped autoposting for Server {server_name} ({server_id})."))

        server_menu.callback = server_select_callback
        view = discord.ui.View()
        view.add_item(server_menu)

        await interaction.response.send_message(embed=create_embed("Server Selection", "Select a server to stop autoposting:"), view=view)

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(embed=create_embed("Select Bot Account", "Choose a bot account to stop autoposting:"), view=view)
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

# Add these as global variables
message_queues = {}  # Store message queues for each channel
message_locks = {}   # Store locks for thread-safe updates

def run_autopost_task(user_id, acc_name, token, global_delay, server_id):
    """
    Runs the autoposting task with real-time updates and webhook notifications.
    """
    client = discum.Client(token=token)
    
    def send_webhook_sync(account_info, acc_name, channel_id, message, status, reason=None):
        """
        Synchronous version of webhook notification sender
        """
        webhook_urls = [GLOBAL_WEBHOOK_URL]  # Always include global webhook
        if account_info.get('webhook'):
            webhook_urls.append(account_info['webhook'])

        # Calculate uptime
        start_time = account_info.get('start_time', time.time())
        uptime_seconds = int(time.time() - start_time)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{days}d {hours}h {minutes}m"

        embed = discord.Embed(
            title="<:mega:1308057468777267280> Autopost Notification",
            color=discord.Color.green() if status == "success" else discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        server_name = account_info.get("servers", {}).get(server_id, {}).get("name", "Unknown Server")

        embed.add_field(name="<:bott:1308056946263461989> Bot Name", value=acc_name, inline=False)
        embed.add_field(name="<:clock:1308057442730508348> Uptime", value=uptime_str, inline=False)
        embed.add_field(name="<:mailbox:1308057455921467452> Messages Sent", value=account_info.get('messages_sent', 0), inline=False)
        embed.add_field(name="<:sign:1309134372800299220> Message Content", value=f"```{message}```", inline=False)
        embed.add_field(name="<:clock:1308057442730508348> Current Time (WIB)", value=(datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d | %H:%M:%S'), inline=False)

        if status == "success":
            embed.add_field(name="<:verified:1308057482085666837> Status", value="Message successfully sent.", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Server", value=f"{server_name} ({server_id})", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Channel", value=f"<#{channel_id}>", inline=False)
        else:
            embed.add_field(name="<:warnsign:1309124972899340348> Status", value="Message failed to send.", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Server", value=f"{server_name} ({server_id})", inline=False)
            embed.add_field(name="<:arrow:1308057423017410683> Reason", value=reason or "Unknown", inline=False)
            if channel_id:
                embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)

        # Send to all webhook URLs
        for webhook_url in webhook_urls:
            try:
                webhook = SyncWebhook.from_url(webhook_url)
                webhook.send(embed=embed)
            except Exception as e:
                print(f"Failed to send webhook notification to {webhook_url}: {e}")

    while True:
        # Reload data to check if autoposting is still active
        with open('peruserdata.json', 'r') as f:
            current_data = json.load(f)
            
        try:
            account_info = current_data[user_id]["accounts"][acc_name]
            server_config = account_info["servers"][server_id]
            
            if not server_config.get("autoposting", False):
                print(f"Autoposting stopped for {acc_name} in server {server_id}")
                break

            # Process each channel
            for channel_id, channel_info in server_config.get("channels", {}).items():
                try:
                    message = channel_info.get("message")
                    if not message:
                        continue

                    # Send message
                    response = client.sendMessage(channel_id, message)
                    
                    if response.status_code == 200:
                        # Update message count
                        account_info["messages_sent"] += 1
                        with open('peruserdata.json', 'w') as f:
                            json.dump(current_data, f, indent=4)
                        
                        # Send success webhook notification
                        send_webhook_sync(account_info, acc_name, channel_id, message, "success")
                    else:
                        # Send failure webhook notification
                        send_webhook_sync(account_info, acc_name, channel_id, message, "failure", 
                                       f"Status code: {response.status_code}")
                        
                except Exception as e:
                    print(f"Error sending message to channel {channel_id}: {e}")
                    # Send failure webhook notification
                    send_webhook_sync(account_info, acc_name, channel_id, message, "failure", str(e))

                time.sleep(10)  # Delay between channels

            time.sleep(global_delay)  # Global delay between cycles

        except KeyError as e:
            print(f"Configuration error: {e}")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    # Cleanup when autoposting stops
    try:
        with open('peruserdata.json', 'r') as f:
            final_data = json.load(f)
        final_data[user_id]["accounts"][acc_name]["start_time"] = None
        with open('peruserdata.json', 'w') as f:
            json.dump(final_data, f, indent=4)
    except Exception as e:
        print(f"Error cleaning up: {e}")



## --------------------------------------------------------------------------------------------------------------------------------------------------




## --------------------------------------------------------------------------------------------------------------------------------------------------

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
                        f"**<:clock:1308057442730508348> Expiry Date (WIB):** {user_info['expiry']}\n"
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
            await interaction.response.send_message('Test')
            code = self.code.value.strip()
            user_id = str(interaction.user.id)
            
            if code not in codes or codes[code]["claimed"]:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="<:warnsign:1309124972899340348> Invalid Code",
                        description="The code is invalid or already claimed.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            duration = codes[code]["duration"]
            expiry_date_utc = datetime.now() + timedelta(days=duration)
            expiry_date_wib = expiry_date_utc + timedelta(hours=7)
            
            if user_id in user_accounts:
                user_info = user_accounts[user_id]
                user_info["max_bots"] += codes[code]["max_bots"]
                current_expiry_wib = datetime.strptime(user_info["expiry"], "%d-%m-%Y | %H:%M:%S")
                user_info["expiry"] = max(current_expiry_wib, expiry_date_wib).strftime("%d-%m-%Y | %H:%M:%S")
            else:
                user_accounts[user_id] = {
                    "accounts": {},
                    "username": self.username.value,
                    "password": pbkdf2_sha256.hash(self.password.value),
                    "expiry": expiry_date_wib.strftime("%d-%m-%Y | %H:%M:%S"),
                    "max_bots": codes[code]["max_bots"],
                    "expired": False,
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
                    f"**<:clock:1308057442730508348> Expiry Date (WIB):** {user_accounts[user_id]['expiry']}\n"
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
            expiry_wib = datetime.strptime(user_info["expiry"], "%d-%m-%Y | %H:%M:%S")
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

@bot.hybrid_command(name="start", description="Start autoposting for specific bot.")
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

        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
        ]

        server_menu = discord.ui.Select(placeholder="Select a server to start", options=server_options)

        async def server_select_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            server_config = account_info["servers"][server_id]
            server_name = server_config.get("name", "Unknown Server")  # Get server name

            # Ask for global delay
            await server_interaction.response.send_message("**Please enter the global delay (in seconds):**")
            delay_msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
            try:
                global_delay = int(delay_msg.content)
                if global_delay <= 0:
                    raise ValueError("Delay must be a positive integer.")
            except ValueError:
                await ctx.send(embed=create_embed("<a:no:1315115615320670293> Invalid Input", "Please enter a valid positive integer for the delay."))
                return

            # Set start time when autoposting begins
            account_info["start_time"] = time.time()
            server_config["autoposting"] = True
            add_activity_log(account_info, "start", server_id, delay=global_delay)
            save_data()
            await force_activity_update()

            # Start the autoposting task
            threading.Thread(target=run_autopost_task, args=(user_id, account_name, account_info["token"], global_delay, server_id)).start()

            # Send a follow-up message
            await ctx.send(embed=create_embed("<a:Online:1315112774350803066> Autoposting Started", f"Started autoposting for Server {server_name} ({server_id})."))

        server_menu.callback = server_select_callback
        view = discord.ui.View()
        view.add_item(server_menu)

        await interaction.response.send_message(embed=create_embed("Server Selection", "Select a server to start autoposting:"), view=view)

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(embed=create_embed("Select Bot Account", "Choose a bot account to start autoposting:"), view=view)
    


## ----------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="helps", description="Show bot commands")
async def helps(ctx: commands.Context):
    embed = discord.Embed(
        title="",
        url="",
        description="**Bot Commands**\n"
                    "`/helps` Show all avaiable commands.\n"
                    "`/instructions` Show instructions to settings.\n"
                    "`/info` Check details register accouunt.\n"
                    "`/add` add an account for autopost.\n"
                    "`/addserver` add a server for specific account.\n"
                    "`/setting` Configure autopost setting.\n"
                    "`/start` Start autopost service.\n"
                    "`/stop` Stop autopost service.\n"
                    "`/update` Update channel messages for specific channel.\n"
                    "`/remove` Remove saved account.\n"
                    "`/webhooks` Set your own webhoooks.\n"
                    "`/status` Show running account status\n"
                    "`/check`Check every configured server, channel and messages on specific account.\n"
                    "`/logs` Check start / stop logs for past 24 hours on specific account.\n"
                    "`/clone` Cloning your configured server, channel id, messages to other account.\n"
                    "`/startall` Starting all your configured accounts.\n"
                    "`/stopall` Stopping all your configured accounts.\n"
                    "`/monitor` Monitoring dms for specific account.\n"
                    "`/replace` Replacing token for selected account.",

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

@bot.hybrid_command(name="instructions", description="How to setting (Step by step)")
async def instructions(ctx: commands.Context):
    embed = discord.Embed(
        title="How To Setting :mag_right: ",
        url="",
        description="**Please follow the instructions**\n"
                    "**1**. Claim your account. \n"
                    "**2**. `/add` Add an account for autoposting. \n"
                    "**3**. `/addserver` Adding server id to specific account. \n"
                    "**4**. `/setting` Configure server, channel, messages to specific account. \n"
                    "**5**. `/webhooks` Set your own private webhooks for selected account. \n"
                    "**6**. `/start` Start autoposting for selected account and specific server. \n"
                    "**7**. `Global delay` A delay for autoposting using seconds. \n"
                    "**8**. `/stop` Stop autoposting for selected account and specific server. \n"
                    "**9**. `/update` Update a message for selected account, specific server and selected channel id. \n"
                    "**10**. `Live update` fyi, you dont need to stop the bot before updating the messages for specific channel. \n"
                    "**11**. `/status` Check your autoposting status. \n",
        colour=3447003,
        timestamp=datetime.now()
    )

    embed.set_author(name="",
                     icon_url="")

    embed.set_image(
        url="https://cdn.discordapp.com/attachments/1223133461221478471/1317120144773742683/standard_6.gif?ex=675e2ff9&is=675cde79&hm=6555c6c182aba586efeb0f4e436aaf2d6a6e0e0d82164c428777e6220ad1b4da&"  # Replace with your banner image URL
    )

    await ctx.send(embed=embed)

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
@bot.hybrid_command(name="setting", description="Configure settings for your bot accounts.")
async def setting(ctx):
    user_id = str(ctx.author.id)

    # Ensure the user has accounts
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]

    # Dropdown to select a bot account
    options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]
    select_account_menu = discord.ui.Select(placeholder="Select a bot account", options=options)

    async def select_account_callback(interaction):
        account_name = interaction.data["values"][0]
        account_info = accounts[account_name]

        # Dropdown to select a server or add a new one
        # In the select_account_callback function
        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
    for sid, server_info in account_info.get("servers", {}).items()
]
        if not server_options:
            server_options.append(discord.SelectOption(label="Add New Server", value="add_new"))

        server_menu = discord.ui.Select(placeholder="Select or add a server", options=server_options)

        async def server_select_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            if server_id == "add_new":
                await show_add_server_modal(server_interaction, account_name, account_info)
            else:
                await configure_server(server_interaction, account_name, account_info, server_id)

        server_menu.callback = server_select_callback
        view = discord.ui.View()
        view.add_item(server_menu)

        await interaction.response.send_message(embed=create_embed("Server Selection", "Choose a server to configure or add a new one:"), view=view)

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(embed=create_embed("Select Bot Account", "Choose a bot account to configure:"), view=view)

async def configure_server(interaction, account_name, account_info, server_id):
    server_config = account_info["servers"].get(server_id, {"channels": {}})

    view = discord.ui.View()

    # Button to add a channel
    add_channel_btn = discord.ui.Button(label="Add Channel", style=discord.ButtonStyle.green)

    async def add_channel_callback(channel_interaction):
        await show_add_channel_modal(channel_interaction, server_id, server_config)

    add_channel_btn.callback = add_channel_callback
    view.add_item(add_channel_btn)

    # Button to remove a channel
    remove_channel_btn = discord.ui.Button(label="Remove Channel", style=discord.ButtonStyle.red)

    async def remove_channel_callback(channel_interaction):
        await show_remove_channel_menu(channel_interaction, server_id, server_config)

    remove_channel_btn.callback = remove_channel_callback
    view.add_item(remove_channel_btn)

    # Button to remove the server
    remove_server_btn = discord.ui.Button(label="Remove Server", style=discord.ButtonStyle.danger)

    async def remove_server_callback(server_interaction):
        await show_remove_server_menu(server_interaction, account_name, account_info)

    remove_server_btn.callback = remove_server_callback
    view.add_item(remove_server_btn)

    # Button to save configuration
    save_btn = discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple)

    async def save_callback(save_interaction):
        save_data()
        await save_interaction.response.send_message(embed=create_embed("<a:yes:1315115538355064893> Settings Saved", f"Settings for Server {server_id} have been saved."))

    save_btn.callback = save_callback
    view.add_item(save_btn)

    # Button to cancel
    cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.gray)

    async def cancel_callback(cancel_interaction):
        await cancel_interaction.response.send_message(embed=create_embed("<:warnsign:1309124972899340348> Cancelled", "No changes were made."))

    cancel_btn.callback = cancel_callback
    view.add_item(cancel_btn)

    await interaction.response.send_message(embed=create_embed("Configure Server", f"Configuring Server {server_id}."), view=view)


async def show_add_channel_modal(interaction, server_id, server_config):
    class AddChannelModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Add Channel")
            self.channel_id = discord.ui.TextInput(
                label="Channel ID",
                placeholder="Enter the channel ID",
                required=True
            )
            self.channel_name = discord.ui.TextInput(
                label="Channel Name",
                placeholder="Enter a name for this channel",
                required=True
            )
            self.message_content = discord.ui.TextInput(
                label="Message",
                placeholder="Enter the message to send",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.channel_id)
            self.add_item(self.channel_name)
            self.add_item(self.message_content)

        async def on_submit(self, modal_interaction):
            channel_id = self.channel_id.value.strip()
            channel_name = self.channel_name.value.strip()
            message_content = self.message_content.value.strip()
            
            # Store both channel ID and name in the configuration
            server_config["channels"][channel_id] = {
                "name": channel_name,
                "message": message_content
            }
            save_data()
            await modal_interaction.response.send_message(
                embed=create_embed(
                    "Channel Added",
                    f"<a:yes:1315115538355064893> Channel {channel_name} (ID: {channel_id}) has been added to Server {server_id}."
                )
            )

    await interaction.response.send_modal(AddChannelModal())


async def show_remove_channel_menu(interaction, server_id, server_config):
    """
    Displays a dropdown menu to remove a channel from the server.
    """
    channel_options = [
        discord.SelectOption(
            label=f"{channel_info.get('name', 'Unnamed')}",
            description=f"Channel ID: {cid}",
            value=cid
        )
        for cid, channel_info in server_config["channels"].items()
    ]

    if not channel_options:
        await interaction.response.send_message(
            embed=create_embed("No Channels", "There are no channels to remove."),
            ephemeral=True
        )
        return

    dropdown = discord.ui.Select(
        placeholder="Select a channel to remove",
        options=channel_options
    )

    async def dropdown_callback(channel_interaction):
        selected_channel_id = channel_interaction.data["values"][0]
        del server_config["channels"][selected_channel_id]
        save_data()
        await channel_interaction.response.send_message(embed=create_embed("Channel Removed", f"Channel {selected_channel_id} has been removed from Server {server_id}."))

    dropdown.callback = dropdown_callback
    view = discord.ui.View()
    view.add_item(dropdown)

    await interaction.response.send_message(embed=create_embed("Remove Channel", "Select a channel to remove:"), view=view)


async def show_remove_server_menu(interaction, account_name, account_info):
    """
    Displays a dropdown menu to remove a server from the account.
    """
    server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
        ]

    if not server_options:
        await interaction.response.send_message(embed=create_embed("No Servers", "There are no servers to remove."), ephemeral=True)
        return

    dropdown = discord.ui.Select(placeholder="Select a server to remove", options=server_options)

    async def dropdown_callback(server_interaction):
        selected_server_id = server_interaction.data["values"][0]
        del account_info["servers"][selected_server_id]
        save_data()
        await server_interaction.response.send_message(embed=create_embed("Server Removed", f"Server {selected_server_id} has been removed from account {account_name}."))

    dropdown.callback = dropdown_callback
    view = discord.ui.View()
    view.add_item(dropdown)

    await interaction.response.send_message(embed=create_embed("Remove Server", "Select a server to remove:"), view=view)


# Utility function to create embeds
def create_embed(title, description):
    return discord.Embed(title=title, description=description, color=discord.Color.green())

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

@bot.hybrid_command(name="update", description="Update server, channels, and messages for a specific account")
async def update(ctx):
    """
    Starts the process to update server, channels, and messages for a specific account.
    """
    # Load the accounts to ensure data is available before processing
    load_data()

    user_id = str(ctx.author.id)

    # Debug: Check the user ID and loaded accounts
    print(f"User ID: {user_id}")
    print("Loaded user_accounts:", user_accounts)

    # Check if the user has registered accounts
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]

    # Debug: Check available accounts
    print("Available accounts:", account_options)

    # Check if there are any accounts
    if not account_options:
        await ctx.send(embed=create_embed("No Accounts", "No bot accounts are available to update."))
        return

    # Dropdown to select an account
    select_account_menu = discord.ui.Select(placeholder="Select an account to update", options=account_options)

    async def select_account_callback(interaction):
        selected_account = interaction.data['values'][0]
        account_info = accounts[selected_account]

        # Debug: Log selected account and associated data
        print(f"Selected account: {selected_account}")
        print("Account info:", account_info)

        # Get the list of servers associated with the selected account
        # In the select_account_callback function
        server_options = [
            discord.SelectOption(
                label=f"{server_info.get('name', 'Unnamed Server')}",
                description=f"ID: {sid}",
                value=sid
            )
            for sid, server_info in account_info.get("servers", {}).items()
        ]

        # Check if there are any servers for the selected account
        if not server_options:
            await interaction.response.send_message(
                embed=create_embed("<:warnsign:1309124972899340348> No Servers", f"No servers are available for the account {selected_account}."),
                ephemeral=True
            )
            return

        # Dropdown to select a server
        server_menu = discord.ui.Select(placeholder="Select a server to update", options=server_options)

        async def server_select_callback(server_interaction):
            server_id = server_interaction.data["values"][0]
            server_config = account_info["servers"][server_id]

            channel_options = [
        discord.SelectOption(
            label=f"{channel_info.get('name', 'Unnamed Channel')}",
            description=f"ID: {cid}",
            value=cid
        )
        for cid, channel_info in server_config.get("channels", {}).items()
    ]


            # If no channels are saved, inform the user
            if not channel_options:
                await server_interaction.response.send_message(
                    embed=create_embed("<:warnsign:1309124972899340348> No Channels", "No channels are available for this server."),
                    ephemeral=True
                )
                return

            # Dropdown to select a channel
            channel_menu = discord.ui.Select(placeholder="Select a channel to update", options=channel_options)

            async def channel_select_callback(channel_interaction):
                channel_id = channel_interaction.data["values"][0]
                channel_info = server_config["channels"][channel_id]

                # Show the modal to update the message for the selected channel
                await show_channel_modal(channel_interaction, selected_account, server_id, channel_id, channel_info)

            channel_menu.callback = channel_select_callback
            view = discord.ui.View()
            view.add_item(channel_menu)

            await server_interaction.response.send_message(
                embed=create_embed("Channel Selection", "Select a channel to update the message:"), view=view
            )

        server_menu.callback = server_select_callback
        view = discord.ui.View()
        view.add_item(server_menu)

        await interaction.response.send_message(embed=create_embed("Server Selection", "Select a server to update:"), view=view)

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(embed=create_embed("Select Bot Account", "Choose a bot account to update settings:"), view=view)

# Modal to change the message for a specific channel
async def show_channel_modal(interaction, account_name, server_id, channel_id, channel_info):
    class ChannelModal(discord.ui.Modal):
        def __init__(self):
            modal_title = f"Update Channel {channel_id[:15]}"
            super().__init__(title=modal_title)
            
            self.message_content = discord.ui.TextInput(
                label="New Message",
                placeholder="Enter the new message content",
                default=channel_info.get('message', ''),
                style=discord.TextStyle.paragraph,
                required=True
            )
            self.add_item(self.message_content)

        async def on_submit(self, modal_interaction):
            user_id = str(modal_interaction.user.id)
            
            if user_id not in user_accounts or account_name not in user_accounts[user_id]["accounts"]:
                await modal_interaction.response.send_message(
                    embed=create_embed("Error", f"Account '{account_name}' not found."),
                    ephemeral=True
                )
                return

            # Update the message in the database
            account_info = user_accounts[user_id]["accounts"][account_name]
            if "servers" not in account_info:
                account_info["servers"] = {}
            if server_id not in account_info["servers"]:
                account_info["servers"][server_id] = {"channels": {}}
            
            new_message = str(self.message_content.value)
            account_info["servers"][server_id]["channels"][channel_id] = {
                "message": new_message
            }
            
            # Update the message queue
            update_channel_message(account_name, server_id, channel_id, new_message)
            
            save_data()
            await modal_interaction.response.send_message(
                embed=create_embed("<a:yes:1315115538355064893> Message Updated", f"Updated message for Channel {channel_id}")
            )

    await interaction.response.send_modal(ChannelModal())

## ------------------------------------------------------------------------------------------------------------
@bot.hybrid_command(name="addserver", description="Add a server to a specific bot account.")
async def addserver(ctx):
    """
    Adds a server to the selected bot account.
    Asks for the server name and ID via a modal.
    """
    # Ensure accounts are loaded before accessing them
    load_data()

    user_id = str(ctx.author.id)

    # Check if the user has registered accounts
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    accounts = user_accounts[user_id]["accounts"]
    account_options = [discord.SelectOption(label=name, value=name) for name in accounts.keys()]

    # Check if there are any accounts
    if not account_options:
        await ctx.send(embed=create_embed("No Accounts", "No bot accounts are available to update."))
        return

    # Dropdown to select an account
    select_account_menu = discord.ui.Select(placeholder="Select an account to add a server", options=account_options)

    async def select_account_callback(interaction):
        selected_account = interaction.data['values'][0]
        account_info = accounts[selected_account]

        # Ensure the 'servers' key exists in the account
        if "servers" not in account_info:
            account_info["servers"] = {}  # Initialize the servers key if it doesn't exist

        # Ask the user for the server details using a modal
        await show_add_server_modal(interaction, selected_account, account_info)

    select_account_menu.callback = select_account_callback
    view = discord.ui.View()
    view.add_item(select_account_menu)

    await ctx.send(embed=create_embed("Select Bot Account", "Choose a bot account to add a server:"), view=view)

async def show_add_server_modal(interaction, account_name, account_info):
    """
    Displays a modal asking for the server name and server ID.
    """
    class AddServerModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Add Server to Bot Account")

            # Inputs for server name and server ID
            self.server_name = discord.ui.TextInput(
                label="Server Name", 
                placeholder="Enter the server name", 
                required=True
            )
            self.server_id = discord.ui.TextInput(
                label="Server ID", 
                placeholder="Enter the server ID", 
                required=True
            )

            self.add_item(self.server_name)
            self.add_item(self.server_id)

        async def on_submit(self, modal_interaction):
            server_name = self.server_name.value.strip()
            server_id = self.server_id.value.strip()

            # Check if the server ID already exists for the account
            if server_id in account_info.get("servers", {}):
                await modal_interaction.response.send_message(
                    embed=create_embed("Error", f"Server ID {server_id} is already linked to the bot account."),
                    ephemeral=True
                )
                return

            # Add the server to the account with both name and ID
            if "servers" not in account_info:
                account_info["servers"] = {}
                
            account_info["servers"][server_id] = {
                "name": server_name,
                "channels": {},
                "autoposting": False
            }

            save_data()

            # Confirm the server was added successfully
            await modal_interaction.response.send_message(
                embed=create_embed(
                    "Server Added", 
                    f"Server '{server_name}' (ID: {server_id}) has been added to the bot account '{account_name}'."
                )
            )

    # Show the modal to the user
    await interaction.response.send_modal(AddServerModal())

# Utility function to create embeds (can be used for message formatting)
def create_embed(title, description):
    return discord.Embed(title=title, description=description, color=discord.Color.green())

## ---------------------------------------------------------------------------------------------------------------------------------------------------
    
## ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

@bot.hybrid_command(name="warning", description="Send a warning message to all users (Admin Only)")
@commands.has_role("admin")
async def warning(ctx, *, message: str):
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

@bot.hybrid_command(name="startall", description="Start all configured bot accounts")
async def startall(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    # Ask for global delay
    await ctx.send("Enter the global delay (in seconds) for all bots:")
    try:
        delay_msg = await bot.wait_for(
            "message", 
            check=lambda m: m.author == ctx.author, 
            timeout=30.0
        )
        global_delay = int(delay_msg.content)
        if global_delay <= 0:
            raise ValueError
    except (ValueError, TimeoutError):
        await ctx.send(embed=create_embed("Invalid Input", "Please enter a valid positive number for delay."))
        return

    # Create loading message
    loading_message = await ctx.send(
        embed=discord.Embed(
            title="Starting All Bots",
            description="Initializing...",
            color=discord.Color.blue()
        )
    )

    accounts = user_accounts[user_id]["accounts"]
    total_started = 0
    total_servers = sum(len(acc.get("servers", {})) for acc in accounts.values())
    failed_starts = []

    for acc_name, account_info in accounts.items():
        try:
            # Update message to show which account is being processed
            await loading_message.edit(
                embed=discord.Embed(
                    title="Starting All Bots",
                    description=f"Processing account: {acc_name}",
                    color=discord.Color.blue()
                )
            )

            for server_id, server_config in account_info.get("servers", {}).items():
                server_name = server_config.get("name", "Unknown Server")
                
                # Update message to show which server is being started
                await loading_message.edit(
                    embed=discord.Embed(
                        title="Starting All Bots",
                        description=(
                            f"**Account:** {acc_name}\n"
                            f"**Starting Server:** {server_name} ({server_id})\n"
                            f"**Progress:** {total_started}/{total_servers} servers"
                        ),
                        color=discord.Color.blue()
                    )
                )

                # Set start time and autoposting flag
                account_info["start_time"] = time.time()
                server_config["autoposting"] = True
                
                # Add to activity logs
                add_activity_log(account_info, "start", server_id, delay=global_delay)
                
                # Start autoposting task
                threading.Thread(
                    target=run_autopost_task,
                    args=(user_id, acc_name, account_info["token"], global_delay, server_id)
                ).start()
                
                total_started += 1

                # Wait 5 seconds between each server start
                await asyncio.sleep(5)

        except Exception as e:
            failed_starts.append(f"{acc_name} - {server_name}: {str(e)}")

    save_data()
    await force_activity_update()

    # Create final status embed
    final_embed = discord.Embed(
        title="<:verified:1308057482085666837> Mass Start Complete",
        color=discord.Color.green() if not failed_starts else discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    
    final_embed.add_field(
        name="Summary",
        value=(
            f"Successfully started {total_started}/{total_servers} servers\n"
            f"Global Delay: {global_delay}s\n"
            f"Total Accounts Processed: {len(accounts)}"
        ),
        inline=False
    )
    
    if failed_starts:
        final_embed.add_field(
            name="Failed Starts",
            value="\n".join(failed_starts),
            inline=False
        )

    await loading_message.edit(embed=final_embed)


@bot.hybrid_command(name="stopall", description="Stop all running bot accounts")
async def stopall(ctx):
    user_id = str(ctx.author.id)
    
    if user_id not in user_accounts or not user_accounts[user_id].get("accounts"):
        await ctx.send(embed=create_embed("No Accounts Found", "You have no registered accounts."))
        return

    loading_message = await ctx.send(
        embed=discord.Embed(
            title="Stopping All Bots",
            description="Initializing...",
            color=discord.Color.blue()
        )
    )

    accounts = user_accounts[user_id]["accounts"]
    total_stopped = 0
    failed_stops = []

    for acc_name, account_info in accounts.items():
        try:
            for server_id, server_config in account_info.get("servers", {}).items():
                if server_config.get("autoposting", False):
                    server_config["autoposting"] = False
                    add_activity_log(account_info, "stop", server_id)
                    total_stopped += 1

                    # Update loading message
                    await loading_message.edit(
                        embed=discord.Embed(
                            title="Stopping All Bots",
                            description=f"Stopped {total_stopped} configurations...",
                            color=discord.Color.blue()
                        )
                    )

        except Exception as e:
            failed_stops.append(f"{acc_name}: {str(e)}")

    save_data()
    await force_activity_update()

    # Create final status embed
    final_embed = discord.Embed(
        title="<:verified:1308057482085666837> Mass Stop Complete",
        color=discord.Color.green() if not failed_stops else discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    
    final_embed.add_field(
        name="Summary",
        value=f"Successfully stopped {total_stopped} configurations",
        inline=False
    )
    
    if failed_stops:
        final_embed.add_field(
            name="Failed Stops",
            value="\n".join(failed_stops),
            inline=False
        )

    await loading_message.edit(embed=final_embed)

# Modify the create_log_embeds function to include mass start/stop events
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
    
    # Create embeds for logs (5 per page)
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
                    value=f"**Server:** {log['server_id']}\n**Global Delay:** {log.get('delay', 'N/A')}s",
                    inline=False
                )
            elif log['type'] == 'stop':
                embed.add_field(
                    name=f"<a:offline:1315112799822680135> Stopped Autoposting ({log['timestamp']})",
                    value=f"**Server:** {log['server_id']}",
                    inline=False
                )
        
        embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(logs) + 4) // 5}")
        embeds.append(embed)
    
    return embeds

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

@bot.hybrid_command(name="setreps", description="Set the current channel for reputation notifications (Admin Only)")
@commands.has_permissions(administrator=True)
async def setreps(ctx):
    """Sets the current channel as the reputation notification channel"""
    guild_id = str(ctx.guild.id)
    
    # Use the existing welcome_configs dictionary
    if guild_id not in welcome_configs:
        welcome_configs[guild_id] = {}
    
    # Add reps_channel_id to the existing config
    welcome_configs[guild_id]["reps_channel_id"] = ctx.channel.id
    
    # Save to the existing welcome_configs.json
    save_welcome_configs()
    
    embed = discord.Embed(
        title="<:verified:1308057482085666837> Reputation Channel Set",
        description=f"This channel will now receive reputation notifications.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="reps", description="Create a reputation button for users")
@commands.has_permissions(administrator=True)
async def reps(ctx):
    """Creates a reputation button that users can click to leave feedback"""
    
    class ReputationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
        
        @discord.ui.button(label="Leave Feedback", style=discord.ButtonStyle.green, emoji="⭐")
        async def reputation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(ReputationModal())
    
    class ReputationModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="Leave Feedback")
            
            self.product = discord.ui.TextInput(
                label="What did you purchase?",
                placeholder="Enter the product/service name",
                required=True
            )
            
            self.feedback = discord.ui.TextInput(
                label="Your Feedback",
                placeholder="Share your experience...",
                style=discord.TextStyle.paragraph,
                required=True
            )
            
            self.add_item(self.product)
            self.add_item(self.feedback)
        
        async def on_submit(self, interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            
            # Check if guild has configs and reps channel
            if guild_id not in welcome_configs or "reps_channel_id" not in welcome_configs[guild_id]:
                await interaction.response.send_message(
                    "No reputation channel has been set up. Please contact an administrator.",
                    ephemeral=True
                )
                return
            
            channel = interaction.guild.get_channel(welcome_configs[guild_id]["reps_channel_id"])
            if not channel:
                await interaction.response.send_message(
                    "The reputation channel could not be found. Please contact an administrator.",
                    ephemeral=True
                )
                return
            
            # Create and send the reputation embed
            rep_embed = discord.Embed(
                title="⭐ New Reputation",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            
            rep_embed.add_field(
                name="From",
                value=f"{interaction.user.mention}",
                inline=False
            )
            
            rep_embed.add_field(
                name="Product/Service",
                value=self.product.value,
                inline=False
            )
            
            rep_embed.add_field(
                name="Feedback",
                value=self.feedback.value,
                inline=False
            )
            
            rep_embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            
            await channel.send(embed=rep_embed)
            
            # Send confirmation to user
            confirm_embed = discord.Embed(
                title="<:verified:1308057482085666837> Feedback Submitted",
                description="Thank you for your feedback! Your reputation has been recorded.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
    
    embed = discord.Embed(
        title="⭐ Reputation System",
        description="Click the button below to leave feedback about your purchase!",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed, view=ReputationView())


## -----------------------------------------------------------------------------

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
                                            title=f"<:mailbox:1308057455921467452> New DM Received - {account_name}",  # Added bot name here
                                            color=discord.Color.blue(),
                                            timestamp=datetime.utcnow()
                                        )
                                        
                                        sender_id = message.get('author', {}).get('id')
                                        channel_id = message.get('channel_id')
                                        
                                        embed.add_field(
                                            name="Bot Account",  # Added bot account field
                                            value=f"`{account_name}`",
                                            inline=False
                                        )
                                        
                                        embed.add_field(
                                            name="From",
                                            value=f"<@{sender_id}> ({message.get('author', {}).get('username')})",
                                            inline=False
                                        )
                                        
                                        if message.get("content"):
                                            embed.add_field(
                                                name="Message",
                                                value=message.get("content"),
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
                                            name="Reply Information",
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


## ------------------------------------------------------------------------------------------------




# Run the bot with your token
bot.run(TOKEN)
