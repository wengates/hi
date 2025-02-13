import discord
from discord.ext import commands
import asyncio
import json
import os

# ---------- Load & Save Data ----------
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"status_channel_id": None, "tracked_bots": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"status_channel_id": bot.status_channel_id, "tracked_bots": tracked_bots}, f, indent=4)

data = load_data()

# Intents Setup (Required for Python 3.12)
intents = discord.Intents.default()
intents.members = True  # Required for member join events
intents.presences = True
intents.message_content = True  # Allows reading command messages

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

warnings = {}  # Stores user warnings
welcome_channel_id = None  # Stores the welcome channel ID 
bot.status_channel_id = data.get("status_channel_id")
tracked_bots = data.get("tracked_bots", {})

# ---------------------- Status track Commands ----------------------

@bot.tree.command(name="bot-list", description="Show a list of currently tracked bots.")
async def show_tracked_bots(interaction: discord.Interaction):
    """Displays tracked bots."""
    if not tracked_bots:
        embed = discord.Embed(title="📜 Tracked Bots", description="No bots are currently being tracked.", color=0xffcc00)
    else:
        embed = discord.Embed(title="📜 Tracked Bots", color=0x00ffcc)
        bot_names = [
            f"🤖 {interaction.guild.get_member(int(bot_id)).name if interaction.guild.get_member(int(bot_id)) else bot_id} (tracking bots)"
            for bot_id in tracked_bots
        ]
        embed.description = "\n".join(bot_names)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setstatuschannel", description="Set the channel for bot status updates.")
async def set_status_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Sets the status update channel."""
    bot.status_channel_id = channel.id
    save_data()
    embed = discord.Embed(title="✅ Status Channel Set", description=f"Updates will be sent in {channel.mention}.", color=0x00ffcc)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="trackbot", description="Start tracking a bot's status.")
async def track_bot(interaction: discord.Interaction, bot_id: str):
    """Tracks a bot's online/offline status."""
    if not bot.status_channel_id:
        await interaction.response.send_message(embed=discord.Embed(title="⚠️ Warning", description="Set a status channel first using `/setstatuschannel`.", color=0xffcc00), ephemeral=True)
        return

    try:
        bot_id = int(bot_id)
    except ValueError:
        await interaction.response.send_message(embed=discord.Embed(title="❌ Error", description="Invalid bot ID.", color=0xff0000), ephemeral=True)
        return

    bot_member = interaction.guild.get_member(bot_id)

    if not bot_member or not bot_member.bot:
        await interaction.response.send_message(embed=discord.Embed(title="❌ Error", description="Bot not found or ID is not a bot.", color=0xff0000), ephemeral=True)
        return

    tracked_bots[str(bot_id)] = True
    save_data()
    embed = discord.Embed(title="✅ Bot Tracked", description=f"Now tracking **{bot_member.name}**.", color=0x00ffcc)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="untrackbot", description="Stop tracking a bot's status.")
async def untrack_bot(interaction: discord.Interaction, bot_id: str):
    """Untracks a bot."""
    if str(bot_id) in tracked_bots:
        del tracked_bots[str(bot_id)]
        save_data()
        embed = discord.Embed(title="✅ Bot Untracked", description=f"Bot **{bot_id}** removed from tracking.", color=0xffcc00)
    else:
        embed = discord.Embed(title="❌ Error", description="This bot is not currently tracked.", color=0xff0000)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------------- MODERATION COMMANDS ----------------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # Sync slash commands globally
    try:
        await bot.tree.sync()
        print(f"✅ Slash commands synced.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    # Remove bots that left the server
    guild = bot.guilds[0]  # Assumes bot is in one server
    for bot_id in list(tracked_bots.keys()):
        if not guild.get_member(int(bot_id)):
            del tracked_bots[bot_id]  # Remove if bot left

    save_data()
    print(f"✅ Tracking {len(tracked_bots)} bots.")

@bot.event
async def on_member_join(member):
    """Send a welcome message when a user joins."""
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"🎉 Welcome to SnareHub | Sideloading, {member.mention}!")

@bot.event
async def on_member_remove(member):
    """Send a farewell message when a user leaves the server."""
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            username = member.name if member.discriminator == "0" else f"{member.name}#{member.discriminator}"
            await channel.send(f"😢 **{username}** has left the server.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_welcome(ctx, channel: discord.TextChannel):
    """Set up the welcome channel."""
    global welcome_channel_id
    welcome_channel_id = channel.id
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban a user."""
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.mention} has been **banned**. Reason: {reason}")

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kick a user."""
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.mention} has been **kicked**. Reason: {reason}")

@bot.command()
@commands.has_permissions(administrator=True)
async def lock(ctx):
    """Lock the current channel."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 This channel has been **locked**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    """Unlock the current channel."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 This channel has been **unlocked**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def slowmode(ctx, seconds: int):
    """Set a slowmode delay."""
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐌 Slowmode set to **{seconds} seconds**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    """Change a user's nickname."""
    await member.edit(nick=nickname)
    await ctx.send(f"✅ {member.mention}'s nickname has been changed.")

