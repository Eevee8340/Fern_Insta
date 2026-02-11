import llama_cpp
print(f"llama-cpp-python version: {llama_cpp.__version__}")
try:
    from llama_cpp import Llama
    print("Llama class imported successfully")
except ImportError as e:
    print(f"Import Error: {e}")
