# Mimic Plugin Manual

The `Mimic Plugin` is a persona-switching engine that allows Fern to "clone" the identity and speaking style of any user in the chat. It achieves this by collecting per-user message logs and using an LLM to generate a customized system prompt that captures the target's unique linguistic traits.

## Core Functionality

- **Per-User Logging:** Silently records messages from every user into individual text files in the `user_data/` directory.
- **Style Analysis:** Uses an LLM to analyze a user's slang, grammar, casing, and tone from their last 200 messages.
- **Persona Generation:** Creates a persistent "System Prompt" for the cloned user, stored in `clones.json`.
- **Identity Theft (Cloning):** Switches the bot's core profile to the generated persona.
- **Mention Interception:** If a clone is active, the bot will automatically intercept and reply to any message that mentions the cloned user's handle.

## How it Works in Code

### Class: `MimicPlugin`

- **`__init__(self, context)`**:
    - Initializes `PluginLLM` for profile generation.
    - Loads existing clones from `clones.json`.
    - Backs up the `original_profile` (from `config.py`) to allow for restoration.
- **`on_chat_message(self, sender, text, bubble)`**:
    - **Logging**: Extracts the sender's handle and appends the message text to a handle-specific buffer.
    - **Flushing**: Periodically writes the buffer to `user_data/<handle>.txt` to minimize file open/close cycles.
    - **Command Detection**: Checks for `/fern clone <target>` or `/fern unclone`.
    - **Interception**: If `active_clone` is set and the `active_clone` handle is mentioned in a message, it triggers an immediate response.
- **`activate_clone(self, bot, target_handle)`**:
    1. **Cache Check**: If the handle already exists in `clones.json`, it immediately sends the stored prompt to the `cortex`.
    2. **Data Gathering**: Reads up to 200 lines from the user's log file.
    3. **LLM Generation**: Sends the logs to the LLM with a detailed meta-prompt instructing it to "study how they talk, not what they say."
    4. **Persistence**: Saves the resulting "Clone Prompt" to `clones.json`.
    5. **Activation**: Sends the new prompt to the `cortex` via `set_profile`.
- **`restore_original(self, bot)`**:
    - Reverts the `cortex` profile back to the bot's default persona.

### Data Storage

- **User Logs**: `user_data/@username.txt` (Raw text of all messages sent by that user).
- **Clone Profiles**: `clones.json` (Dictionary mapping handles to generated system prompts).

## Commands

| Command | Action |
| :--- | :--- |
| `/fern clone @user` | Generates (if needed) and activates the persona of `@user`. |
| `/fern clone me` | Clones the person who sent the command. |
| `/fern unclone` | Restores Fern's original personality. |

## Interaction with Cortex

The plugin uses `cortex.send_command("set_profile", prompt)`. This instruction changes the underlying system instructions for the LLM, effectively altering the bot's personality, vocabulary, and behavior without requiring a restart.

## Metadata & Casing

The generation prompt specifically instructs the LLM to capture:
- **Casing & Punctuation:** Does the user use all lowercase? Do they use excessive exclamation marks?
- **Message Length:** Are they a "yapper" (long messages) or a "texter" (short bursts)?
- **Reactions:** How do they respond when challenged or joked with?
