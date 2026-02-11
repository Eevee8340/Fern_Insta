# Dreamer Plugin Manual

The `Dreamer Plugin` gives the Fern bot a sense of "consciousness" and personality by generating and sharing a surreal dream every morning. This dream is constructed by mixing actual conversation logs and established "lore" into a chaotic narrative.

## Core Functionality

- **Scheduled Activation:** Checks the time once per minute and triggers a "dream broadcast" at a configurable `wake_time` (default: 09:00 AM).
- **Daily Persistence:** Tracks the date of the last dream to ensure it only happens once per day.
- **Contextual Synthesis:** Gathers "ingredients" for the dream from the bot's memory (random logs) and the project's `lore.json`.
- **Surreal Generation:** Uses an LLM to weave these ingredients into a humorous, unhinged, and lower-case paragraph.
- **Chat Broadcast:** Automatically sends the generated dream to the main chat channel.

## How it Works in Code

### Class: `DreamerPlugin`

- **`__init__(self, context)`**:
    - Loads settings from `plugin_config`.
    - Initializes `PluginLLM` with the "Dreamer" context.
    - Loads its state (last dream date) from `user_data/dreamer_state.json`.
- **`on_tick(self, bot)`**:
    - Triggered by `EVENT_TICK` (usually every minute).
    - Compares the current time with `self.wake_time`.
    - If it's time and a dream hasn't been sent today, it calls `broadcast_dream`.
- **`broadcast_dream(self, bot)`**:
    1. **Gather Ingredients**:
        - Requests random log snippets from the `cortex` via IPC (`IPC_GET_RANDOM_LOGS`).
        - Cleans regex patterns (like headers or bold markers) from the logs.
        - Reads random entries from `lore.json`.
    2. **Generate Prompt**: Constructs a prompt for the LLM that instructs it to be "surreal," "funny," and "unhinged," using the gathered fragments as context.
    3. **LLM Call**: Calls `self.llm.generate(prompt)`.
    4. **Sending**: Uses `bot.type_and_send` to broadcast the dream to the chat.
    5. **Logging**: Saves the dream to the bot's history so it remembers what it "dreamed" about.
- **`on_local_command(self, command)`**:
    - Allows manual triggering of the dream using the `/force_dream` command.

### State Persistence

The plugin saves its state in `user_data/dreamer_state.json`:
```json
{
  "last_dream_date": "2026-02-04"
}
```

## Configuration

Settings are managed in `plugins/config.py` under the "Dreamer" key:
- `wake_time`: String (e.g., "08:30") determining when the dream occurs.
- `enabled`: Boolean to toggle the plugin.

## Integration

- **Event Bus:** Subscribes to `EVENT_TICK` for time-based checks and `EVENT_LOCAL_COMMAND` for manual overrides.
- **PluginLLM:** Utilizes the shared LLM utility to handle backend transitions (Gemini vs. Local).
- **Cortex:** Interfaces with the memory system to retrieve random conversation fragments.

## Commands

| Command | Action |
| :--- | :--- |
| `/force_dream` | Immediately triggers the dream generation and broadcast process. |
