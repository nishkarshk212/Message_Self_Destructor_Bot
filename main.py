import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import aioschedule as schedule
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(level=logging.INFO)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Dictionary to store scheduled message deletions
scheduled_messages: Dict[int, asyncio.Task] = {}
# Dictionary to store group settings (whether message deletion is enabled)
group_settings: Dict[int, bool] = {}
# Dictionary to store default deletion times for groups
default_deletion_times: Dict[int, int] = {}  # Default is 60 seconds
# Dictionary to store custom timer values for each user/chat
custom_timers: Dict[str, int] = {}  # Key: f"{user_id}:{chat_id}", Value: seconds

# Create inline keyboard with timer options
def get_timer_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 seconds", callback_data="timer_5"),
            InlineKeyboardButton(text="10 seconds", callback_data="timer_10")
        ],
        [
            InlineKeyboardButton(text="30 seconds", callback_data="timer_30"),
            InlineKeyboardButton(text="1 minute", callback_data="timer_60")
        ],
        [
            InlineKeyboardButton(text="5 minutes", callback_data="timer_300"),
            InlineKeyboardButton(text="10 minutes", callback_data="timer_600")
        ],
        [
            InlineKeyboardButton(text="1 hour", callback_data="timer_3600")
        ],
        [
            InlineKeyboardButton(text="⏱️ Custom Time", callback_data="custom_time")
        ]
    ])
    return keyboard

# Create custom time keyboard
def get_custom_time_keyboard(current_time: int = 3600):
    hours = current_time // 3600
    remaining_seconds = current_time % 3600
    minutes = remaining_seconds // 60
    
    time_display = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="- Hour", callback_data="decrease_hour"),
            InlineKeyboardButton(text=time_display, callback_data="show_time"),
            InlineKeyboardButton(text="+ Hour", callback_data="increase_hour")
        ],
        [
            InlineKeyboardButton(text="Set Time", callback_data=f"set_custom_{current_time}"),
            InlineKeyboardButton(text="Cancel", callback_data="cancel_custom")
        ]
    ])
    return keyboard

# Create main menu keyboard
def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Mention Owner", url="https://t.me/Hacker_unity_212"),
            InlineKeyboardButton(text="Channel", url="https://t.me/Titanic_bots")
        ],
        [
            InlineKeyboardButton(text="Add to Group", url="https://t.me/Message_Self_destruction_212_bot?startgroup=true")
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="start_settings")
        ]
    ])
    return keyboard

# Create group settings keyboard with time options (with save changes button)
def get_group_settings_keyboard(chat_id: int, is_enabled: bool = None):
    # Get current status, default to True if not set
    if is_enabled is None:
        is_enabled = group_settings.get(chat_id, True)
    
    status_text = "Disable Message Deletion" if is_enabled else "Enable Message Deletion"
    status_callback = "disable_delete" if is_enabled else "enable_delete"
    
    # Get current default deletion time
    default_time = default_deletion_times.get(chat_id, 60)  # Default to 60 seconds
    hours = default_time // 3600
    remaining_seconds = default_time % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    
    time_display = ""
    if hours > 0:
        time_display += f"{hours}h "
    if minutes > 0:
        time_display += f"{minutes}m "
    if seconds > 0 or (hours == 0 and minutes == 0):
        time_display += f"{seconds}s"
    
    time_display = time_display.strip()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=status_text, callback_data=status_callback)
        ],
        [
            InlineKeyboardButton(text="1 min", callback_data="time_60"),
            InlineKeyboardButton(text="5 min", callback_data="time_300"),
            InlineKeyboardButton(text="10 min", callback_data="time_600")
        ],
        [
            InlineKeyboardButton(text="6 hour", callback_data="time_21600"),
            InlineKeyboardButton(text="12 hour", callback_data="time_43200"),
            InlineKeyboardButton(text="24 hour", callback_data="time_86400")
        ],
        [
            InlineKeyboardButton(text="- Hour", callback_data="decrease_default_time"),
            InlineKeyboardButton(text=time_display, callback_data="show_default_time"),
            InlineKeyboardButton(text="+ Hour", callback_data="increase_default_time")
        ],
        [
            InlineKeyboardButton(text="Save Changes", callback_data="save_changes")
        ]
    ])
    return keyboard

