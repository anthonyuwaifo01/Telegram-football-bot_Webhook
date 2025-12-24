# Telegram Football Team Bot

A Telegram bot to randomly create football teams from group members who are available.  
Supports admin-controlled selection, dynamic team creation, and live status checking.

---

## Features

- Admin-only commands:
  - `/start_selection` - Start weekly player selection
  - `/end_selection` - End selection and shuffle teams
  - `/status` - Check current player responses
  - `/add_admin @username` - Grant bot admin rights to other members
- Members can join or leave selection:
  - `/in` - Mark yourself as available
  - `/out` - Mark yourself as unavailable
- Dynamic teams: max 6 players per team, random assignment
- Fully async webhook ready for deployment on Render
- Uses FastAPI + python-telegram-bot v21

---

## Commands

| Command                 | Who Can Use           | Description |
|-------------------------|--------------------|-------------|
| `/start_selection`       | Admin only          | Start player collection |
| `/end_selection`         | Admin only          | End selection and create teams |
| `/status`                | Admin only          | Show current IN/OUT status |
| `/add_admin @username`   | Admin only          | Make another member a bot admin |
| `/in`                    | Any member          | Mark as available for selection |
| `/out`                   | Any member          | Mark as unavailable |

---

## Project Structure

