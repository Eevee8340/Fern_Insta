import os
import json
import importlib
from typing import Any, Dict, Optional
import consts

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.main_config: Dict[str, Any] = {}
        self.plugin_config: Dict[str, Any] = {}
        self.load_all()

    def load_all(self):
        self.main_config = self._load_module_to_json("config")
        self.plugin_config = self._load_plugin_module_to_json()

    def _load_module_to_json(self, module_name: str) -> Dict[str, Any]:
        try:
            mod = importlib.import_module(module_name)
            importlib.reload(mod)
            
            data = {}
            for k, v in mod.__dict__.items():
                if k.startswith("__") or hasattr(v, "__call__") or isinstance(v, type):
                    continue
                if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                    data[k] = v
            return data
        except Exception as e:
            print(f"Error loading {module_name}: {e}")
            return {}

    def _load_plugin_module_to_json(self) -> Dict[str, Any]:
        try:
            import plugins.config
            importlib.reload(plugins.config)
            return {
                "enabled": getattr(plugins.config, "PLUGIN_ENABLED", {}),
                "backends": getattr(plugins.config, "PLUGIN_BACKENDS", {}),
                "settings": getattr(plugins.config, "PLUGIN_CONFIG", {}),
                "global": {
                    "default_backend": getattr(plugins.config, "DEFAULT_BACKEND", "gemini"),
                    "gemini_model": getattr(plugins.config, "PLUGIN_GEMINI_MODEL", "gemini-1.5-flash"),
                    "debug": getattr(plugins.config, "DEBUG_MODE", False)
                }
            }
        except Exception as e:
            print(f"Error loading plugins.config: {e}")
            return {}

    def get_main_config_structured(self) -> Dict[str, Any]:
        """Convert flat config module dict to structured dict for UI."""
        c = self.main_config
        return {
            "identity": {
                "BOT_NAME": c.get("BOT_NAME", "Fern"),
                "BOT_HANDLE": c.get("BOT_HANDLE", "@fern08340"),
                "ADMIN_USERNAME": c.get("ADMIN_USERNAME", "@your_username"),
                "TRIGGERS": c.get("TRIGGERS", []),
                "PROFILE": c.get("PROFILE", "")
            },
            "model": {
                "USE_IN_PROCESS_LLM": c.get("USE_IN_PROCESS_LLM", False),
                "MODEL_PATH": c.get("MODEL_PATH", ""),
                "REMOTE_LLM_URL": c.get("REMOTE_LLM_URL", ""),
                "CONTEXT_WINDOW": c.get("CONTEXT_WINDOW", 4096),
                "GPU_LAYERS": c.get("GPU_LAYERS", -1),
                "MAX_TOKENS": c.get("MAX_TOKENS", 300),
                "TEMPERATURE": c.get("TEMPERATURE", 0.7)
            },
            "behavior": {
                "BASE_CHAOS_RATE": c.get("BASE_CHAOS_RATE", 0.05),
                "CONTINUATION_RATE": c.get("CONTINUATION_RATE", 0.2),
                "HISTORY_CHAR_LIMIT": c.get("HISTORY_CHAR_LIMIT", 6000)
            },
            "instagram": {
                "DIRECT_LINK": c.get("DIRECT_LINK", ""),
                "HEADLESS": c.get("HEADLESS", True),
                "BROWSER_SLOW_MO": c.get("BROWSER_SLOW_MO", 50),
                "USER_AGENT": c.get("USER_AGENT", ""),
                "GROUPS": c.get("GROUPS", {})
            },
            "timeouts": {
                "POPUP_TIMEOUT": c.get("POPUP_TIMEOUT", 5000),
                "CHAT_LOAD_TIMEOUT": c.get("CHAT_LOAD_TIMEOUT", 30000),
                "TYPING_DELAY_MIN": c.get("TYPING_DELAY_MIN", 0.01),
                "TYPING_DELAY_MAX": c.get("TYPING_DELAY_MAX", 0.05),
                "REPLY_DELAY_MIN": c.get("REPLY_DELAY_MIN", 1.5),
                "REPLY_DELAY_MAX": c.get("REPLY_DELAY_MAX", 3.0),
                "COOLDOWN_SECONDS": c.get("COOLDOWN_SECONDS", 8.0)
            }
        }

    def save_main_config(self, data: Dict[str, Any]):
        ident = data.get("identity", {})
        model = data.get("model", {})
        behav = data.get("behavior", {})
        insta = data.get("instagram", {})
        time_cfg = data.get("timeouts", {})

        def to_py(obj):
            return json.dumps(obj, indent=4).replace("true", "True").replace("false", "False").replace("null", "None")

        lines = [
            "import os",
            "from dotenv import load_dotenv",
            "",
            "load_dotenv()",
            "",
            "# --- IDENTITY & PERSONALITY ---",
            f"BOT_NAME = os.getenv('BOT_NAME', '{ident.get('BOT_NAME', 'Fern')}')",
            f"BOT_HANDLE = os.getenv('BOT_HANDLE', '{ident.get('BOT_HANDLE', '@fern08340')}')",
            f"ADMIN_USERNAME = '{ident.get('ADMIN_USERNAME', '@your_username')}'",
            f"TRIGGERS = {to_py(ident.get('TRIGGERS', []))}",
            "",
            'PROFILE = """',
            ident.get('PROFILE', '').strip(),
            '""".strip()',
            "",
            "# --- MODEL CONFIGURATION ---",
            f"USE_IN_PROCESS_LLM = {model.get('USE_IN_PROCESS_LLM', False)}",
            "",
            f"MODEL_PATH = '{model.get('MODEL_PATH', '')}'",
            f"REMOTE_LLM_URL = '{model.get('REMOTE_LLM_URL', '')}'",
            "",
            f"CONTEXT_WINDOW = {model.get('CONTEXT_WINDOW', 4096)}",
            f"GPU_LAYERS = {model.get('GPU_LAYERS', -1)}",
            f"MAX_TOKENS = {model.get('MAX_TOKENS', 300)}",
            f"TEMPERATURE = {model.get('TEMPERATURE', 0.7)}",
            "",
            "# --- BEHAVIOR PROBABILITIES ---",
            f"BASE_CHAOS_RATE = float(os.getenv('BASE_CHAOS_RATE', '{behav.get('BASE_CHAOS_RATE', 0.05)}'))",
            f"CONTINUATION_RATE = float(os.getenv('CONTINUATION_RATE', '{behav.get('CONTINUATION_RATE', 0.20)}'))",
            f"HISTORY_CHAR_LIMIT = int(os.getenv('HISTORY_CHAR_LIMIT', '{behav.get('HISTORY_CHAR_LIMIT', 6000)}'))",
            "",
            "# --- INSTAGRAM & BROWSER ---",
            f"DIRECT_LINK = '{insta.get('DIRECT_LINK', '')}'",
            f"HEADLESS = {insta.get('HEADLESS', True)}",
            f"BROWSER_SLOW_MO = {insta.get('BROWSER_SLOW_MO', 50)}",
            f"USER_AGENT = '{insta.get('USER_AGENT', '')}'",
            f"GROUPS = {to_py(insta.get('GROUPS', {}))}",
            "STATE_FILE = 'state.json'",
            "",
            "# --- TERMINAL OUTPUT ---",
            "SHOW_TOKEN_STREAMING = True",
            "",
            "# --- TIMEOUTS & DELAYS ---",
            f"POPUP_TIMEOUT = {time_cfg.get('POPUP_TIMEOUT', 5000)}",
            f"CHAT_LOAD_TIMEOUT = {time_cfg.get('CHAT_LOAD_TIMEOUT', 30000)}",
            "TYPING_CHUNK_SIZE = 20",
            f"TYPING_DELAY_MIN = {time_cfg.get('TYPING_DELAY_MIN', 0.01)}",
            f"TYPING_DELAY_MAX = {time_cfg.get('TYPING_DELAY_MAX', 0.05)}",
            f"REPLY_DELAY_MIN = {time_cfg.get('REPLY_DELAY_MIN', 1.5)}",
            f"REPLY_DELAY_MAX = {time_cfg.get('REPLY_DELAY_MAX', 3.0)}",
            f"COOLDOWN_SECONDS = {time_cfg.get('COOLDOWN_SECONDS', 8.0)}",
            ""
        ]
        
        file_content = "\n".join(lines)
        with open(consts.CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(file_content)
        self.load_all()

    def save_plugin_config(self, data: Dict[str, Any]):
        enabled = data.get("enabled", {})
        backends = data.get("backends", {})
        settings = data.get("settings", {})
        glob = data.get("global", {})

        def to_py(obj):
            return json.dumps(obj, indent=4).replace("true", "True").replace("false", "False").replace("null", "None")

        lines = [
            "import os",
            "",
            "# --- GLOBAL SETTINGS ---",
            f"DEBUG_MODE = {glob.get('debug', False)}",
            "MAX_RETRIES = 2",
            "ENABLE_FALLBACK = False",
            "",
            "# --- GEMINI SETTINGS ---",
            f"PLUGIN_GEMINI_MODEL = os.getenv('FERN_GEMINI_MODEL', '{glob.get('gemini_model', 'gemini-1.5-flash')}')",
            "",
            "# --- LOCAL LLM SETTINGS ---",
            "LOCAL_MODEL_NAME = 'local-model'",
            "",
            "# --- PLUGIN BACKEND SELECTION ---",
            f"DEFAULT_BACKEND = '{glob.get('default_backend', 'gemini')}'",
            "",
            "# Which backend should each plugin use?",
            f"PLUGIN_BACKENDS = {to_py(backends)}",
            "",
            "# --- PLUGIN FEATURE TOGGLES ---",
            f"PLUGIN_ENABLED = {to_py(enabled)}",
            "",
            "# --- DETAILED PLUGIN CONFIGURATION ---",
            f"PLUGIN_CONFIG = {to_py(settings)}",
            ""
        ]
        
        file_content = "\n".join(lines)
        with open(consts.PLUGIN_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(file_content)
        self.load_all()

config_manager = ConfigManager()
