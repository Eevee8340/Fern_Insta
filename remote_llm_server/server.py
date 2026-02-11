import os
import sys
import subprocess
import config

def main():
    print("--- Remote LLM Server Launcher ---")
    print(f"Target: {config.HOST}:{config.PORT}")
    print(f"Model:  {config.MODEL_PATH}")
    print(f"GPU:    {'ALL LAYERS' if config.GPU_LAYERS == -1 else config.GPU_LAYERS}")
    
    if not os.path.exists(config.MODEL_PATH):
        print(f"\n[ERROR] Model file not found at: {config.MODEL_PATH}")
        print("Please copy your .gguf file into this folder or update config.py")
        sys.exit(1)

    # Construct the command for llama-cpp-python server
    cmd = [
        sys.executable, "-m", "llama_cpp.server",
        "--host", config.HOST,
        "--port", str(config.PORT),
        "--model", config.MODEL_PATH,
        "--n_ctx", str(config.CONTEXT_WINDOW),
        "--n_gpu_layers", str(config.GPU_LAYERS),
        "--n_threads", str(config.THREADS),
        "--n_batch", str(config.BATCH_SIZE)
    ]

    print("\n[+] Launching Server...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n[!] Server stopped by user.")
    except Exception as e:
        print(f"\n[!] Server crashed: {e}")

if __name__ == "__main__":
    main()

