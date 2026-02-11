# Help Plugin Manual

The `Help Plugin` serves as the central documentation repository for all commands supported by the Fern bot. it provides a formatted list of commands to users in the chat and to administrators in the console.

## Core Functionality

- **Command Registry:** Maintains a `COMMAND_REGISTRY` of known commands, grouped by plugin.
- **Dynamic Registration:** Allows other plugins to register their commands at runtime via `register_command`.
- **Chat Help:** Responds to `/fern help` in the chat with a formatted Markdown list.
- **Local Help:** Responds to `/help` in the local console with a plain-text list.
- **State Sensitivity:** Automatically filters out commands from plugins that are currently disabled in `plugin_config`.

## How it Works in Code

### Class: `HelpPlugin`

- **`__init__(self, ctx)`**: Initializes the plugin and an empty `dynamic_registry`.
- **`register_command(self, plugin_name, command, description)`**:
    - This method allows other plugins to programmatically add commands to the help menu.
    - Example: `ctx._bot.help_plugin.register_command("MyPlugin", "/doit", "Does something cool")`.
- **`generate_help_text(self)`**:
    - Merges the static `COMMAND_REGISTRY` and the `dynamic_registry`.
    - Iterates through all plugins and checks `plugin_config.PLUGIN_ENABLED`.
    - Formats the output with Markdown (bold headers, italic plugin names, code blocks for commands).
- **`handle_chat_help(self, sender, text, bubble)`**:
    - Listens for the exact string `/fern help`.
    - Generates the help text and sends it to the chat via `ctx.send_message`.
    - Returns `False` to indicate the message was handled.
- **`handle_local_command(self, command)`**:
    - Listens for `/help` from the internal command queue.
    - Strips Markdown formatting for better console readability and prints the result.

### Integration

- **Priority:** Set to `99` (very high), ensuring help requests are handled before general chat logic.
- **Registration**: Subscribes to `EVENT_CHAT_MESSAGE` and `EVENT_LOCAL_COMMAND`.
- **Exposure**: The instance is attached to `ctx._bot.help_plugin` during registration, making it accessible to other plugins.

## Configuration Dependencies

- `plugin_config.PLUGIN_ENABLED`: Used to determine which commands to show based on active plugins.
- `consts.EVENT_CHAT_MESSAGE` & `consts.EVENT_LOCAL_COMMAND`: Triggers for help display.

## Command Formatting

The plugin organizes commands by the plugin that provides them:

```text
__Plugin Name__
`/command` - Description
```

If a plugin is disabled in the configuration, its entire section is omitted from the help output.
