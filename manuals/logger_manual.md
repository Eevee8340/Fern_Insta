# Logger Plugin Manual

The `Logger Plugin` is a utility component designed to maintain a persistent record of all chat interactions. It acts as a passive observer, writing every incoming message to a text-based log file.

## Core Functionality

- **Persistent Logging:** Appends every chat message to a central log file with a timestamp.
- **High Priority Recording:** Processes messages with very high priority to ensure logs are captured even if other plugins intercept or modify the message flow.
- **Directory Management:** Automatically creates the necessary storage directories if they are missing.

## How it Works in Code

### Class: `LoggerPlugin`

- **`__init__(self, context)`**: 
    - Ensures the `USER_DATA_DIR` exists using `os.makedirs`.
- **`on_chat_message(self, sender, text, bubble)`**:
    - Triggered by `EVENT_CHAT_MESSAGE`.
    - **Formatting**: Generates a timestamp string `[YYYY-MM-DD HH:MM:SS]`.
    - **Writing**: Opens `chat.log` in append mode (`"a"`) and writes the formatted entry: `[Timestamp] Sender: Text`.
    - **Error Handling**: Wraps the file I/O in a try-except block to prevent logging failures from crashing the bot.
    - **Return Value**: Always returns `True`, ensuring other plugins also receive the message event.

### Integration

- **Priority:** Set to `1000`. This is exceptionally high, meaning it is one of the first plugins to "see" a message before any filtering or command processing occurs.
- **File Location:** Logs are saved to `user_data/chat.log`.

## Log Format Example

```text
[2026-02-04 16:30:15] John Doe (@jdoe): Hello Fern!
[2026-02-04 16:30:20] Fern (@fern_bot): Hello John!
```

## Maintenance

The log file grows indefinitely. Administrators should periodically archive or truncate `user_data/chat.log` if disk space becomes a concern, or use the `Archivist` features (if available) to manage long-term history.
