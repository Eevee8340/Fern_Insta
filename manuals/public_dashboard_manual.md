# Public Dashboard Plugin Manual

The `Public Dashboard Plugin` is a data synchronization and hosting utility. It periodically collects internal bot data (leaderboards, lore, and user profiles), aggregates them into a single `db.json` file, and serves that file over a built-in HTTP server. This enables external web dashboards to display real-time bot statistics and character profiles.

## Core Functionality

- **Data Aggregation:** Gathers data from multiple sources: `leaderboard.json`, `lore.json`, and individual JSON files in `user_profiles/`.
- **Built-in HTTP Server:** Starts a lightweight server on port `8856` to serve the exported data.
- **Scheduled Sync:** Automatically exports data every 60 seconds.
- **Incremental Caching:** Uses file modification times (`mtime`) to only reload and process files that have changed since the last sync, optimizing performance.
- **Data Sanitization:** Strips sensitive or internal-only fields from user profiles before exporting them to the public `db.json`.

## How it Works in Code

### Class: `PublicDashboardPlugin`

- **`__init__(self, context)`**:
    - Sets up paths for the public distribution directory (`web/public/dist/`).
    - Initializes a `cache` for leaderboard, lore, and user profiles.
    - Starts the internal HTTP server if the plugin is enabled.
- **`start_server(self)`**:
    - Launches a `socketserver.TCPServer` on port `8856`.
    - Uses `threading.Thread` to run the server in the background without blocking the bot.
- **`on_tick(self, bot)`**:
    - Triggered by `EVENT_TICK`.
    - Checks if the `sync_interval` (60s) has passed.
    - Calls `run_export` if it's time to sync.
- **`gather_data(self, bot)`**:
    - The core processing engine.
    - **Status**: Captures bot state (is_sleeping, msg_count).
    - **Leaderboard/Lore**: Uses `_load_if_modified` to efficiently read the main JSON files.
    - **Profiles**: Iterates through `user_profiles/*.json`, sanitizes the content (keeping only public fields like `handle`, `title`, `quote`, etc.), and merges message counts from the leaderboard.
- **`on_local_command(self, command)`**:
    - Handles `/force_export` to manually trigger an immediate data sync.

### Integration

- **Event Bus:** Subscribes to `EVENT_TICK` (Priority 10) and `EVENT_LOCAL_COMMAND`.
- **Filesystem:** Writes to `web/public/dist/db.json`.

## Served Endpoint

Once the plugin is running, the aggregated database is available at:
`http://localhost:8856/db.json`

## Configuration

- `sync_interval`: How often to export data (default: 60 seconds).
- `enabled`: Toggle in `plugin_config`.

## Commands

| Command | Action |
| :--- | :--- |
| `/force_export` | Immediately re-scans all files and updates `db.json`. |

## Performance Optimization: Smart Caching

To avoid reading dozens of JSON files on every tick, the plugin maintains a cache of the file contents and their last modification timestamps. 
1. If `os.path.getmtime(file)` is the same as the cached value, it uses the data from memory.
2. If the file has changed, it re-reads, re-sanitizes, and updates the cache.
This ensures the `Public Dashboard` has minimal impact on the bot's CPU and disk usage.
