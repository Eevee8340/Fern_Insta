import os
import asyncio
import plugins.config as plugin_config
import config
from services.tracing import tracer

# Conditional Imports
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Singleton Cache
_CLIENT_CACHE = {
    "gemini": None,
    "local": None
}

class PluginLLM:
    def __init__(self, context_name="Plugin"):
        self.context = context_name
        
        # Determine Backend
        self.backend = plugin_config.PLUGIN_BACKENDS.get(context_name, plugin_config.DEFAULT_BACKEND).lower()
        
        # Load Plugin Specific Config
        self.settings = plugin_config.PLUGIN_CONFIG.get(context_name, {})
        self.max_tokens = self.settings.get("max_tokens", config.MAX_TOKENS)
        self.temperature = self.settings.get("temperature", 0.7)
        
        self.client = None
        self.gemini_model = None
        
        # print(f"   [+] {context_name} initializing with backend: {self.backend}")

        if self.backend == "gemini":
            self._init_gemini()
        elif self.backend == "local":
            self._init_local()
        else:
            print(f"   [!] {context_name}: Unknown backend '{self.backend}', defaulting to Gemini.")
            self._init_gemini()

    def _init_gemini(self):
        global _CLIENT_CACHE
        
        if _CLIENT_CACHE["gemini"]:
            self.gemini_model = _CLIENT_CACHE["gemini"]
            return

        if not HAS_GEMINI:
            print(f"   [!] {self.context}: google-generativeai not installed.")
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(f"   [!] {self.context}: Missing GEMINI_API_KEY.")
            return
            
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                plugin_config.PLUGIN_GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens
                )
            )
            _CLIENT_CACHE["gemini"] = model
            self.gemini_model = model
            print(f"   [+] Shared Gemini Client Initialized.")
        except Exception as e:
            print(f"   [!] {self.context} Gemini Init Error: {e}")

    def _init_local(self):
        global _CLIENT_CACHE

        if _CLIENT_CACHE["local"]:
            self.client = _CLIENT_CACHE["local"]
            return

        if not HAS_OPENAI:
            print(f"   [!] {self.context}: openai package not installed (required for local backend).")
            return
            
        target_url = config.REMOTE_LLM_URL
        if config.USE_IN_PROCESS_LLM:
             print(f"   [!] {self.context}: Main bot is using In-Process LLM. Plugins might not be able to connect unless a server is also running at {target_url}.")

        try:
            client = OpenAI(
                base_url=target_url,
                api_key="sk-no-key-required"
            )
            _CLIENT_CACHE["local"] = client
            self.client = client
            print(f"   [+] Shared Local Client Initialized.")
        except Exception as e:
            print(f"   [!] {self.context} Local Client Init Error: {e}")

    async def generate(self, prompt, system_instruction=None, **kwargs):
        """
        Unified generation method with Retry Logic.
        """
        trace_id = tracer.start_trace(f"plugin_llm_{self.context}")
        tracer.log_event(trace_id, "plugin_gen_started", {"backend": self.backend})
        
        retries = plugin_config.MAX_RETRIES
        for attempt in range(retries + 1):
            try:
                result = None
                if self.backend == "gemini":
                    result = await self._generate_gemini(prompt, system_instruction)
                else:
                    result = await self._generate_local(prompt, system_instruction, **kwargs)
                
                if result is not None:
                    tracer.log_event(trace_id, "plugin_gen_completed", {"attempt": attempt})
                    tracer.end_trace(trace_id)
                    return result
                    
            except Exception as e:
                print(f"   [!] {self.context} Gen Error (Attempt {attempt+1}/{retries+1}): {e}")
                tracer.log_event(trace_id, "plugin_gen_error", {"attempt": attempt, "error": str(e)})
                if attempt == retries:
                    tracer.end_trace(trace_id)
                    return None
                await asyncio.sleep(1) # Backoff
        
        tracer.end_trace(trace_id)
        return None

    async def _generate_gemini(self, prompt, system_instruction):
        if not self.gemini_model:
            return None
            
        full_prompt = prompt
        if system_instruction:
                full_prompt = f"System Instruction: {system_instruction}\n\nUser Task: {prompt}"

        response = await asyncio.to_thread(
            self.gemini_model.generate_content, full_prompt
        )
        return response.text.strip()

    async def _generate_local(self, prompt, system_instruction, **kwargs):
        if not self.client:
            return None

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        messages.append({"role": "user", "content": prompt})

        # Handle Grammar for llama.cpp / openai-compatible servers
        extra_body = kwargs.pop("extra_body", {})
        if "grammar" in kwargs:
            grammar_content = kwargs.pop("grammar")
            extra_body["grammar"] = grammar_content

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=plugin_config.LOCAL_MODEL_NAME,
            messages=messages,
            max_tokens=self.max_tokens, 
            temperature=self.temperature,
            extra_body=extra_body,
            **kwargs
        )
        return response.choices[0].message.content.strip()