# Function to check if user has permission to change settings
async def check_permission(chat_id: int, user_id: int) -> bool:
    try:
        # Get chat member information
        chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        
        # Allow if user is creator (owner) or administrator (moderator)
        if chat_member.status in ["creator", "administrator"]:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking permissions: {e}")
        return False

# Function to schedule message deletion
async def schedule_message_deletion(chat_id: int, message_id: int, delay_seconds: int):
    async def delete_message():
        await asyncio.sleep(delay_seconds)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"Message {message_id} in chat {chat_id} deleted after {delay_seconds}s")
        except Exception as e:
            print(f"Failed to delete message {message_id}: {e}")
    
    # Cancel any existing scheduled deletion for this message
    if message_id in scheduled_messages:
        scheduled_messages[message_id].cancel()
    
    # Schedule the new deletion task
    task = asyncio.create_task(delete_message())
    scheduled_messages[message_id] = task
    return task

# Function to format time nicely
def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
        else:
            return f"{hours} hour{'s' if hours != 1 else ''}"

# Helper function to safely edit message
async def safe_edit_message(message, text, reply_markup=None, parse_mode="HTML"):
    try:
        await message.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Message hasn't changed, just return
            pass
        else:
            # Re-raise if it's a different error
            raise

# Handler for /start command
@dp.message(Command("start"))
async def send_welcome(message: Message):
    welcome_text = (
        "🌟 <b>Welcome to Message Self-Destructor Bot!</b> 🌟\n\n"
        "I can help you send self-destructing messages in groups and private chats.\n\n"
        "<b>How to use:</b>\n"
        "• Send any message and I'll offer to make it self-destruct\n"
        "• Use /help for more commands\n\n"
        "<i>𝔱𝔥𝔦𝔰 𝔟𝔬𝔱 𝔦𝔰 𝔠𝔯𝔢𝔞𝔱𝔢𝔡 𝔟𝔶 @Titanic_bots 𝔞𝔫𝔡 𝔬𝔴𝔫𝔢𝔯 :- @hacker_unity_212</i>\n\n"
        "Look for my profile picture above! 🤖" 
    )
    
    keyboard = get_main_menu_keyboard()
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=keyboard)

# Handler for /help command
@dp.message(Command("help"))
async def send_help(message: Message):
    help_text = (
        "📖 <b>Help - Message Self-Destructor Bot</b> 📖\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Change group settings (owners/moderators only)\n\n"
        "<b>Features:</b>\n"
        "• Send any message to make it self-destruct\n"
        "• Choose from various timer options\n"
        "• Use custom time with + and - buttons\n"
        "• Enable/disable message deletion in groups\n\n"
        "I'm a girl bot 🌸"
    )
    
    await message.answer(help_text, parse_mode="HTML")

