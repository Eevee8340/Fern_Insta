import os

# --- PATHS ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.py")
PLUGIN_CONFIG_PATH = os.path.join(ROOT_DIR, "plugins", "config.py")
MEMORY_DB_PATH = os.path.join(ROOT_DIR, "fern_memory_db")
USER_DATA_DIR = os.path.join(ROOT_DIR, "user_data")
USER_PROFILES_DIR = os.path.join(ROOT_DIR, "user_profiles")
BACKUPS_DIR = os.path.join(ROOT_DIR, "backups")
HISTORY_LOGS_PATH = os.path.join(USER_DATA_DIR, "history_logs.jsonl")

# --- BACKENDS ---
BACKEND_GEMINI = "gemini"
BACKEND_LOCAL = "local"

# --- IPC MESSAGE TYPES ---
IPC_SHUTDOWN = "shutdown"
IPC_GENERATE = "generate_response"
IPC_ENGAGEMENT = "analyze_engagement"
IPC_ADD_MEMORY = "add_memory"
IPC_ANALYZE_BATCH = "analyze_batch"
IPC_GET_RANDOM_MEMS = "get_random_mems"
IPC_GET_RANDOM_LOGS = "get_random_logs"
IPC_GET_HISTORY_STATS = "get_history_stats"
IPC_GET_CHAT_HISTORY = "get_chat_history"
IPC_GET_ALL_MEMORIES = "get_all_memories"
IPC_GET_MEMORY_GRAPH = "get_memory_graph"
IPC_GET_FACTS_BY_USER = "get_facts_by_user"
IPC_DELETE_MEMORY = "delete_memory"
IPC_UPDATE_HISTORY = "update_history"
IPC_COMMAND = "command"
IPC_HEARTBEAT = "heartbeat"

# --- IPC RESPONSE TYPES ---
IPC_INIT_COMPLETE = "init_complete"
IPC_TOKEN = "token"
IPC_GEN_COMPLETE = "generation_complete"
IPC_ENGAGEMENT_RESULT = "engagement_result"
IPC_DATA_RESPONSE = "data_response"
IPC_META = "meta"
IPC_HEARTBEAT_ACK = "heartbeat_ack"
IPC_TRACE_EVENT = "trace_event"
IPC_ERROR = "error"

# --- EVENT NAMES ---
EVENT_CHAT_MESSAGE = "on_chat_message"
EVENT_TICK = "on_tick"
EVENT_LOCAL_COMMAND = "on_local_command"
EVENT_ERROR = "on_error"
EVENT_SYSTEM_START = "on_system_start"
EVENT_PLAYGROUND_MESSAGE = "on_playground_message"
EVENT_NARRATIVE_LOGGED = "on_narrative_logged"
EVENT_USER_UPDATE = "on_user_update"

# --- ADMIN INFO ---
ADMIN_THREAD_ID = "your_admin_thread_id_here"

# --- LOG LEVELS ---
LOG_INFO = "INFO"
LOG_WARNING = "WARNING"
LOG_ERROR = "ERROR"
LOG_DEBUG = "DEBUG"
