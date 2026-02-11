# Leaderboard Plugin Manual

The `Leaderboard Plugin` tracks user participation within the chat, playfully ranking users as "Yappers" based on the volume of messages they send. It provides visibility into engagement trends over daily, weekly, and all-time intervals.

## Core Functionality

- **Message Tracking:** Monitors all incoming chat messages and increments activity counters for each user handle.
- **Time-Based Resets:** Automatically clears the "Daily" leaderboard at 09:00 AM and the "Weekly" leaderboard every 7 days.
- **Batched Persistence:** Saves leaderboard data to `leaderboard.json` in batches (every 10 updates or 60 seconds) to minimize disk I/O.
- **Leaderboard Display:** Generates and sends a ranked list of the top 5 users to the chat upon request.

## How it Works in Code

### Class: `LeaderboardPlugin`

- **`__init__(self, context)`**:
    - Initializes the data structure for different timeframes.
    - Loads existing data from `leaderboard.json`.
    - Sets up batching parameters (`pending_updates`, `save_interval`).
- **`load_data()` / `save_data()`**:
    - Handles reading from and writing to the JSON persistence file.
    - Ensures the data structure is consistent even if the file is missing or corrupted.
- **`check_resets()`**:
    - Logic for clearing temporal leaderboards.
    - Uses 09:00 AM as the daily sync point.
    - Resets the `daily` dictionary and updates the `last_daily_reset` timestamp.
- **`on_chat_message(self, sender, text, bubble)`**:
    - Triggered by `EVENT_CHAT_MESSAGE`.
    - **Filtering:** Ignores messages from the bot itself or system messages.
    - **Command Parsing:** If the message starts with `/fern top`, it routes to the command handler.
    - **Handle Extraction:** Safely extracts the user's handle from the sender string (e.g., `Name (@handle)` -> `@handle`).
    - **Counting:** Increments the count for the user in `all_time`, `weekly`, and `daily` dictionaries.
    - **Batching Logic:** Increments `pending_updates`. If the limit is reached or time has elapsed, it calls `save_data()`.
- **`on_local_command(self, command)`**:
    - Handles `/top`, `/top week`, and `/top day`.
    - Sorts the relevant dictionary by message count (descending).
    - Formats the top 5 users with medals (🥇, 🥈, 🥉) and sends the message.

### Data Structure (`leaderboard.json`)

```json
{
  "all_time": { "@user1": 150, "@user2": 120 },
  "weekly": { "@user1": 10 },
  "daily": { "@user1": 2 },
  "last_daily_reset": 1738659600.0,
  "last_weekly_reset": 1738659600.0
}
```

## Integration

- **Event Bus:** Subscribes to `EVENT_CHAT_MESSAGE` (Priority 50) and `EVENT_LOCAL_COMMAND`.
- **Persistence:** Uses `leaderboard.json` in the project root.

## Supported Commands

| Command | Action |
| :--- | :--- |
| `/fern top` | Shows the top 5 all-time contributors. |
| `/fern top week` | Shows the top 5 contributors for the current week. |
| `/fern top day` | Shows the top 5 contributors since the 9 AM reset. |

## Logic Details: The 9 AM Reset

The plugin doesn't use a background timer for resets. Instead, it checks if a reset is due *every time a message is received*. If the current time has passed 09:00 AM today, and the `last_daily_reset` was *before* 09:00 AM today, it performs the wipe.
