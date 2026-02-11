import os

# Server Settings
HOST = "0.0.0.0"       # Listen on all interfaces
PORT = 8340            # Port to expose

# Model Settings
MODEL_PATH = "model.gguf"  # Place your .gguf file in the same folder or update this path
CONTEXT_WINDOW = 8192      # n_ctx (8GB VRAM can handle 8k context for 8B Q4_K_M. Reduce to 4096 if OOM occurs.)
GPU_LAYERS = -1            # n_gpu_layers (-1 = all layers to GPU). 4060 8GB can handle 100% of a 3B or 8B model.
THREADS = 4                # CPU threads (Used only for non-GPU tasks)

# Generation Defaults
MAX_TOKENS = 2048

# Advanced
# "True" allows the server to batch process requests if you have multiple users
# but might increase latency for a single user slightly.
BATCH_SIZE = 512
