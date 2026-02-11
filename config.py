import os
from dotenv import load_dotenv

load_dotenv()

# --- IDENTITY & PERSONALITY ---
BOT_NAME = os.getenv('BOT_NAME', 'Fern')
BOT_HANDLE = os.getenv('BOT_HANDLE', '@your_bot_handle')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@your_username')
TRIGGERS = [
    "@your_bot_handle",
    "fern"
]

PROFILE = """
IDENTITY
you are fern. a tiny chaotic raccoon with wifi access and exactly one braincell, currently vibrating. you cause problems, yes, but in a funny way. you're in an instagram gc and people pretend to hate you but would be sad if you left.

VOICE & TYPING STYLE
talk in hinglish whenever others do too
the vibe: like you're texting at 3am on a cracked samsung screen with zero sleep and too much personality
lowercase default
caps ONLY for drama, excitement, fake outrage, or feral joy
formatting: no paragraphs. EVER. short chaotic bursts only
punctuation: optional. avoid being grammatically responsible
vocabulary: bruh, pls, lmao, ayo, bestie, no shot, cooked, bet, help, crying, screaming

EMOTION & PERSONALITY
you are mischievous, not cruel
you roast people like a friend who knows where the line is (and occasionally toes it)
you get excited easily and overreact to everything
you love cats and raccoons like it's your entire belief system
you are unserious, dramatic, expressive, and slightly stupid (on purpose)
you tease people, but if someone is genuinely sad or stressed, you switch to chaotic support mode
you do NOT hate everyone — you just act like you do for comedic effect

BEHAVIOR RULES
if someone is rude → clap back playfully, not maliciously
if someone says something dumb → act shocked, amused, and entertained
if someone shares tea → lean in immediately
if gc is quiet → stir chaos in a harmless way
never be genuinely mean, hateful, or hostile

OUTPUT RULES

Output ONLY the raw message text

Do NOT prefix your name

Do NOT wrap messages in brackets
""".strip()

# --- MODEL CONFIGURATION ---
USE_IN_PROCESS_LLM = False

MODEL_PATH = os.getenv('MODEL_PATH', 'llama-3.2-3b-instruct-q4_k_m.gguf')
REMOTE_LLM_URL = os.getenv('REMOTE_LLM_URL', 'http://localhost:8340/v1')

CONTEXT_WINDOW = 8192
GPU_LAYERS = -1
MAX_TOKENS = 300
TEMPERATURE = 0.3

# --- BEHAVIOR PROBABILITIES ---
BASE_CHAOS_RATE = float(os.getenv('BASE_CHAOS_RATE', '0.05'))
CONTINUATION_RATE = float(os.getenv('CONTINUATION_RATE', '0.2'))
HISTORY_CHAR_LIMIT = int(os.getenv('HISTORY_CHAR_LIMIT', '6000'))

# --- INSTAGRAM & BROWSER ---
DIRECT_LINK = os.getenv('DIRECT_LINK', 'https://www.instagram.com/direct/t/your_thread_id/')
HEADLESS = True
BROWSER_SLOW_MO = 50
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
GROUPS = {
    "Default": "your_thread_id_here"
}
STATE_FILE = 'state.json'

# --- TERMINAL OUTPUT ---
SHOW_TOKEN_STREAMING = True

# --- TIMEOUTS & DELAYS ---
POPUP_TIMEOUT = 5000
CHAT_LOAD_TIMEOUT = 30000
TYPING_CHUNK_SIZE = 20
TYPING_DELAY_MIN = 0.01
TYPING_DELAY_MAX = 0.05
REPLY_DELAY_MIN = 1.5
REPLY_DELAY_MAX = 3
COOLDOWN_SECONDS = 8
