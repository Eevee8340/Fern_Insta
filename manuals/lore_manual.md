# Lore Plugin Manual

The `Lore Plugin` acts as the group's "cultural archivist." It automatically identifies and records new slang, inside jokes, and significant recurring themes from chat conversations, storing them in a persistent dictionary called the `lore.json` (or "The Grimoire").

## Core Functionality

- **Autonomous Discovery:** Periodically scans recent narrative summaries (logs) to find new terms or memes.
- **Dynamic Updates:** Refines existing definitions as the group's usage of a term evolves.
- **Structured Storage:** Categories entries as "Slang," "Event," or "Inside Joke" with metadata like origin and first-seen timestamp.
- **Context Awareness:** Informs other plugins (like `Dreamer`) about the group's culture to make the bot's interactions more personalized.

## How it Works in Code

### Class: `LorePlugin`

- **`__init__(self, context)`**:
    - Initializes `PluginLLM` with the "Lore" context.
    - Loads existing lore from `lore.json`.
    - Loads its state (how many logs since the last scan) from `user_data/lore_state.json`.
- **`on_narrative_logged(self, users)`**:
    - Triggered by `EVENT_NARRATIVE_LOGGED` (fired when the `Summarizer` completes a log entry).
    - Increments a `log_counter`.
    - Once the counter reaches a threshold (default: 5), it triggers `update_lore_from_history` and resets the counter.
- **`update_lore_from_history(self)`**:
    1. **Log Retrieval**: Reads the last 10 lines from `history_logs.jsonl`.
    2. **Prompt Construction**: Sends the recent logs and a list of currently known terms to the LLM.
    3. **LLM Analysis**: Instructs the LLM to identify new terms or updates in JSON format.
    4. **Grammar Enforcement**: Uses GBNF grammar to ensure the LLM output matches the required JSON schema precisely.
    5. **Database Update**:
        - **New Entries**: Adds them to `lore_db` with timestamps and metadata.
        - **Updates**: Replaces definitions if the new one is more comprehensive (heuristic: longer definition).
    6. **Persistence**: Saves the updated dictionary to `lore.json`.
- **`log_debug_dump(...)`**: Saves failed LLM outputs to `user_data/llm_debug_failures.log` for troubleshooting JSON parsing errors.

### Data Structure (`lore.json`)

```json
{
  "yap": {
    "definition": "To talk excessively without much substance.",
    "category": "Slang",
    "origin": "Extracted from History",
    "first_seen": 1738686180.0,
    "usage_count": 1
  }
}
```

## Integration

- **Event Bus:** Subscribes to `EVENT_NARRATIVE_LOGGED`.
- **PluginLLM:** Uses the LLM to process and extract cultural data from raw text.
- **Summarizer Dependency:** Relies on the `Summarizer` plugin to generate the narrative logs it scans.

## Configuration

- `update_threshold`: Number of new logs to wait for before scanning (default: 5).
- `enabled`: Toggle in `plugin_config`.

## Key Concepts: GBNF Grammar

The plugin uses GBNF (GGML BNF) to force the LLM to output valid JSON. This is crucial because standard LLMs often add conversational filler or incorrect formatting that would break `json.loads()`.