# Handler for /settings command (for groups)
@dp.message(Command("settings"))
async def send_settings(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Check if user has permission
        if not await check_permission(chat_id, user_id):
            await message.answer("❌ You don't have permission to change settings.\nOnly group owners and moderators can modify settings.")
            return
        
        is_enabled = group_settings.get(chat_id, True)  # Default to enabled
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        status = "Enabled" if is_enabled else "Disabled"
        settings_text += f"Message deletion: <b>{status}</b>\n\n"
        
        # Show current default time
        default_time = default_deletion_times.get(chat_id, 60)
        settings_text += f"Default deletion time: <b>{format_time(default_time)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        keyboard = get_group_settings_keyboard(chat_id, is_enabled)
        await message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer("⚙️ Settings are only available in groups.")

# Handler for regular messages
@dp.message()
async def handle_message(message: Message):
    # Check if this is a group and if message deletion is enabled
    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id
        is_enabled = group_settings.get(chat_id, True)  # Default to enabled
        
        if not is_enabled:
            # If deletion is disabled, just send a message without timer options
            await message.answer("⚠️ Message deletion is currently disabled in this group.")
            return
        else:
            # If deletion is enabled, use the default time for automatic deletion
            default_time = default_deletion_times.get(chat_id, 60)  # Default to 60 seconds
            await schedule_message_deletion(
                chat_id=message.chat.id,
                message_id=message.message_id,
                delay_seconds=default_time
            )
    else:
        # For private chats, show timer options
        await message.answer(
            "⏱️ Select a time for this message to self-destruct:",
            reply_markup=get_timer_keyboard()
        )

# Handler for callback queries
@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery):
    # Check if this is a group callback and requires permission
    if callback_query.message.chat.type in ["group", "supergroup"]:
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        
        # Check if user has permission for settings-related callbacks
        if callback_query.data in [
            "enable_delete", "disable_delete", "time_60", "time_300", "time_600",
            "time_21600", "time_43200", "time_86400", "increase_default_time",
            "decrease_default_time", "save_changes"
        ]:
            if not await check_permission(chat_id, user_id):
                await bot.answer_callback_query(
                    callback_query.id, 
                    "❌ You don't have permission to change settings.\nOnly group owners and moderators can modify settings.",
                    show_alert=True
                )
                return
    
    if callback_query.data.startswith("timer_"):
        # Extract delay in seconds
        delay_seconds = int(callback_query.data.split("_")[1])
        
        # Inform user about the selected timer
        formatted_time = format_time(delay_seconds)
        await bot.answer_callback_query(
            callback_query.id,
            f"⏰ Timer set to {formatted_time}! Message will self-destruct after this time."
        )
        
        # Schedule the original message for deletion
        original_message = callback_query.message.reply_to_message or callback_query.message
        await schedule_message_deletion(
            chat_id=original_message.chat.id,
            message_id=original_message.message_id,
            delay_seconds=delay_seconds
        )
        
        # Edit the reply message to confirm
        await callback_query.message.edit_text(
            f"⏱️ Selected timer: {formatted_time}.\n"
            f"The message will self-destruct in {formatted_time}!"
        )
    
    elif callback_query.data == "custom_time":
        # Show custom time interface
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        key = f"{user_id}:{chat_id}"
        
        # Set default custom time to 1 hour if not set
        if key not in custom_timers:
            custom_timers[key] = 3600  # 1 hour in seconds
        
        await callback_query.message.edit_text(
            f"⏱️ <b>Custom Timer Settings</b> ⏱️\n\n"
            f"Current time: <b>{format_time(custom_timers[key])}</b>\n\n"
            f"Use the buttons below to adjust the time:",
            parse_mode="HTML",
            reply_markup=get_custom_time_keyboard(custom_timers[key])
        )
    
    elif callback_query.data == "increase_hour":
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        key = f"{user_id}:{chat_id}"
        
        # Increase time by 1 hour (3600 seconds)
        if key not in custom_timers:
            custom_timers[key] = 3600
        custom_timers[key] += 3600
        
        # Cap at 24 hours (86400 seconds)
        if custom_timers[key] > 86400:
            custom_timers[key] = 86400
        
        await callback_query.message.edit_text(
            f"⏱️ <b>Custom Timer Settings</b> ⏱️\n\n"
            f"Current time: <b>{format_time(custom_timers[key])}</b>\n\n"
            f"Use the buttons below to adjust the time:",
            parse_mode="HTML",
            reply_markup=get_custom_time_keyboard(custom_timers[key])
        )
        
        await callback_query.answer(f"Time increased to {format_time(custom_timers[key])}")
    
    elif callback_query.data == "decrease_hour":
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        key = f"{user_id}:{chat_id}"
        
        # Decrease time by 1 hour (3600 seconds), minimum 60 seconds
        if key not in custom_timers:
            custom_timers[key] = 3600
        custom_timers[key] -= 3600
        
        if custom_timers[key] < 60:
            custom_timers[key] = 60
        
        await callback_query.message.edit_text(
            f"⏱️ <b>Custom Timer Settings</b> ⏱️\n\n"
            f"Current time: <b>{format_time(custom_timers[key])}</b>\n\n"
            f"Use the buttons below to adjust the time:",
            parse_mode="HTML",
            reply_markup=get_custom_time_keyboard(custom_timers[key])
        )
        
        await callback_query.answer(f"Time decreased to {format_time(custom_timers[key])}")
    
    elif callback_query.data.startswith("set_custom_"):
        # Extract custom time from callback data
        delay_seconds = int(callback_query.data.split("_")[2])
        
        # Inform user about the selected timer
        formatted_time = format_time(delay_seconds)
        await bot.answer_callback_query(
            callback_query.id,
            f"⏰ Custom timer set to {formatted_time}! Message will self-destruct after this time."
        )
        
        # Schedule the original message for deletion
        original_message = callback_query.message.reply_to_message or callback_query.message
        await schedule_message_deletion(
            chat_id=original_message.chat.id,
            message_id=original_message.message_id,
            delay_seconds=delay_seconds
        )
        
        # Edit the reply message to confirm
        await callback_query.message.edit_text(
            f"⏱️ Custom timer set: {formatted_time}.\n"
            f"The message will self-destruct in {formatted_time}!"
        )
    
    elif callback_query.data == "cancel_custom":
        await callback_query.message.edit_text(
            "⏱️ <b>Custom Timer Settings</b> ⏱️\n\n"
            "Timer selection cancelled.",
            parse_mode="HTML",
            reply_markup=get_timer_keyboard()
        )
    
    elif callback_query.data == "start_settings":
        if callback_query.message.chat.type in ["private"]:
            await callback_query.message.edit_text(
                "🔧 <b>Settings Menu</b> 🔧\n\n"
                "This bot doesn't have personal settings.\n\n"
                "Use this bot in groups where owners and moderators can configure:\n"
                "• Enable/disable message deletion\n"
                "• Set default deletion time\n\n"
                "Use /settings in a group to manage group settings.",
                parse_mode="HTML"
            )
        else:
            chat_id = callback_query.message.chat.id
            user_id = callback_query.from_user.id
            
            # Check if user has permission
            if not await check_permission(chat_id, user_id):
                await callback_query.answer(
                    "❌ You don't have permission to change settings.\nOnly group owners and moderators can modify settings.",
                    show_alert=True
                )
                return
            
            is_enabled = group_settings.get(chat_id, True)  # Default to enabled
            
            settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
            status = "Enabled" if is_enabled else "Disabled"
            settings_text += f"Message deletion: <b>{status}</b>\n\n"
            
            # Show current default time
            default_time = default_deletion_times.get(chat_id, 60)
            settings_text += f"Default deletion time: <b>{format_time(default_time)}</b>\n\n"
            settings_text += "Adjust settings below:"
            
            keyboard = get_group_settings_keyboard(chat_id, is_enabled)
            await callback_query.message.edit_text(settings_text, parse_mode="HTML", reply_markup=keyboard)
    
    elif callback_query.data == "enable_delete":
        chat_id = callback_query.message.chat.id
        group_settings[chat_id] = True
        is_enabled = group_settings.get(chat_id, True)
        
        # Show current default time
        default_time = default_deletion_times.get(chat_id, 60)
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        settings_text += f"Message deletion: <b>Enabled</b>\n\n"
        settings_text += f"Default deletion time: <b>{format_time(default_time)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        await bot.answer_callback_query(callback_query.id, "✅ Message deletion enabled in this group!")
        await safe_edit_message(
            callback_query.message,
            settings_text,
            reply_markup=get_group_settings_keyboard(chat_id, True)
        )
    
    elif callback_query.data == "disable_delete":
        chat_id = callback_query.message.chat.id
        group_settings[chat_id] = False
        is_enabled = group_settings.get(chat_id, True)
        
        # Show current default time
        default_time = default_deletion_times.get(chat_id, 60)
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        settings_text += f"Message deletion: <b>Disabled</b>\n\n"
        settings_text += f"Default deletion time: <b>{format_time(default_time)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        await bot.answer_callback_query(callback_query.id, "❌ Message deletion disabled in this group!")
        await safe_edit_message(
            callback_query.message,
            settings_text,
            reply_markup=get_group_settings_keyboard(chat_id, False)
        )
    
    elif callback_query.data.startswith("time_"):
        chat_id = callback_query.message.chat.id
        # Extract time from callback data
        time_seconds = int(callback_query.data.split("_")[1])
        default_deletion_times[chat_id] = time_seconds
        is_enabled = group_settings.get(chat_id, True)
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        status = "Enabled" if is_enabled else "Disabled"
        settings_text += f"Message deletion: <b>{status}</b>\n\n"
        settings_text += f"Default deletion time: <b>{format_time(time_seconds)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        await safe_edit_message(
            callback_query.message,
            settings_text,
            reply_markup=get_group_settings_keyboard(chat_id, is_enabled)
        )
        await bot.answer_callback_query(callback_query.id, f"Default time set to {format_time(time_seconds)}")
    
    elif callback_query.data == "increase_default_time":
        chat_id = callback_query.message.chat.id
        
        # Get current default time and increase by 1 hour (3600 seconds)
        current_time = default_deletion_times.get(chat_id, 60)
        new_time = current_time + 3600
        
        # Cap at 24 hours (86400 seconds)
        if new_time > 86400:
            new_time = 86400
            
        default_deletion_times[chat_id] = new_time
        is_enabled = group_settings.get(chat_id, True)
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        status = "Enabled" if is_enabled else "Disabled"
        settings_text += f"Message deletion: <b>{status}</b>\n\n"
        settings_text += f"Default deletion time: <b>{format_time(new_time)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        await safe_edit_message(
            callback_query.message,
            settings_text,
            reply_markup=get_group_settings_keyboard(chat_id, is_enabled)
        )
        await callback_query.answer(f"Default time increased to {format_time(new_time)}")
    
    elif callback_query.data == "decrease_default_time":
        chat_id = callback_query.message.chat.id
        
        # Get current default time and decrease by 1 hour (3600 seconds), minimum 0 seconds
        current_time = default_deletion_times.get(chat_id, 60)
        new_time = current_time - 3600
        
        if new_time < 0:
            new_time = 0
            
        default_deletion_times[chat_id] = new_time
        is_enabled = group_settings.get(chat_id, True)
        
        settings_text = f"🔧 <b>Group Settings</b> 🔧\n\n"
        status = "Enabled" if is_enabled else "Disabled"
        settings_text += f"Message deletion: <b>{status}</b>\n\n"
        settings_text += f"Default deletion time: <b>{format_time(new_time)}</b>\n\n"
        settings_text += "Adjust settings below:"
        
        await safe_edit_message(
            callback_query.message,
            settings_text,
            reply_markup=get_group_settings_keyboard(chat_id, is_enabled)
        )
        await callback_query.answer(f"Default time decreased to {format_time(new_time)}")
    
    elif callback_query.data == "show_default_time":
        chat_id = callback_query.message.chat.id
        current_time = default_deletion_times.get(chat_id, 60)
        await callback_query.answer(f"Current default time: {format_time(current_time)}")
    
    elif callback_query.data == "save_changes":
        chat_id = callback_query.message.chat.id
        is_enabled = group_settings.get(chat_id, True)
        default_time = default_deletion_times.get(chat_id, 60)
        
        # Send confirmation message
        confirmation_text = (
            f"✅ <b>Settings Saved Successfully!</b> ✅\n\n"
            f"• Message deletion: <b>{'Enabled' if is_enabled else 'Disabled'}</b>\n"
            f"• Default deletion time: <b>{format_time(default_time)}</b>\n\n"
            f"All changes have been applied to this group."
        )
        
        await callback_query.message.edit_text(confirmation_text, parse_mode="HTML")
        await bot.answer_callback_query(callback_query.id, "Settings saved successfully!")
    
    elif callback_query.data == "show_time":
        # Just show the current time without changing anything
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        key = f"{user_id}:{chat_id}"
        
        if key in custom_timers:
            await callback_query.answer(f"Current time: {format_time(custom_timers[key])}")
        else:
            await callback_query.answer("Current time: 1 hour")
    
    # Acknowledge the callback
    await callback_query.answer()

# Run scheduler
async def run_scheduler():
    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("Starting Message Self-Destructor Bot...")
    print("Bot is running...")
    
    # Run the bot
    try:
        dp.run_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"An error occurred: {e}")