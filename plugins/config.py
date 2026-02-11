import os

# --- GLOBAL SETTINGS ---
DEBUG_MODE = False
MAX_RETRIES = 2
ENABLE_FALLBACK = False

# --- GEMINI SETTINGS ---
PLUGIN_GEMINI_MODEL = os.getenv('FERN_GEMINI_MODEL', 'gemini-3-flash-preview')

# --- LOCAL LLM SETTINGS ---
LOCAL_MODEL_NAME = 'local-model'

# --- PLUGIN BACKEND SELECTION ---
DEFAULT_BACKEND = 'gemini'

# Which backend should each plugin use?
PLUGIN_BACKENDS = {
    "Dreamer": "gemini",
    "Mimic": "gemini",
    "Profiler": "local",
    "Archivist": "local",
    "Lore": "local",
    "Migrator": "local"
}

# --- PLUGIN FEATURE TOGGLES ---
PLUGIN_ENABLED = {
    "Dreamer": True,
    "Mimic": True,
    "Profiler": True,
    "Archivist": True,
    "Lore": True,
    "PublicDashboard": True
}

# --- DETAILED PLUGIN CONFIGURATION ---
PLUGIN_CONFIG = {
    "Lore": {
        "temperature": 0.3,
        "max_tokens": 2000
    },
    "Dreamer": {
        "interval": 1800,
        "temperature": 0.7,
        "max_tokens": 1000,
        "memory_seeds": 3,
        "night_buffer_size": 20,
        "trigger_commands": [
            "/dream",
            "/force_dream"
        ]
    },
    "Mimic": {
        "temperature": 0.1,
        "max_tokens": 2000,
        "sample_lines": 200,
        "ignored_senders": [
            "system",
            "admin"
        ],
        "trigger_commands": [
            "/clone",
            "/unclone"
        ]
    },
    "Profiler": {
        "cooldown": 86400,
        "history_limit": 50,
        "temperature": 0.4,
        "max_tokens": 1000
    },
    "Archivist": {
        "batch_size": 50,
        "temperature": 0.2,
        "max_tokens": 2000,
        "trigger_commands": [
            "/recap",
            "/force_summary",
            "/clearmem"
        ]
    }
}
