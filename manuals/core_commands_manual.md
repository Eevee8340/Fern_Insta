# Core Commands Plugin Manual

The `Core Commands Plugin` handles the fundamental control instructions for the Fern bot. It processes internal commands that change the bot's state or trigger direct actions like sending a specific message.

## Core Functionality

- **State Management:** Toggles the bot between `sleeping` and `awake` states.
- **Memory Management:** Triggers the clearing of the bot's short-term memory in the `cortex`.
- **Direct Messaging:** Allows for manually sending messages through the bot using the `/say` command.
- **Diagnostics:** Responds to `/ping` to verify command processing is active.

## How it Works in Code

### Class: `CoreCommandsPlugin`

- **`__init__(self, ctx)`**: Initializes the plugin with the bot context.
- **`handle_local_command(self, command)`**:
    - This method is triggered by the `EVENT_LOCAL_COMMAND` event.
    - It checks the `command` string against a set of predefined keywords.
    - **`/sleep`**: 
        - Sets `bot.is_sleeping = True`.
        - Sends a "Going to sleep..." message to the chat.
        - Notifies the `cortex` to enter sleep mode.
    - **`/wake`**:
        - Sets `bot.is_sleeping = False`.
        - Sends a "Waking up..." message.
        - Notifies the `cortex` to exit sleep mode.
    - **`/clearmem`**:
        - Notifies the `cortex` to wipe its current context/history.
        - Sends a confirmation message.
    - **`/ping`**:
        - Logs a "PONG!" to the local console (useful for debugging).
    - **`/say <text>`**:
        - Extracts the `<text>` and sends it directly to the chat interface.
    - **Return Value**:
        - Returns `False` if the command was recognized and handled (stopping further event propagation).
        - Returns `True` if the command was not recognized.

### Integration

- **Priority:** Set to `90`.
- **Registration**: Subscribes to `EVENT_LOCAL_COMMAND` on the `event_bus`. This event is typically fired when a command is pulled from the bot's internal `command_queue`.

## Interaction with Cortex

When a state-changing command is received (like sleep or wake), the plugin calls `cortex.send_command(action)`. This ensures that the AI logic is synchronized with the bot's operational state.

## Summary of Commands

| Command | Action | Effect |
| :--- | :--- | :--- |
| `/sleep` | Sleep | Bot stops replying, AI context is notified. |
| `/wake` | Wake | Bot resumes replying, AI context is notified. |
| `/clearmem` | Clear Memory | Wipes current AI conversation history. |
| `/ping` | Diagnostic | Logs activity to console. |
| `/say <msg>` | Say | Bot sends `<msg>` to the chat. |
