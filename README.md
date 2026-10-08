# 🚀 Roblox Chat Macro

A dedicated, non-intrusive desktop macro program designed for Roblox players. It lets you chat a sequence of multiple custom messages in rapid succession with millisecond/second interval precision, custom global keybinds, an Always-On-Top window pin, and an intelligent **Roblox Spam Limit Guard** to prevent chat flood mutes.

---

## ⚡ How It Works Under the Hood

### 1. 🛡️ 100% Non-Intrusive & Memory-Safe
- **Zero Memory Tampering**: This application does **not** inject any DLLs, read Roblox memory, or modify game files.
- **External Keystroke Simulation**: It operates purely as an external Windows input automation utility.
- **The Execution Cycle**:
  1. Activates the Roblox chat bar by simulating the Chat Open Key (default `/`).
  2. Waits for Roblox's chat bar animation and focus delay (~70ms).
  3. Inserts your message using either **Instant Clipboard Paste (`Ctrl+V`)** (preserves symbols, unicode, emojis, and avoids dropped keystrokes) or **Direct Typing**.
  4. Presses `Enter` to send the message into chat.
  5. Waits your configured interval (`ms` or `s`) before executing the next message.

### 2. 🎯 Unfocused Keybind Detection (`GetAsyncKeyState`)
- Traditional Python keyboard hooks (`WH_KEYBOARD_LL`) fail when you tab into Roblox because anti-cheat or Windows security drops non-admin background hooks.
- **Roblox Chat Macro** uses a dedicated background listener calling the native Windows **`user32.GetAsyncKeyState`** API directly against the Windows kernel every 10ms.
- **Result**: Your keybind (Default: `[F8]`) and emergency stop (`[ESC]`) trigger **100% reliably**, whether you are tabbed into Roblox, running fullscreen, or minimized.

### 3. ⏱️ Anti-Glitch Start Countdown & Roblox Auto-Focus
- When starting via the GUI **START MACRO** button:
  - An automated **3-second safety countdown** begins (`CLICK ROBLOX NOW! (3s) -> 2s -> 1s`).
  - The program automatically searches for and focuses the Roblox window (`focus_roblox_window()`).
  - Clears focus from all text boxes so keystrokes will never glitch the macro window.
- When starting via your **Keybind** (`F8`):
  - Starts immediately without countdown because you are already playing inside Roblox!

### 4. 🚨 Real-Time Roblox Spam & Flood Limit Guard
Roblox enforces strict chat rules:
- **Character Cap**: Max **200 characters** per message. Messages exceeding 200 chars fail to send.
- **Flood / Spam Filter**: Sending more than **5 messages within 5 seconds** or spamming under 500ms triggers a chat flood block (*"You are sending messages too quickly"*) and mutes your chat for 5 to 15 seconds.
- **Live Analyzer**:
  - 🟢 **SAFE**: Fully compliant with Roblox chat limits (intervals $\ge 1.0\text{s}$).
  - 🟡 **CAUTION**: Rapid burst (500ms – 999ms). Safe for 2–3 messages, but risk of throttle if looped.
  - 🔴 **RATE LIMIT DANGER**: Intervals $< 500\text{ms}$ or messages exceeding 200 chars. Prominently warns you to adjust speeds before you get muted.

---

## 💻 Requirements & Prerequisites

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python (Optional if using EXE)**: Python 3.10+ (tested on Python 3.13)
- **Roblox**: Any Roblox game on the official Roblox Player desktop client.

---

## 📦 How to Run

### Method 1: Run Standalone Executable (No Python Required)
1. Navigate to the `dist/` folder.
2. Double-click `RobloxChatMacro.exe`.
3. The app will launch immediately without needing any installations!

---

### Method 2: Run from Python Source Code

1. **Clone the repository**:
   ```bash
   git clone https://github.com/BlackwellArchitecture/Roblox-Chat-Macro.git
   cd Roblox-Chat-Macro
   ```

2. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the application**:
   - Double-click `run.bat` **OR** run in terminal:
     ```bash
     py main.py
     ```

---

### Method 3: Build Your Own Standalone EXE

To compile the source code into a single, portable `.exe`:
1. Double-click `build_exe.bat` **OR** run:
   ```bash
   py -m PyInstaller --noconsole --onefile --collect-all customtkinter --name "RobloxChatMacro" main.py
   ```
2. Your compiled standalone executable will be located in `dist\RobloxChatMacro.exe`.

---

## 🎮 Step-by-Step Usage Guide

1. **Add Your Messages**:
   - Click `+ Add Message` to add rows to your sequence.
   - Enter your text in each `[ Insert text message ]` box.
   - Watch the character counter `[ 0/200 ]` to stay within Roblox limits.
   - Use `✕` to remove any message you don't need.

2. **Configure Intervals & Speed**:
   - **Individual Mode**: Enter distinct delays for each message (select `ms` or `s`).
   - **Master Interval Mode**: Flip the **Master Interval** switch to apply a uniform speed (slider or number box) to all messages at once.

3. **Set Your Keybind & Activation Key**:
   - **Global Keybind**: Click `[ F8 ]` (it changes to `[Press Key...]`), then press any key on your keyboard to bind it.
   - **Chat Key**: Leave as `/` (default for Roblox chat) or change to your custom chat bind.

4. **Pin On Top**:
   - Enable the **Pin On Top** switch to keep the macro window visible above your Roblox game.

5. **Start Macroing**:
   - **Using Keybind**: Tab into Roblox, and press your hotkey (`F8`). The macro starts immediately in Roblox!
   - **Using GUI Button**: Click `START MACRO`. A 3-second countdown will give you time to switch back to Roblox.
   - **Emergency Stop**: Press `ESC` or your hotkey at any time to immediately halt execution.

---

## ⚙️ Configuration File (`macro_config.json`)

The application automatically saves your messages, intervals, hotkeys, and preferences upon exit:
```json
{
  "hotkey": "F8",
  "chat_key": "/",
  "always_on_top": true,
  "master_interval_enabled": true,
  "master_interval_ms": 1000,
  "send_method": "clipboard",
  "loop_mode": "once",
  "repeat_count": 3,
  "messages": [
    {
      "text": "GG well played!",
      "interval_ms": 1000
    }
  ]
}
```

---

## 🧪 Running Unit Tests

Run the built-in test suite to verify flood detection calculations and config persistence:
```bash
py test_suite.py
```

---

## 📜 License

This project is licensed under the MIT License. Feel free to use, modify, and distribute!
