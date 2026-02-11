import os
import json
from typing import Any, Dict, Optional
from services.event_bus import event_bus
import consts

class BasePlugin:
    """
    Standard base class for all Fern plugins.
    """
    name = "BasePlugin"
    priority = 50
    
    # Default settings that can be overridden by plugins/config.py
    default_config: Dict[str, Any] = {}

    def __init__(self, context) -> None:
        self.ctx = context
        self.enabled = True
        
        # Load merged configuration
        self.config = self._merge_config()
        
        # Centralized paths
        self.data_dir = os.path.join(consts.USER_DATA_DIR, "plugins", self.name.lower())
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.state_file = os.path.join(self.data_dir, "state.json")
        self.log_file = os.path.join(self.data_dir, "plugin.log")

    def _merge_config(self) -> Dict[str, Any]:
        """Merges default plugin config with global overrides from plugins/config.py."""
        import plugins.config as global_plugin_config
        
        # Start with defaults
        merged = self.default_config.copy()
        
        # Apply global overrides if they exist
        global_overrides = global_plugin_config.PLUGIN_CONFIG.get(self.name, {})
        merged.update(global_overrides)
        
        # Check if enabled globally
        self.enabled = global_plugin_config.PLUGIN_ENABLED.get(self.name, True)
        
        return merged

    def load_state(self) -> Dict[str, Any]:
        """Loads plugin state from the centralized data directory."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"   [!] {self.name}: Failed to load state: {e}")
        return {}

    def save_state(self, data: Dict[str, Any]):
        """Saves plugin state to the centralized data directory."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"   [!] {self.name}: Failed to save state: {e}")

    def log(self, message: str):
        """Writes to the plugin-specific log file."""
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}")
        except: pass

    async def on_enable(self):
        """Called when the plugin is loaded and enabled."""
        pass

    async def on_disable(self):
        """Called when the plugin is being unloaded or disabled."""
        pass

    # Standard Event Hooks (To be overridden)
    async def on_chat_message(self, sender: str, text: str, bubble: Any, **kwargs) -> bool:
        return True

    async def on_tick(self, bot) -> None:
        pass

    async def on_local_command(self, command: str) -> bool:
        return True
