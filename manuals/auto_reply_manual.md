# Auto Reply Plugin Manual

The `Auto Reply Plugin` is the core intelligence component responsible for deciding when the bot should engage in a conversation. It evaluates incoming messages and triggers the bot's response mechanism if appropriate.

## Core Functionality

- **Engagement Analysis:** Uses the `cortex` service to determine if a message warrants a reply.
- **State Management:** Respects the bot's current state (sleeping or busy) before attempting a reply.
- **Asynchronous Execution:** Launches the reply generation process in a background task to avoid blocking the message processing loop.
- **History Tracking:** Updates the conversation history even if the bot decides not to reply, ensuring it has context for future interactions.

## How it Works in Code

### Class: `AutoReplyPlugin`

- **`__init__(self, ctx)`**: Initializes the plugin with the bot context.
- **`handle_auto_reply(self, sender, text, bubble)`**:
    1. **Metadata Extraction**: Retrieves `parent_context` and `reply_log` from the `bubble` object (usually a dictionary representing the UI element).
    2. **State Checks**:
        - If `bot.is_sleeping` is true, it ignores the message.
        - If `bot.is_busy` is true, it ignores the message to prevent overlapping replies.
    3. **Cortex Integration**: Calls `await cortex.ask_engagement(sender, text)` to get a decision (`should_reply`) and a `reason`.
    4. **Action**:
        - **If `should_reply` is True**: Logs the decision and starts `bot.execute_reply` as an asynchronous task. It returns `False` to indicate the message has been "consumed".
        - **If `should_reply` is False**: Logs the reason for ignoring. If the sender isn't the bot itself, it updates the `cortex` history with the message content. It returns `False`.

### Integration

- **Priority:** Sets a `PRIORITY` of `10`, which is lower than `AdminChatPlugin`, allowing admin commands to be processed first.
- **Registration**: Subscribes to `EVENT_CHAT_MESSAGE` on the `event_bus`.

## Logic Flow

1. Message received.
2. Is bot sleeping? Yes -> Ignore.
3. Is bot already replying? Yes -> Ignore.
4. Ask `Cortex`: "Should I reply to this?"
5. `Cortex` says "Yes" -> Start `execute_reply`.
6. `Cortex` says "No" -> Update history with the message (if not from self) and stay silent.

## Configuration & Dependencies

- `config.BOT_HANDLE`, `config.BOT_NAME`: Used to identify if a message is from the bot itself.
- `cortex.ask_engagement`: The AI-driven decision engine.
- `bot.execute_reply`: The method that generates and sends a response.
- `consts.EVENT_CHAT_MESSAGE`: The trigger event.
