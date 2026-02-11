import importlib
import os
import sys
import traceback
import asyncio
from typing import Any, List, Dict, Optional, Type
import consts
from services.event_bus import event_bus
from services.config_manager import config_manager
from plugins.base import BasePlugin

class PluginContext:
    """The restricted interface provided to plugins."""
    def __init__(self, bot: Any, plugin_name: str) -> None:
        self._bot = bot
        self.name = plugin_name
        self.config = config_manager.main_config
        
        # Centralized data path for this plugin
        self.data_dir = os.path.join(consts.USER_DATA_DIR, "plugins", plugin_name.lower())
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def is_busy(self) -> bool:
        return self._bot.is_busy

    @property
    def is_sleeping(self) -> bool:
        return self._bot.is_sleeping

    async def log(self, text: str) -> None:
        # Log to console/main bot log
        await self._bot.log(f"   [{self.name}] {text}")

    async def reply(self, sender: str, text: str, bubble: Any = None, trace_id: Optional[str] = None) -> None:
        """Triggers the bot's engagement logic (LLM reply)."""
        self._bot.is_busy = True
        asyncio.create_task(self._bot.execute_reply(sender, text, bubble, trace_id=trace_id))

    async def send_message(self, text: str) -> None:
        """Send a direct message without LLM generation."""
        async def msg_gen(): yield text
        await self._bot.type_and_send(msg_gen())

    def set_profile(self, prompt: str) -> None:
        """Updates the AI's system personality prompt."""
        if self._bot.cortex:
            self._bot.cortex.send_command("set_profile", prompt)

    def get_cortex(self) -> Any:
        return self._bot.cortex

class PluginManager:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_dir = "plugins"

    def load_plugins(self) -> None:
        if not os.path.exists(self.plugin_dir):
            return

        # Ensure base data dir exists
        os.makedirs(os.path.join(consts.USER_DATA_DIR, "plugins"), exist_ok=True)

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__") and filename not in ["config.py", "llm_utils.py", "base.py"]:
                plugin_name = filename[:-3]
                try:
                    module_name = f"plugins.{plugin_name}"
                    if module_name in sys.modules:
                        importlib.reload(sys.modules[module_name])
                    module = importlib.import_module(module_name)
                    
                    # New Logic: Look for register function
                    if hasattr(module, "register"):
                        context = PluginContext(self.bot, plugin_name)
                        plugin_instance = module.register(context)
                        
                        if isinstance(plugin_instance, BasePlugin):
                            self.plugins[plugin_name] = plugin_instance
                            # Automatically hook up events if they are overridden
                            self._auto_subscribe(plugin_instance)
                            
                            # Call on_enable
                            asyncio.create_task(plugin_instance.on_enable())
                            
                        print(f"   [+] Plugin Loaded: {plugin_name}")
                except Exception as e:
                    print(f"   [!] Failed to load {plugin_name}: {e}")
                    traceback.print_exc()

    def _auto_subscribe(self, plugin: BasePlugin):
        """Automatically subscribes plugin methods to the event bus based on overrides."""
        if type(plugin).on_chat_message != BasePlugin.on_chat_message:
            event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, plugin.on_chat_message, priority=plugin.priority)
            
        if type(plugin).on_tick != BasePlugin.on_tick:
            event_bus.subscribe(consts.EVENT_TICK, plugin.on_tick, priority=plugin.priority)
            
        if type(plugin).on_local_command != BasePlugin.on_local_command:
            event_bus.subscribe(consts.EVENT_LOCAL_COMMAND, plugin.on_local_command, priority=plugin.priority)

    async def dispatch(self, event_name: str, *args, **kwargs) -> bool:
        """Deprecated: Use event_bus.emit directly."""
        results = await event_bus.emit(event_name, *args, **kwargs)
        return not any(r is False for r in results)
