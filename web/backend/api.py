from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import asyncio
import base64
import os
import sys
import json
import logging
import uuid
import time
import consts
import re
from services.config_manager import config_manager
from services.event_bus import event_bus
from services.memory_graph import memory_graph_service
from services.tracing import tracer

# Add root to path so we can import insta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import config

app = FastAPI()

# --- ASSET PATH CONFIG ---
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "dist"))
ASSETS_DIR = os.path.join(DIST_DIR, "assets")
AVATARS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "user_data", "avatars"))

# Mount Assets if they exist
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    print(f"WARNING: Assets not found at {ASSETS_DIR}")

# Mount Avatars
if not os.path.exists(AVATARS_DIR):
    os.makedirs(AVATARS_DIR)

# Custom endpoint for Avatars with aggressive caching
@app.get("/avatars/{filename}")
async def serve_avatar(filename: str):
    file_path = os.path.join(AVATARS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(
            file_path, 
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000, immutable"}
        )
    return Response(status_code=404)

# --- LOG FILTER MIDDLEWARE ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class AccessLogFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/screenshot" and response.status_code == 200:
             pass
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Bot Reference (injected by launcher)
bot_instance = None

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    @property
    def has_active_connections(self) -> bool:
        return len(self.active_connections) > 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    async def shutdown(self):
        """Close all connections on server shutdown."""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except: pass
        self.active_connections = []

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if bot_instance:
                    # Handle incoming commands from WS
                    if msg.get("type") == "command":
                        await bot_instance.command_queue.put(msg.get("text"))
            except: pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- REST ENDPOINTS ---

@app.get("/status")
async def get_status():
    if not bot_instance:
        return {"error": "Bot not initialized"}
    
    # Use cached data + request stats from Cortex
    try:
        stats = {}
        if bot_instance.cortex:
            stats = await bot_instance.cortex.ask_data(consts.IPC_GET_HISTORY_STATS)
    except:
        stats = {}
        
    # Reverse lookup thread name
    current_thread_name = "Unknown"
    
    if hasattr(bot_instance, "browser_mgr") and bot_instance.browser_mgr and hasattr(bot_instance.browser_mgr, "current_url"):
        url = bot_instance.browser_mgr.current_url
        # URL format: https://www.instagram.com/direct/t/{thread_id}/
        if "/direct/t/" in url:
            try:
                # Extract ID: split by '/direct/t/' take the second part, then split by '/' and take the first part
                thread_id_part = url.split("/direct/t/")[1].split("/")[0]
                
                # Find name in GROUPS
                for name, tid in getattr(config, "GROUPS", {}).items():
                    if str(tid) == str(thread_id_part):
                        current_thread_name = name
                        break
            except Exception:
                pass # Fallback to Unknown if parsing fails
    
    # Determine Persona
    persona_name = getattr(config, "BOT_NAME", "Fern")
    system_prompt = getattr(config, "PROFILE", "")
    
    if hasattr(bot_instance, "mimic_plugin") and bot_instance.mimic_plugin:
        active_clone = bot_instance.mimic_plugin.active_clone
        if active_clone:
            persona_name = active_clone
            system_prompt = bot_instance.mimic_plugin.clones.get(active_clone, system_prompt)

    # Get Last Sender Info
    last_sender_handle = bot_instance.last_left_sender or "Unknown"
    
    # improved handle extraction (consistent with Profiler)
    handle = last_sender_handle
    # 1. Try to find (@handle)
    match = re.search(r"\(@(.*?)\)", last_sender_handle)
    if match:
        handle = match.group(1)
    else:
        # 2. Split by "replied to"
        handle = re.split(r"(\s+replied\s+to|\s+\(replied\s+to)", last_sender_handle, flags=re.IGNORECASE)[0].strip()
    
    # 3. Sanitize (remove path chars if any, just in case)
    if "user_data" in handle or "\\" in handle or "/" in handle:
        handle = os.path.basename(handle).replace(".txt", "").replace(".json", "")

    safe_handle = "".join([c for c in handle if c.isalnum() or c in "._-"])
    
    last_sender_profile = {}
    profile_path = os.path.join(consts.USER_PROFILES_DIR, f"{safe_handle}.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                last_sender_profile = json.load(f)
        except: pass

    return {
        "is_sleeping": bot_instance.is_sleeping,
        "is_busy": bot_instance.is_busy,
        "is_typing": getattr(bot_instance, "is_typing", False), # Future proofing
        "last_sender": bot_instance.last_left_sender,
        "last_sender_pfp": last_sender_profile.get("pfp_url"),
        "last_sender_title": last_sender_profile.get("title", last_sender_profile.get("archetype", "Unknown")),
        "context_limit": config.CONTEXT_WINDOW,
        "tps": bot_instance.last_tps if hasattr(bot_instance, "last_tps") else 0.0,
        "mem": stats.get("mem_usage") if stats and stats.get("mem_usage") != "0/0" else (bot_instance.last_mem if hasattr(bot_instance, "last_mem") else "0/0"),
        "msg_count": stats.get("msg_count", 0) if stats else 0,
        "thread_name": current_thread_name,
        "persona_name": persona_name,
        "system_prompt": system_prompt
    }

@app.post("/command")
async def send_command(command: dict):
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not ready")
    
    cmd_text = command.get("text")
    if cmd_text:
        await bot_instance.command_queue.put(cmd_text)
        return {"status": "queued", "command": cmd_text}
    return {"error": "empty command"}

@app.get("/chat/history")
async def get_chat_history():
    if not bot_instance:
        return {"messages": []}
    return {"messages": bot_instance.message_history}

@app.get("/context")
async def get_context():
    if not bot_instance:
        return {"context": "", "rag": {}}
    
    # Use cached context from last meta update
    ctx_text = ""
    rag_data = {}
    
    if hasattr(bot_instance, "last_context"):
        ctx_text = bot_instance.last_context
        
    if hasattr(bot_instance, "last_rag_info"):
        rag_data = bot_instance.last_rag_info.copy() if bot_instance.last_rag_info else {}
        
    # Ensure system prompt is always present
    if not rag_data.get("system"):
        rag_data["system"] = getattr(config, "PROFILE", "")
        
    return {"context": ctx_text, "rag": rag_data}

@app.get("/memories")
async def get_memories():
    if not bot_instance or not bot_instance.cortex:
        return {"memories": []}
    
    # Fetch from Cortex IPC
    try:
        data = await bot_instance.cortex.ask_data(consts.IPC_GET_ALL_MEMORIES)
        if data and "memories" in data:
            return {"memories": data["memories"]}
    except Exception as e:
        return {"error": str(e)}
    
    return {"memories": []}

@app.get("/memories/graph")
async def get_memory_graph():
    if not bot_instance or not bot_instance.cortex:
        return {"nodes": [], "links": []}
    
    try:
        raw_data = await bot_instance.cortex.ask_data(consts.IPC_GET_MEMORY_GRAPH)
        if not raw_data:
            return {"nodes": [], "links": []}
        return memory_graph_service.process_graph_data(raw_data)
    except Exception as e:
        return {"error": str(e)}

@app.delete("/memories/{mem_id}")
async def delete_memory(mem_id: str):
    if not bot_instance or not bot_instance.cortex:
        raise HTTPException(status_code=503, detail="Bot not ready")
    
    bot_instance.cortex.send_command(consts.IPC_DELETE_MEMORY, {"mem_id": mem_id})
    return {"status": "queued"}

# --- CLONE ENDPOINTS ---
@app.get("/clones")
def get_clones():
    if not bot_instance or not hasattr(bot_instance, "mimic_plugin"):
        return {"clones": [], "active": None}
    
    if hasattr(bot_instance, "mimic_plugin"):
        plugin = bot_instance.mimic_plugin
        clones_list = []
        
        for handle in plugin.clones.keys():
            # Get PFP
            safe_handle = "".join([c for c in handle.replace("@", "") if c.isalnum() or c in "._-"])
            pfp_url = None
            try:
                p_path = os.path.join(consts.USER_PROFILES_DIR, f"{safe_handle}.json")
                if os.path.exists(p_path):
                    with open(p_path, "r", encoding="utf-8") as f:
                        p = json.load(f)
                        pfp_url = p.get("pfp_url")
            except: pass
            
            clones_list.append({
                "handle": handle,
                "pfp_url": pfp_url
            })

        return {
            "clones": clones_list,
            "active": plugin.active_clone,
            "prompts": plugin.clones
        }
    
    return {"clones": [], "active": None, "error": "Mimic plugin not loaded"}

@app.post("/clones/activate")
async def activate_clone(data: dict):
    if not bot_instance or not hasattr(bot_instance, "mimic_plugin"):
        raise HTTPException(status_code=503, detail="Mimic Plugin not loaded")
    
    target = data.get("handle")
    await bot_instance.mimic_plugin.activate_clone(bot_instance, target)
    return {"status": "activated", "target": target}

@app.post("/clones/reset")
async def reset_clone():
    if not bot_instance or not hasattr(bot_instance, "mimic_plugin"):
        raise HTTPException(status_code=503, detail="Mimic Plugin not loaded")
    
    await bot_instance.mimic_plugin.restore_original(bot_instance)
    return {"status": "reset"}

@app.delete("/clones/{handle}")
def delete_clone(handle: str):
    if not bot_instance or not hasattr(bot_instance, "mimic_plugin"):
        raise HTTPException(status_code=503, detail="Mimic Plugin not loaded")
    
    plugin = bot_instance.mimic_plugin
    if handle in plugin.clones:
        del plugin.clones[handle]
        plugin.save_clones()
        return {"status": "deleted", "handle": handle}
    
    return {"error": "Clone not found"}

@app.get("/profiles/lite")
def get_profiles_lite():
    """Returns a lightweight list of profiles for dropdowns."""
    profiles = []
    if not os.path.exists(consts.USER_PROFILES_DIR):
        return {"profiles": []}

    for filename in os.listdir(consts.USER_PROFILES_DIR):
        if filename.endswith(".json"):
            try:
                path = os.path.join(consts.USER_PROFILES_DIR, filename)
                with open(path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                    profiles.append({
                        "handle": p.get("handle", filename.replace(".json", "")),
                        "name": p.get("title", "Unknown"),
                        "pfp_url": p.get("pfp_url")
                    })
            except: pass
            
    # Sort by handle
    profiles.sort(key=lambda x: x["handle"])
    return {"profiles": profiles}


# --- PLAYGROUND ENDPOINTS ---

@app.post("/playground/message")
async def playground_message(data: dict):
    """Simulate an incoming message for testing."""
    sender = data.get("sender", "TestUser")
    text = data.get("text", "")
    
    if not bot_instance:
        return {"error": "Bot not running"}
        
    await event_bus.emit(consts.EVENT_PLAYGROUND_MESSAGE, sender, text)
    
    return {"status": "processed"}

# --- CONFIG ENDPOINTS ---

@app.get("/config/json")
def get_config_json():
    return config_manager.get_main_config_structured()

@app.post("/config/json")
async def save_config_json(data: dict):
    try:
        config_manager.save_main_config(data)
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/config/plugins/json")
def get_plugin_config_json():
    return config_manager.plugin_config

@app.post("/config/plugins/json")
async def save_plugin_config_json(data: dict):
    try:
        config_manager.save_plugin_config(data)
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/config")
def get_config_raw():
    try:
        with open(consts.CONFIG_PATH, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/config")
async def save_config_raw(data: dict):
    content = data.get("content")
    if not content: return {"error": "Empty content"}
    try:
        with open(consts.CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/restart")
async def restart_server():
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not ready")
    
    # Trigger shutdown
    if bot_instance:
        await bot_instance.shutdown()
    
    # Restart
    print("Restarting system...")
    os.execv(sys.executable, ['python'] + sys.argv)
    
@app.post("/browser/restart")
def restart_browser():
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not ready")
    
    # Queue restart command
    asyncio.run_coroutine_threadsafe(
        bot_instance.command_queue.put("/restart_browser"), 
        bot_instance.loop
    )
    return {"status": "restarting_browser"}

@app.get("/groups")
def get_groups():
    return {"groups": getattr(config, "GROUPS", {})}

@app.post("/groups/switch")
async def switch_group(data: dict):
    if not bot_instance:
         raise HTTPException(status_code=503, detail="Bot not ready")
    
    thread_id = data.get("thread_id")
    if not thread_id:
        return {"error": "Missing thread_id"}
    
    await bot_instance.command_queue.put(f"/switch_thread {thread_id}")
    return {"status": "switching", "thread_id": thread_id}

@app.get("/logs")
def get_logs():
    if not bot_instance:
        return {"logs": []}
    return {"logs": bot_instance.log_history}

@app.get("/traces")
def get_traces():
    return {"traces": tracer.get_history()}

@app.get("/screenshot")
async def get_screenshot():
    if not bot_instance:
        return Response(content=b"", media_type="image/jpeg")
    
    if bot_instance.latest_screenshot:
        return Response(content=bot_instance.latest_screenshot, media_type="image/jpeg")
    
    return Response(content=b"", media_type="image/jpeg")

# --- SPA STATIC SERVING (CATCH-ALL) ---

# Serve index.html for root and SPA routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if a specific file was requested in public/ or dist/
    potential_file = os.path.join(DIST_DIR, full_path)
    if os.path.isfile(potential_file):
            return FileResponse(potential_file)
            
    # Default to index.html for SPA routing
    index_file = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "UI not built"}