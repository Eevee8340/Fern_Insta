import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from llama_cpp import Llama
import config
import os
import sys

# Initialize FastAPI
app = FastAPI(title="Fern Custom LLM Server")

# Global Model Variable
llm: Optional[Llama] = None

# Pydantic Models for OpenAI Compatibility
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "local-model"
    messages: List[Message]
    max_tokens: Optional[int] = config.MAX_TOKENS
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None

@app.on_event("startup")
def startup_event():
    global llm
    print(f"Loading Model: {config.MODEL_PATH}")
    
    if not os.path.exists(config.MODEL_PATH):
        print(f"FATAL: Model not found at {config.MODEL_PATH}")
        sys.exit(1)
        
    try:
        llm = Llama(
            model_path=config.MODEL_PATH,
            n_gpu_layers=config.GPU_LAYERS,
            n_ctx=config.CONTEXT_WINDOW,
            n_batch=config.BATCH_SIZE,
            n_threads=config.THREADS,
            verbose=True
        )
        print("Model Loaded Successfully!")
    except Exception as e:
        print(f"Failed to load model: {e}")
        sys.exit(1)

@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    if not llm:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Convert Pydantic messages to list of dicts for llama-cpp
    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        response = llm.create_chat_completion(
            messages=messages_payload,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stream=request.stream,
            stop=request.stop
        )
        return response
    except Exception as e:
        print(f"Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host=config.HOST, 
        port=config.PORT
    )
