# Fern: Advanced AI-Powered Instagram Group Chatbot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-green.svg)](https://playwright.dev/)

**Fern** is a sophisticated, production-ready Instagram automation framework designed to bring personality and utility to group chats. Built on a "split-brain" architecture, Fern separates its core automation engine from its AI "Cortex," allowing for high-performance, asynchronous interactions with minimal latency.

---

## ✨ Key Features

### 🧠 Advanced AI "Cortex"
- **Multi-Model Support:** Seamless integration with **Google Gemini 3 Flash**, **OpenRouter**, and local LLMs via **llama-cpp-python**.
- **Dynamic Personality:** Custom-tuned persona for engaging, humorous, and human-like "Hinglish" (Hindi + English) interactions.
- **Contextual Awareness:** Smart message processing that understands group dynamics and thread history.

### 📚 Intelligent Memory System
- **Long-Term Memory:** Powered by **ChromaDB** (Vector Database) to remember user facts, past conversations, and shared lore.
- **User Profiling:** Automatically builds and updates profiles for group members to personalize interactions.

### 🧩 Extensible Plugin Architecture
- **Dreamer:** Generates creative scenarios based on chat history.
- **Mimic:** Analyzes and replicates the typing styles of group members.
- **Leaderboard:** Tracks engagement and "clout" within the group.
- **Summarizer:** Provides concise recaps of missed conversations.

### 🛡️ Robust Automation & Security
- **Browser-Based Interaction:** Uses **Playwright** for reliable Instagram interaction, avoiding traditional API restrictions.
- **Secure Authentication:** Utilizes session-state persistence—your password is never stored or transmitted.
- **Rate Limiting:** Built-in token bucket throttling to ensure natural interaction speeds and account safety.

---

## 🏗️ Architecture Overview

Fern is designed with a **Split-Brain Architecture**:
1. **The Body (`insta.py`):** Handles browser automation, network observation, and message I/O.
2. **The Mind (`ai.py`):** Dedicated process for heavy LLM computations, preventing the browser from hanging during AI generation.
3. **The Interface (`web_gui.py`):** A FastAPI-powered real-time dashboard for monitoring logs, thread status, and AI performance.

---

## 🚀 Getting Started

### 📋 Prerequisites
- **Python:** 3.10 or higher.
- **Browser:** Playwright will manage its own Chromium instance.
- **API Keys:** A Gemini API key (recommended) or OpenRouter access.

### 🛠️ Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/eevee8340/fern-insta.git
   cd fern-insta
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configuration**
   - Copy `.env.example` to `.env`.
   - Update `DIRECT_LINK` with your target Instagram group thread URL.
   - Add your `GEMINI_API_KEY`.

---

## 🔑 Authentication

Fern uses a secure session-based login method:

1. **Generate Session State**
   ```bash
   python tools/login.py
   ```
2. **Log In:** A browser window will open. Manually log in to your Instagram account.
3. **Save Session:** Once your inbox is loaded, return to the terminal and press **ENTER**. This creates a `state.json` file.
   > **Note:** The bot will now use this token to log in automatically in the future.

---

## 🖥️ Usage

### Running the Full Application (Recommended)
Launch the bot alongside the Web Dashboard:
```bash
python web_gui.py
```
Access the dashboard at `http://localhost:8000`.

### Running Standalone
Run only the bot logic via terminal:
```bash
python insta.py
```

---

## ⚖️ Disclaimer
This project is for **educational and research purposes only**. Use of automated tools on Instagram may violate their Terms of Service. The developers are not responsible for any account restrictions or bans.

---

## 📜 License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
