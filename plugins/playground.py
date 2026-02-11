import asyncio
from typing import Any
import consts
from services.event_bus import event_bus
from web.backend.api import manager

class PlaygroundPlugin:
    def __init__(self, context):
        self.ctx = context

    async def on_playground_message(self, sender: str, text: str):
        # 1. Broadcast User Message to Playground UI
        await manager.broadcast({
            "type": "playground_message",
            "sender": sender,
            "text": text,
            "role": "user"
        })

        cortex = self.ctx.get_cortex()
        if not cortex:
            await manager.broadcast({
                "type": "playground_message",
                "sender": "System",
                "text": "Error: Cortex is not connected or initialized.",
                "role": "system"
            })
            return

        # 2. Ask Cortex to Generate
        try:
            # Broadcast Typing Started
            await manager.broadcast({
                "type": "typing_status",
                "is_typing": True,
                "sender": "Fern"
            })

            # We use the main cortex generation logic to test the actual personality/memory
            token_stream = await cortex.generate(sender, text)
            
            full_text = ""
            
            # 3. Stream Response
            async for token in token_stream:
                if token:
                    full_text += token
                    # Broadcast Token Chunk
                    await manager.broadcast({
                        "type": "playground_stream",
                        "content": token,
                        "sender": "Fern"
                    })
            
            # Broadcast Typing Stopped
            await manager.broadcast({
                "type": "typing_status",
                "is_typing": False,
                "sender": "Fern"
            })

            # 4. Broadcast Bot Message to Playground UI (Final Record)
            await manager.broadcast({
                "type": "playground_message",
                "sender": "Fern",
                "text": full_text,
                "role": "assistant"
            })
            
        except Exception as e:
            print(f"   [Playground] Generation Error: {e}")
            await manager.broadcast({
                "type": "typing_status",
                "is_typing": False,
                "sender": "Fern"
            })
            await manager.broadcast({
                "type": "playground_message",
                "sender": "System",
                "text": f"Generation Error: {str(e)}",
                "role": "system"
            })

    async def on_cortex_meta(self, meta: dict):
        """Broadcast debug metadata to the playground."""
        await manager.broadcast({
            "type": "playground_debug",
            "tps": meta.get("tps"),
            "mem_usage": meta.get("mem_usage"),
            "prompt_log": meta.get("prompt_log"),
            "rag_info": meta.get("rag_info")
        })

def register(ctx):
    p = PlaygroundPlugin(ctx)
    event_bus.subscribe(consts.EVENT_PLAYGROUND_MESSAGE, p.on_playground_message)
    event_bus.subscribe("cortex_meta", p.on_cortex_meta)
