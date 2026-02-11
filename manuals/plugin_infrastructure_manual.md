# Plugin Infrastructure Manual

This manual covers the shared utilities and configuration systems that power the Fern AI plugin ecosystem, specifically `llm_utils.py` and `config.py`.

## 1. Plugin Configuration (`plugins/config.py`)

All plugins are governed by a central configuration file that controls their behavior, backend selection, and activation status.

### Key Sections:
- **`PLUGIN_ENABLED`**: A dictionary of booleans. If a plugin is set to `False` here, it will not register or respond to events.
- **`PLUGIN_BACKENDS`**: Maps specific plugins to either `gemini` or `local`. This allows high-priority tasks (like `Dreamer`) to use cloud models while background tasks (like `Archivist`) run on local hardware.
- **`PLUGIN_CONFIG`**: Contains granular settings for each plugin (e.g., `batch_size` for Archivist, `wake_time` for Dreamer).

---

## 2. LLM Utilities (`plugins/llm_utils.py`)

The `PluginLLM` class provides a unified interface for all plugins to interact with Large Language Models, regardless of whether they are hosted on Google Gemini or a local `llama.cpp` server.

### Core Features:
- **Backend Abstraction**: Plugins simply call `llm.generate(prompt)`. The utility handles the routing to the correct API based on the `PLUGIN_BACKENDS` configuration.
- **Singleton Client Cache**: Reuses a single Gemini or OpenAI client across all plugins to save memory and connection overhead.
- **Retry Logic**: Automatically retries failed generations with an exponential backoff (default: 2 retries).
- **Grammar Support**: Supports GBNF grammar for local models, allowing plugins like `Lore` and `Profiler` to force the AI to output valid JSON.
- **Context Isolation**: Each instance of `PluginLLM` is initialized with a `context_name`, allowing for per-plugin temperature and token limit settings.

### How to use in a Plugin:
```python
from plugins.llm_utils import PluginLLM

class MyPlugin:
    def __init__(self, ctx):
        # Initializes with settings for "MyPlugin" from config.py
        self.llm = PluginLLM(context_name="MyPlugin")

    async def do_something(self):
        reply = await self.llm.generate("Hello!")
```

---

## 3. The Event Bus (`services/event_bus.py`)

While not in the `plugins/` folder, the `event_bus` is the nervous system of the plugin architecture.

- **`subscribe(event_id, callback, priority)`**: Plugins use this during `register(ctx)` to listen for chat messages, ticks, or commands.
- **`emit(event_id, *args)`**: Used by the bot or other plugins to trigger actions (e.g., `Summarizer` emits `EVENT_NARRATIVE_LOGGED`).
- **`priority`**: Controls the order of execution. High priority (1000) runs first (e.g., `Logger`). Returning `False` from a callback stops further plugins from receiving that specific event.

## 4. Standard Plugin Lifecycle

1. **Initialization**: `register(ctx)` is called by the `plugin_loader`.
2. **Subscription**: Plugin subscribes to relevant events on the `event_bus`.
3. **Execution**: The plugin's handlers are called when events occur.
4. **Persistence**: Plugins save their state in `user_data/` as JSON files to survive restarts.
