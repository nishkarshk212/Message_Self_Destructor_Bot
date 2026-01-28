# Message Self-Destructor Telegram Bot

A Telegram bot that allows users to send self-destructing messages with customizable timers.

## Features

- **Self-destructing Messages**: Send messages that automatically delete themselves after a specified time
- **Automatic Group Deletion**: In groups, messages auto-delete based on default settings
- **Custom Timers**: Choose from various timer options (5 seconds to 1 hour)
- **Custom Time Setting**: Use + and - buttons to set custom time in hours
- **Enhanced Group Settings**: Enable/disable message deletion and set default deletion time in groups
- **Permission Control**: Only group owners and moderators can change settings
- **Predefined Time Options**: Quick access to 1 min, 5 min, 10 min, 6 hour, 12 hour, and 24 hour options
- **Time Adjustment**: + and - buttons to adjust default deletion time in groups (minimum 0 minutes)
- **Save Confirmation**: Save changes button with confirmation message
- **Owner & Channel Links**: Direct links to owner and channel
- **Add to Group Button**: Easy way to add the bot to groups
- **Settings Button**: Direct access to settings from start menu
- **Profile Picture Reference**: Start message includes reference to bot's profile picture

## Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help information
- `/settings` - Configure group settings (owners/moderators only)

## Timer Options

- 5 seconds
- 10 seconds
- 30 seconds
- 1 minute
- 5 minutes
- 10 minutes
- 1 hour
- **Custom Timer**: Use the '⏱️ Custom Time' button to set custom time with + and - controls

## Bot Details

- **Bot Token**: Stored in .env file
- **Bot Username**: @Message_Self_destruction_212_bot
- **Owner**: @Hacker_unity_212
- **Channel**: @Titanic_bots

## How to Use

1. Start a chat with the bot or add it to your group
2. In groups, the bot will automatically apply the default settings to all messages
3. In private chats, the bot will prompt you to select a timer for self-destruction
4. In groups, only **owners and moderators** can use `/settings` or the "⚙️ Settings" button to configure:
   - Enable/disable message deletion for all messages
   - Set default deletion time with quick presets (1 min, 5 min, 10 min, 6 hour, 12 hour, 24 hour)
   - Adjust time with + and - buttons (1-hour increments, minimum 0 minutes)
   - Save changes with confirmation message

## Technical Implementation

- Built with Python using the aiogram library
- Uses environment variables for secure token storage
- Uses asyncio for scheduling message deletions
- Maintains separate settings for each group
- Provides inline keyboards for easy interaction
- Handles TelegramBadRequest exceptions gracefully
- Implements permission checking for group settings

## Buttons

- **Mention Owner**: Links to @Hacker_unity_212
- **Channel**: Links to @Titanic_bots
- **Add to Group**: Adds the bot to a group with one click
- **Settings**: Access to settings menu from start screen (owners/moderators only)
- **Custom Time**: Allows setting custom time with + and - buttons
- **Save Changes**: Confirms and saves all settings changes

I'm a girl bot 🌸# Message_Self_Destructor_Bot
