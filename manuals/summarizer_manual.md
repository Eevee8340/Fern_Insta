# Summarizer (Archivist) Plugin Manual

The `Summarizer Plugin`, also known as the "Archivist," is a foundational component of Fern's long-term memory system. It transforms raw, voluminous chat history into structured "Narrative logs" that are easier for the AI to retrieve and understand over time.

## Core Functionality

- **Batch Processing:** Collects raw messages into a buffer and summarizes them in batches (default: 50 messages).
- **Structured Extraction:** Uses an LLM to extract specific data points: `Topics`, `User States`, `New Facts`, and `Key Events`.
- **Narrative Persistence:** Appends structured summaries to a permanent `history_logs.jsonl` file.
- **RAG Integration:** Indexes the generated summaries into the bot's memory database for future Retrieval-Augmented Generation.
- **Dynamic Learning:** Emits events for other plugins (like `Profiler` and `Lore`) once a summary is completed, allowing them to update based on high-level narrative shifts.
- **Batch Analysis:** Collects multiple narrative logs (5 at a time) and sends them to the `cortex` for deep thematic analysis.

## How it Works in Code

### Class: `SummarizerPlugin`

- **`__init__(self, context)`**:
    - Initializes the `archive_buffer` (raw messages) and `summary_queue` (narrative summaries).
    - Loads state from `user_data/summarizer_state.json`.
- **`on_chat_message(self, sender, text, bubble)`**:
    - Triggered by `EVENT_CHAT_MESSAGE`.
    - Appends every message to the `archive_buffer`.
    - If the buffer size reaches `batch_size` (50), it triggers `process_batch` in a background task.
- **`process_batch(self, force)`**:
    1. **Data Preparation**: Extracts the messages to be summarized.
    2. **Prompting**: Instructs the LLM to act as an "Intelligence Officer," extracting structured data with specific headers (`[TOPICS]`, `[USER_STATE]`, `[NEW_FACTS]`, `[KEY_EVENTS]`).
    3. **History Logging**: Writes the summary to `history_logs.jsonl` with timestamps and metadata.
    4. **Memory Indexing**: Calls `cortex.add_memory` to make the summary searchable.
    5. **Event Emission**: Scans the summary for known user handles and emits `EVENT_NARRATIVE_LOGGED` for those users.
    6. **Deep Analysis**: Adds the summary to `summary_queue`. If the queue reaches 5 items, it calls `cortex.analyze_batch` to synthesize long-term themes.
- **`on_local_command(self, command)`**:
    - Handles `/recap` and `/force_summary` for manual activation.
    - Handles `/clearmem`, which wipes both the raw buffer and the summary queue.

### Data Storage

- **Structured Logs**: `user_data/history_logs.jsonl` (JSON per line).
- **Internal State**: `user_data/summarizer_state.json`.

## Summary Report Format

The LLM is instructed to use this exact format:
```text
[TOPICS]: gaming, weekend plans
[USER_STATE]: Alice is excited, Bob is tired
[NEW_FACTS]: 
- Alice started playing "Elden Ring".
- Bob moved to a new apartment.
[KEY_EVENTS]: 
- The group scheduled a session for Saturday.
```

## Configuration

- `batch_size`: Messages to collect before summarizing (default: 50).
- `enabled`: Toggle in `plugin_config`.

## Commands

| Command | Action |
| :--- | :--- |
| `/fern recap` | Immediately summarizes the current message buffer. |
| `/fern clearmem` | Wipes the buffer and the AI's active memory. |
