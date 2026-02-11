# Playground Plugin Manual

The `Playground Plugin` acts as a communication bridge between the Fern bot's core logic and the web-based interactive "Playground" UI. It allows developers and administrators to test the bot's persona, memory retrieval, and generation speed in a real-time, isolated environment.

## Core Functionality

- **WebSocket Integration:** Uses the `manager` from the web backend to broadcast messages and status updates to connected browser clients.
- **Real-time Streaming:** Chunks tokens from the `cortex` and sends them immediately to the UI, providing a "typing" effect.
- **Debug Metadata:** Collects and transmits internal metrics like Tokens Per Second (TPS), memory usage, and RAG (Retrieval-Augmented Generation) context.
- **State Synchronization:** Informs the UI when the bot starts and stops "typing."

## How it Works in Code

### Class: `PlaygroundPlugin`

- **`on_playground_message(self, sender, text)`**:
    - Triggered by `EVENT_PLAYGROUND_MESSAGE`.
    - **UI Update**: Immediately broadcasts the user's message to the playground UI.
    - **Typing Indicator**: Sends a `typing_status` (True) to show the bot is thinking.
    - **Generation**: Calls `cortex.generate(sender, text)` to get an asynchronous token stream.
    - **Streaming**: Iterates through the `token_stream` and broadcasts each chunk via `playground_stream`.
    - **Finalization**: Sends the complete message as a `playground_message` (assistant role) and clears the typing status.
- **`on_cortex_meta(self, meta)`**:
    - Listens for a custom `cortex_meta` event.
    - Broadcasts technical details to the UI's debug panel:
        - `tps`: Generation speed.
        - `mem_usage`: System memory consumption.
        - `prompt_log`: The exact prompt sent to the LLM (useful for verifying persona injection).
        - `rag_info`: Details on which memories were retrieved during the generation process.

### Integration

- **Event Bus:** Subscribes to `EVENT_PLAYGROUND_MESSAGE` and `cortex_meta`.
- **Web Backend:** Imports `manager` from `web.backend.api` to handle the WebSocket communication.
- **Cortex:** Directly interacts with the `cortex` service's generation and stream methods.

## Data Schema (WebSocket Events)

| Type | Description | Key Fields |
| :--- | :--- | :--- |
| `playground_message` | A permanent message record. | `text`, `role`, `sender` |
| `playground_stream` | A single token chunk. | `content` |
| `typing_status` | Toggle for typing indicator. | `is_typing` |
| `playground_debug` | Performance and log data. | `tps`, `prompt_log`, `rag_info` |

## Use Cases

1. **Persona Testing:** Verify how a new "Clone" or "Lore" entry affects the bot's output.
2. **Performance Monitoring:** Check if the local LLM is running at acceptable speeds.
3. **Context Verification:** See exactly what information the bot is pulling from its memory database before it answers.