@bot.command()
@commands.has_permissions(administrator=True)
async def purge(ctx, amount: int):
    """Delete a number of messages."""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Deleted {amount} messages.", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, duration: str = None):
    """Mute a user (optional duration)."""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")

    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)

    await member.add_roles(mute_role)
    await ctx.send(f"✅ {member.mention} has been **muted**.")

    if duration:
        time_multiplier = {"s": 1, "m": 60, "h": 3600}
        unit = duration[-1]
        if unit in time_multiplier and duration[:-1].isdigit():
            await asyncio.sleep(int(duration[:-1]) * time_multiplier[unit])
            await member.remove_roles(mute_role)
            await ctx.send(f"✅ {member.mention} has been **unmuted** after {duration}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a user."""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"✅ {member.mention} has been **unmuted**.")

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    """Warn a user."""
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append(reason)
    await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason}")

@bot.command()
@commands.has_permissions(administrator=True)
async def unwarn(ctx, member: discord.Member):
    """Remove the latest warning from a user."""
    if member.id in warnings and warnings[member.id]:
        removed_warning = warnings[member.id].pop()
        await ctx.send(f"✅ Removed warning from {member.mention}. Previous reason: {removed_warning}")
    else:
        await ctx.send(f"❌ {member.mention} has no warnings.")

@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    """Clear all warnings from a user."""
    warnings.pop(member.id, None)
    await ctx.send(f"✅ All warnings for {member.mention} have been cleared.")

@bot.command(name="help")
async def help_command(ctx, command_name: str = None):
    """Displays help for commands."""
    prefix_commands = {
        "setup_welcome": "Set up the welcome channel. Usage: `.setup_welcome #channel`",
        "ban": "Ban a user. Usage: `.ban @user [reason]`",
        "kick": "Kick a user. Usage: `.kick @user [reason]`",
        "lock": "Lock the current channel. Usage: `.lock`",
        "unlock": "Unlock the current channel. Usage: `.unlock`",
        "slowmode": "Set slowmode delay. Usage: `.slowmode seconds`",
        "nick": "Change a user's nickname. Usage: `.nick @user new_nickname`",
        "purge": "Delete messages. Usage: `.purge amount`",
        "mute": "Mute a user. Usage: `.mute @user [duration]`",
        "unmute": "Unmute a user. Usage: `.unmute @user`",
        "warn": "Warn a user. Usage: `.warn @user [reason]`",
        "unwarn": "Remove the latest warning. Usage: `.unwarn @user`",
        "clearwarns": "Clear all warnings. Usage: `.clearwarns @user`"
    }

    slash_commands = {
        "/bot_list": "Show tracked bots.",
        "/setstatuschannel": "Set the status update channel. Usage: `/setstatuschannel #channel`",
        "/trackbot": "Track a bot's online/offline status. Usage: `/trackbot bot_id`",
        "/untrackbot": "Stop tracking a bot. Usage: `/untrackbot bot_id`"
    }

    if command_name:
        # If user requested help for a specific command
        command_name = command_name.lower()
        if command_name in prefix_commands:
            description = prefix_commands[command_name]
            embed = discord.Embed(title=f"📌 Help: {command_name}", description=description, color=0x00ffcc)
        elif command_name in slash_commands:
            description = slash_commands[command_name]
            embed = discord.Embed(title=f"📌 Help: {command_name}", description=description, color=0x00ffcc)
        else:
            embed = discord.Embed(title="❌ Error", description="Command not found. Use `.help` to list all commands.", color=0xff0000)
    else:
        # Display all commands
        embed = discord.Embed(title="📜 Help - Available Commands", description="Use `.help [command]` for details.", color=0x00ffcc)

        embed.add_field(name="🔧 Moderation Commands", value="\n".join(f"`.{cmd}`" for cmd in prefix_commands), inline=False)
        embed.add_field(name="🤖 Bot Tracking Commands", value="\n".join(f"`{cmd}`" for cmd in slash_commands), inline=False)

    await ctx.send(embed=embed)

# ---------------------- ERROR HANDLING ----------------------

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You must be an **administrator** to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required arguments. Use `.help [command]` for details.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument type. Try mentioning the user correctly.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `.help` to see available commands.")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

# ---------- TRACK BOT STATUS CHANGES ONLY ----------

@bot.event
async def on_presence_update(before, after):
    """Tracks bot status changes."""
    if after.bot and str(after.id) in tracked_bots and before.status != after.status:
        await send_status_update(after, after.status)

async def send_status_update(bot_member, status):
    """Sends an embed when a bot goes offline/online."""
    if not bot.status_channel_id:
        return

    channel = bot.get_channel(bot.status_channel_id)
    if not channel:
        return

    color = 0xff0000 if status == discord.Status.offline else 0x00ff00
    embed = discord.Embed(title="🤖 Bot Status Update", color=color)
    embed.add_field(name="Bot Name", value=bot_member.mention, inline=True)
    embed.add_field(name="New Status", value="❌ Offline" if status == discord.Status.offline else "✅ Online", inline=True)

    await channel.send(embed=embed)

# Run the bot
bot.run("MTMzNzU5MjM5MDE5Nzg0MTk2MQ.Guo5sv._oh2dQpcU5vrV_fhEaHSnLC2MvEip6sSel7NSc")
