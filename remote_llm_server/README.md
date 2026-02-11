# Remote LLM Server (Linux/NVIDIA)

This package contains everything needed to run an OpenAI-compatible LLM API server on a remote Linux machine with an NVIDIA GPU.

## 1. Setup

### Prerequisites
- Python 3.10 or higher
- NVIDIA Drivers & CUDA Toolkit installed (verify with `nvidia-smi`)

### Installation
1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **IMPORTANT: Install with CUDA Support**
   You must compile `llama-cpp-python` with CUDA enabled. Run this exact command:
   ```bash
   CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python[server]
   ```

3. Install remaining requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy your Model**
   - Copy your `.gguf` model file (e.g., `llama-3.2-3b-instruct-q4_k_m.gguf`) into this folder.
   - Rename it to `model.gguf` OR update `config.py` with the correct filename.

## 2. Configuration (`config.py`)
- **HOST**: Default `0.0.0.0` (Exposes to local network).
- **PORT**: Default `8000`.
- **GPU_LAYERS**: `-1` offloads everything to GPU.

## 3. Running (Development)
Run the start script directly:
```bash
chmod +x start.sh
./start.sh
```

## 4. Running (Production / Keep-Alive)
To keep the server running in the background and automatically restart on crashes:
```bash
chmod +x keep_alive.sh
nohup ./keep_alive.sh &
```
- **Logs**: Output is saved to `server_output.log`. Crashes are logged to `server_crash.log`.
- **Stop**: Run `pkill -f keep_alive.sh` to stop the monitor.

## 5. Connecting Fern
On your main machine, update `config.py`:
```python
USE_IN_PROCESS_LLM = False
REMOTE_LLM_URL = "http://<REMOTE_IP_ADDRESS>:8000/v1"
```
