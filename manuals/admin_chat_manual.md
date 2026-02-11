# Admin Chat Plugin Manual

The `Admin Chat Plugin` provides a mechanism for an authorized administrator to control the Fern bot directly through the chat interface. It monitors incoming messages and intercepts commands prefixed with `/fern`.

## Core Functionality

- **Command Interception:** Listens for chat messages and checks if they come from the designated administrator.
- **Admin Verification:** Securely extracts the sender's handle and compares it against `config.ADMIN_USERNAME`.
- **Bot Control:** Routes specific commands to the bot's internal command queue.

## How it Works in Code

### Class: `AdminChatPlugin`

- **`__init__(self, ctx)`**: Initializes the plugin with the bot context (`ctx`).
- **`handle_chat_command(self, sender, text, bubble)`**: This is the primary event handler.
    1. **Handle Extraction**: Uses regex `\(@(.*?)\)` to extract the user's handle from the `sender` string. It also has a fallback for simpler formats.
    2. **Verification**: Checks if the extracted handle matches `config.ADMIN_USERNAME` (case-insensitive).
    3. **Parsing**: If the message starts with `/fern `, it splits the text into the action and arguments.
    4. **Execution**: Based on the action, it puts a command into `bot.command_queue`.
    5. **Return Value**:
        - Returns `False` if it handled a command, which stops further processing of the message by other plugins (due to its high priority).
        - Returns `True` if it's not a valid admin command, allowing other plugins to process it.

### Integration

- **Priority:** Sets a `PRIORITY` of `100`, ensuring it processes messages before most other plugins.
- **Registration**: The `register(ctx)` function creates an instance and subscribes it to the `EVENT_CHAT_MESSAGE` on the `event_bus`.

## Supported Commands

The plugin handles the following commands when prefixed with `/fern `:

| Action | Bot Command | Description |
| :--- | :--- | :--- |
| `sleep` | `/sleep` | Puts the bot into a sleep state. |
| `wake` or `wakey` | `/wake` | Wakes the bot up. |
| `clearmem` | `/clearmem` | Clears the bot's temporary memory. |
| `ping` | `/ping` | A simple check to see if the bot is responsive. |
| `say <message>` | `/say <message>` | Forces the bot to send the specified `<message>` in chat. |

## Configuration Dependencies

- `config.ADMIN_USERNAME`: The handle of the user allowed to use these commands.
- `consts.EVENT_CHAT_MESSAGE`: The event ID for incoming chat messages.
- `services.event_bus`: The central event system.
