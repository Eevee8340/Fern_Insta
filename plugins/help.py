import asyncio
import consts
import plugins.config as plugin_config
from services.event_bus import event_bus

PRIORITY = 99

# Static Registry of Known Commands
# Format: "PluginName": [("/command", "Description")]
COMMAND_REGISTRY = {
    "Core": [
        ("`/fern sleep`", "Put Fern to sleep (stops replying)"),
        ("`/fern wake`", "Wake Fern up"),
        ("`/fern ping`", "Pong!"),
        ("`/fern say <text>`", "Make Fern say something")
    ],
    "Dreamer": [
        ("`/fern dream`", "Force a hallucination/dream")
    ],
    "Mimic": [
        ("`/fern clone @user`", "Imitate a user (Identity Theft)"),
        ("`/fern unclone`", "Restore original persona")
    ],
    "Archivist": [
        ("`/fern recap`", "Summarize recent chat history"),
        ("`/fern clearmem`", "Wipe active memory buffer")
    ],
    "Leaderboard": [
        ("`/fern top`", "Show All-Time Leaderboard"),
        ("`/fern top week`", "Show Weekly Leaderboard"),
        ("`/fern top day`", "Show Daily Leaderboard")
    ],
    "PublicDashboard": [
        ("`/force_export`", "Update Dashboard (Local Only)")
    ]
}

class HelpPlugin:
    def __init__(self, ctx):
        self.ctx = ctx
        self.dynamic_registry = {} # Allow runtime registration

    def register_command(self, plugin_name, command, description):
        if plugin_name not in self.dynamic_registry:
            self.dynamic_registry[plugin_name] = []
        self.dynamic_registry[plugin_name].append((command, description))

    def generate_help_text(self) -> str:
        lines = ["**Fern AI Commands**", "-------------------"]
        
        # Merge Static and Dynamic Registries
        all_plugins = set(COMMAND_REGISTRY.keys()) | set(self.dynamic_registry.keys())
        
        for plugin in sorted(list(all_plugins)):
            # Check if Plugin is Enabled
            # If not in config, assume Enabled (e.g. Core, Leaderboard)
            if not plugin_config.PLUGIN_ENABLED.get(plugin, True):
                continue
                
            cmds = COMMAND_REGISTRY.get(plugin, []) + self.dynamic_registry.get(plugin, [])
            if not cmds: continue
            
            lines.append(f"\n__{plugin}__")
            for cmd, desc in cmds:
                lines.append(f"{cmd} - {desc}")
                
        return "\n".join(lines)

    async def handle_chat_help(self, sender, text, bubble, **kwargs):
        if text.strip().lower() == "/fern help":
            help_text = self.generate_help_text()
            await self.ctx.send_message(help_text)
            return False
        return True

    async def handle_local_command(self, command):
        if command == "/help":
            # Strip markdown for console readability
            help_text = self.generate_help_text().replace("**", "").replace("__", "").replace("`", "")
            print(f"\033[96m{help_text}\033[0m")
            return False
        return True

def register(ctx):
    p = HelpPlugin(ctx)
    event_bus.subscribe(consts.EVENT_CHAT_MESSAGE, p.handle_chat_help, priority=PRIORITY)
    event_bus.subscribe(consts.EVENT_LOCAL_COMMAND, p.handle_local_command, priority=PRIORITY)
    
    # Expose for other plugins
    ctx._bot.help_plugin = p