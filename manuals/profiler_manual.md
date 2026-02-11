# Profiler Plugin Manual

The `Profiler Plugin` is responsible for building and maintaining a deep understanding of every user in the chat. It constructs "User Profiles" that store titles, personality traits, relationship dynamics, and iconic quotes. It acts as the bot's "social brain," helping it understand who is who and how they relate to each other.

## Core Functionality

- **Persona Construction:** Generates structured profiles including `title`, `traits`, and a unique `fern_thought` (the bot's internal opinion of the user).
- **Relationship Mapping:** Tracks how users interact with each other (e.g., identifying rivals, besties, or group dynamics).
- **Golden Quote Extraction:** Scans raw chat logs once a day to find the most "iconic" verbatim quote for active users.
- **Narrative-Driven Updates:** Automatically patches user profiles after every 20 narrative log entries involving that user.
- **Peer Perspective Integration:** When updating a user's profile, it looks at what *other* users think of them to ensure social consistency.

## How it Works in Code

### Class: `ProfilerPlugin`

- **`__init__(self, context)`**:
    - Initializes directories and `PluginLLM`.
    - Loads state from `user_data/profiler_state.json` (tracking active users and reset times).
- **`on_narrative_logged(self, users)`**:
    - Triggered by `EVENT_NARRATIVE_LOGGED`.
    - Increments a per-user narrative count.
    - If a user reaches the `narrative_threshold` (20), it triggers `update_narrative_profile` in the background.
- **`on_chat_message(self, sender, text, bubble)`**:
    - Tracks "active users" for the daily quote reset.
    - Triggers `check_quote_resets` to see if it's 09:00 AM and a daily refresh is needed.
- **`update_narrative_profile(self, handle)`**:
    1. **Context Gathering**: Fetches recent narrative logs mentioning the user, long-term "facts" from the `cortex`, and peer perspectives (what others think of this handle).
    2. **Prompting**: Asks the LLM to generate a "JSON Patch" with updated titles, traits, and relationships.
    3. **Conservative Editing**: The prompt instructs the LLM to only change fields if there is a major shift, ensuring profile stability.
- **`update_quote_profile(self, handle)`**:
    - Reads the last 100 raw chat lines for a specific user.
    - Asks the LLM to select ONE verbatim line that is "funny, iconic, or defines their personality."
- **`update_profile(self, handle, new_data)`**:
    - Performs a partial merge (patch) of the new LLM data into the existing JSON profile in `user_profiles/`.
    - Automatically updates aliases from the `AliasManager`.

### Data Structure (`user_profiles/@user.json`)

```json
{
  "handle": "@user",
  "aliases": ["UserNickname"],
  "title": "The Silent Observer",
  "traits": ["Sarcastic", "Tech-savvy"],
  "quote": "i think the server is on fire again lol",
  "relationships": {
    "@friend": "Reliable Ally",
    "@rival": "Constant Debater"
  },
  "fern_thought": "They seem to know a lot about the backend but never actually fix anything.",
  "last_updated": 1738686180.0
}
```

## Integration

- **Event Bus:** Subscribes to `EVENT_NARRATIVE_LOGGED` and `EVENT_CHAT_MESSAGE`.
- **Cortex:** Retrieves long-term "Facts" to validate personality traits.
- **Alias Manager:** Syncs user nicknames with their profile handles.
- **Summarizer Dependency:** Relies on narrative logs to understand high-level user behavior.

## Configuration

- `narrative_threshold`: Number of logs before a profile update (default: 20).
- `enabled`: Toggle in `plugin_config`.

## The "Fern Thought"

The `fern_thought` field is a unique part of the profile. It is explicitly designed as the bot's private monologue. This field is *not* shown to users in normal interaction but informs the bot's "inner voice" when generating replies, allowing for more consistent and opinionated responses.
