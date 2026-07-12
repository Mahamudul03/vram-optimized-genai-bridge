# vram-optimized-genai-bridge
An asynchronous Telegram interface for local Stable Diffusion APIs. Features a dynamic execution-time engine using rolling averages to optimize inference steps and prevent OOM crashes on low-VRAM (4GB) hardware, alongside a regex-based inline flag parser.
# VRAM-Optimized GenAI Telegram Bridge

A production-ready, asynchronous Telegram bot interface designed to act as a lightweight middleware client for a local Stable Diffusion WebUI REST API. This architecture specializes in resource constraint handling, memory management, and dynamic execution adjustments for low-VRAM environments.

## 🚀 Key Engineering Solutions

### 1. Dynamic Execution-Time Engine
To bypass deterministic step mapping which frequently triggers Out-Of-Memory (OOM) exceptions on 4GB VRAM hardware, this system implements a rolling-average stopwatch engine. It continuously tracks hardware execution latency:
* Computes an updated coefficient of seconds-per-iteration over a moving window of recent generations.
* Dynamically scales the mathematical inference step boundaries to guarantee the hardware finishes within the targeted user time budget.
* Implements strict upper and lower execution bounds ($15 \le \text{steps} \le 45$) to safeguard resources during spikes in system activity.

### 2. Universal Inline Command Parser
Built a native string interpreter using regular expression pattern matching. It strips configuration flags directly out of raw incoming text strings and handles real-time variable overrides without breaking the natural text pipeline.
* Extracted parameters are cast to isolated execution dictionaries, decoupling global user settings from single-run overrides.

### 3. Session State Management
Maintains asynchronous context tracking for individual users. The bot maps dimension choices, specific prompt weight scaling (CFG), and baseline time allocations safely inside user data frames to prevent payload leakage between concurrent network calls.

---

## 🛠️ Architecture Overview

* **Backend Engine:** Stable Diffusion WebUI API (REST Architecture)
* **Client Framework:** Python Telegram Bot (Asynchronous / Non-blocking IO)
* **Automation:** Custom Windows Command Script Shell Launcher (`.bat`)

---

## 📖 Interface & Command Reference

### Master Chat Shortcuts
* `/menu` - Invokes the interactive graphical UI overlay for click-based time adjustments and hardware model swaps.
* `/settings` - Compiles a structured, live diagnostic view of active generation dimensions, CFG scale weights, and the current target runtime budget.
* `/aspect` - Quickly scales boundaries to aspect ratios calculated to respect low-VRAM constraints (`Portrait`, `Square`, `Landscape`).
* `/reset` - Flushes the execution time history arrays and falls back to baseline environment configurations.

### Inline Parameter Flags
Append these arguments directly to any prompt string to execute micro-adjustments at runtime:
* `--w [pixels]` : Overrides current generation width
* `--h [pixels]` : Overrides current generation height
* `--cfg [scale]` : Manually re-weights prompt guidance scale strictness
* `--time [seconds]` : Requests a temporary adjustment to the dynamic step budgeting engine
* `--steps [count]` : Static override to lock down exact generation step lengths

**Example Payload Structure:**
```text
cinematic cinematic view of a spaceship landing on Mars --w 512 --h 512 --cfg 6.5 --time 45
