"""
main.py - Roblox Chat Macro GUI Application
Modern CustomTkinter interface with GetAsyncKeyState global hotkey detection,
automatic Roblox window focusing, start countdown protections, and spam limit guard.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import List, Dict, Any, Optional

from spam_analyzer import analyze_chat_macro, ROBLOX_MAX_CHAR_LIMIT
from config_manager import load_config, save_config, DEFAULT_CONFIG
from macro_engine import MacroEngine, focus_roblox_window, VK_LOOKUP, get_vk_for_keyname

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MessageRow(ctk.CTkFrame):
    """Individual message row inside the scrollable container."""
    def __init__(self, master, row_index: int, text: str = "", interval_ms: int = 1000, 
                 on_delete=None, on_change=None, is_master_active: bool = False, master_val_ms: int = 1000):
        super().__init__(master, fg_color="#1e222d", corner_radius=8)
        self.row_index = row_index
        self.on_delete = on_delete
        self.on_change = on_change
        self.is_master_active = is_master_active
        self.master_val_ms = master_val_ms

        self.grid_columnconfigure(1, weight=1)

        # Index badge
        self.badge = ctk.CTkLabel(
            self, 
            text=f"#{row_index + 1}", 
            width=32, 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8da2b5"
        )
        self.badge.grid(row=0, column=0, padx=(8, 4), pady=6, sticky="w")

        # Text input field
        self.entry_var = tk.StringVar(value=text)
        self.entry_var.trace_add("write", self._on_text_updated)
        self.entry = ctk.CTkEntry(
            self, 
            textvariable=self.entry_var, 
            placeholder_text="[ Insert text message ]",
            height=34,
            corner_radius=6,
            font=ctk.CTkFont(size=13)
        )
        self.entry.grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        # Char count badge
        self.char_label = ctk.CTkLabel(
            self, 
            text=f"{len(text)}/{ROBLOX_MAX_CHAR_LIMIT}", 
            width=58, 
            font=ctk.CTkFont(size=11),
            text_color="#7f8c8d"
        )
        self.char_label.grid(row=0, column=2, padx=4, pady=6)

        # Interval Frame
        self.interval_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.interval_frame.grid(row=0, column=3, padx=6, pady=6)

        self.interval_var = tk.StringVar(value=str(interval_ms))
        self.interval_var.trace_add("write", self._on_interval_updated)
        
        self.unit_var = tk.StringVar(value="ms")
        
        self.interval_entry = ctk.CTkEntry(
            self.interval_frame,
            textvariable=self.interval_var,
            width=65,
            height=32,
            font=ctk.CTkFont(size=12)
        )
        self.interval_entry.pack(side="left", padx=(0, 4))

        self.unit_menu = ctk.CTkOptionMenu(
            self.interval_frame,
            values=["ms", "s"],
            variable=self.unit_var,
            command=self._on_unit_switched,
            width=54,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.unit_menu.pack(side="left")

        # Delete button
        self.del_btn = ctk.CTkButton(
            self, 
            text="✕", 
            width=32, 
            height=32, 
            fg_color="#3d232a",
            hover_color="#c0392b", 
            text_color="#e74c3c",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.on_delete(self) if self.on_delete else None
        )
        self.del_btn.grid(row=0, column=4, padx=(4, 8), pady=6)

        self.update_master_state(is_master_active, master_val_ms)
        self._check_char_limit()

    def _on_text_updated(self, *args):
        self._check_char_limit()
        if self.on_change:
            self.on_change()

    def _check_char_limit(self):
        length = len(self.entry_var.get())
        self.char_label.configure(text=f"{length}/{ROBLOX_MAX_CHAR_LIMIT}")
        if length > ROBLOX_MAX_CHAR_LIMIT:
            self.char_label.configure(text_color="#e74c3c", font=ctk.CTkFont(size=11, weight="bold"))
            self.entry.configure(border_color="#e74c3c")
        else:
            self.char_label.configure(text_color="#7f8c8d", font=ctk.CTkFont(size=11, weight="normal"))
            self.entry.configure(border_color=["#979DA2", "#565B5E"])

    def _on_interval_updated(self, *args):
        if self.on_change:
            self.on_change()

    def _on_unit_switched(self, choice):
        try:
            val = float(self.interval_var.get())
            if choice == "s" and val >= 50:
                self.interval_var.set(f"{val / 1000:.2f}".rstrip("0").rstrip("."))
            elif choice == "ms" and val < 50:
                self.interval_var.set(str(int(val * 1000)))
        except ValueError:
            pass
        if self.on_change:
            self.on_change()

    def update_master_state(self, is_master_active: bool, master_val_ms: int):
        self.is_master_active = is_master_active
        self.master_val_ms = master_val_ms
        if is_master_active:
            self.interval_entry.configure(state="disabled", fg_color="#2b2d35", text_color="#636e72")
            self.unit_menu.configure(state="disabled")
        else:
            self.interval_entry.configure(state="normal", fg_color=["#F9F9FA", "#343638"], text_color=["#000000", "#ffffff"])
            self.unit_menu.configure(state="normal")

    def get_text(self) -> str:
        return self.entry_var.get()

    def get_interval_ms(self) -> int:
        if self.is_master_active:
            return self.master_val_ms
        try:
            val = float(self.interval_var.get())
            if self.unit_var.get() == "s":
                return max(10, int(val * 1000))
            return max(10, int(val))
        except ValueError:
            return 1000


class RobloxChatMacroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Roblox Chat Macro - Speed & Limit Guard")
        self.geometry("800x780")
        self.minsize(700, 650)

        # Load configurations
        self.config = load_config()
        self.message_rows: List[MessageRow] = []
        self.is_capturing_keybind = False
        
        # Countdown state for UI button click
        self.countdown_remaining = 0
        self.countdown_job = None

        # Macro Execution Engine with GetAsyncKeyState background polling
        self.engine = MacroEngine(
            on_status_change=self._thread_safe_status_change,
            on_progress=self._thread_safe_progress
        )
        self.engine.set_start_request_callback(self._on_hotkey_triggered_start)
        self.engine.set_hotkey(self.config.get("hotkey", "F8"))

        self._build_ui()
        self._load_messages_from_config()
        self._apply_pin_on_top(self.config.get("always_on_top", True))
        self._refresh_spam_analysis()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # 1. HEADER
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=18, pady=(12, 6))

        self.app_title = ctk.CTkLabel(
            self.header_frame, 
            text="ROBLOX CHAT MACRO", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.app_title.pack(side="left")

        self.pin_switch_var = tk.BooleanVar(value=self.config.get("always_on_top", True))
        self.pin_switch = ctk.CTkSwitch(
            self.header_frame,
            text="Pin On Top",
            variable=self.pin_switch_var,
            command=self._on_pin_toggle,
            font=ctk.CTkFont(size=12)
        )
        self.pin_switch.pack(side="right", padx=(10, 0))

        self.esc_hint = ctk.CTkLabel(
            self.header_frame,
            text="Failsafe: [ESC] stops macro anytime",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        )
        self.esc_hint.pack(side="right", padx=(0, 15))

        # 2. TOP TOOLBAR CARD
        self.toolbar_card = ctk.CTkFrame(self, fg_color="#181a20", corner_radius=10)
        self.toolbar_card.pack(fill="x", padx=18, pady=4)

        # Trigger Hotkey
        hotkey_col = ctk.CTkFrame(self.toolbar_card, fg_color="transparent")
        hotkey_col.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(hotkey_col, text="Global Keybind:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a4b0be").pack(anchor="w")
        
        self.hotkey_btn = ctk.CTkButton(
            hotkey_col,
            text=f"[{self.config.get('hotkey', 'F8')}]",
            width=90,
            height=30,
            command=self._start_keybind_capture,
            fg_color="#2f3542",
            hover_color="#57606f",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.hotkey_btn.pack(anchor="w", pady=(2, 0))

        # Chat Open Key (Default /)
        chatkey_col = ctk.CTkFrame(self.toolbar_card, fg_color="transparent")
        chatkey_col.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(chatkey_col, text="Chat Key:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a4b0be").pack(anchor="w")
        self.chat_key_var = tk.StringVar(value=self.config.get("chat_key", "/"))
        self.chat_key_entry = ctk.CTkEntry(
            chatkey_col,
            textvariable=self.chat_key_var,
            width=45,
            height=30,
            justify="center",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.chat_key_entry.pack(anchor="w", pady=(2, 0))

        # Execution Mode
        mode_col = ctk.CTkFrame(self.toolbar_card, fg_color="transparent")
        mode_col.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(mode_col, text="Execution Mode:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a4b0be").pack(anchor="w")
        self.loop_mode_menu = ctk.CTkOptionMenu(
            mode_col,
            values=["Single Run (once)", "Repeat 3x", "Repeat 5x", "Continuous Loop"],
            command=self._on_loop_mode_change,
            width=135,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        current_mode = self.config.get("loop_mode", "once")
        if current_mode == "once":
            self.loop_mode_menu.set("Single Run (once)")
        elif current_mode == "continuous":
            self.loop_mode_menu.set("Continuous Loop")
        elif current_mode == "repeat":
            self.loop_mode_menu.set(f"Repeat {self.config.get('repeat_count', 3)}x")
        self.loop_mode_menu.pack(anchor="w", pady=(2, 0))

        # Send Method
        send_col = ctk.CTkFrame(self.toolbar_card, fg_color="transparent")
        send_col.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(send_col, text="Typing Method:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a4b0be").pack(anchor="w")
        self.send_segmented = ctk.CTkSegmentedButton(
            send_col,
            values=["Clipboard (Fast)", "Direct Type"],
            command=self._on_send_method_change,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        if self.config.get("send_method", "clipboard") == "type":
            self.send_segmented.set("Direct Type")
        else:
            self.send_segmented.set("Clipboard (Fast)")
        self.send_segmented.pack(anchor="w", pady=(2, 0))

        # 3. MASTER INTERVAL CONTROLLER CARD
        self.master_card = ctk.CTkFrame(self, fg_color="#181a20", corner_radius=10)
        self.master_card.pack(fill="x", padx=18, pady=4)

        self.master_enable_var = tk.BooleanVar(value=self.config.get("master_interval_enabled", True))
        self.master_switch = ctk.CTkSwitch(
            self.master_card,
            text="Master Interval (Override all)",
            variable=self.master_enable_var,
            command=self._on_master_toggle,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.master_switch.pack(side="left", padx=14, pady=8)

        # Master Interval Controls
        self.master_ctrl_frame = ctk.CTkFrame(self.master_card, fg_color="transparent")
        self.master_ctrl_frame.pack(side="right", padx=14, pady=8)

        self.master_interval_var = tk.StringVar(value=str(self.config.get("master_interval_ms", 1000)))
        self.master_interval_var.trace_add("write", lambda *_: self._on_master_val_changed())
        
        self.master_entry = ctk.CTkEntry(
            self.master_ctrl_frame,
            textvariable=self.master_interval_var,
            width=65,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        self.master_entry.pack(side="left", padx=(0, 4))

        self.master_unit_var = tk.StringVar(value="ms")
        self.master_unit_menu = ctk.CTkOptionMenu(
            self.master_ctrl_frame,
            values=["ms", "s"],
            variable=self.master_unit_var,
            command=self._on_master_unit_switched,
            width=54,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.master_unit_menu.pack(side="left", padx=(0, 8))

        self.master_slider = ctk.CTkSlider(
            self.master_ctrl_frame,
            from_=50,
            to=3000,
            number_of_steps=59,
            command=self._on_slider_moved,
            width=150
        )
        self.master_slider.set(self.config.get("master_interval_ms", 1000))
        self.master_slider.pack(side="left")

        # 4. MESSAGES LIST CONTAINER
        self.list_header = ctk.CTkFrame(self, fg_color="transparent")
        self.list_header.pack(fill="x", padx=22, pady=(6, 2))
        
        ctk.CTkLabel(
            self.list_header, 
            text="MESSAGE SEQUENCE", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8da2b5"
        ).pack(side="left")

        ctk.CTkLabel(
            self.list_header, 
            text="Interval (ms / s)", 
            font=ctk.CTkFont(size=11),
            text_color="#8da2b5"
        ).pack(side="right", padx=(0, 48))

        # Scrollable Frame for Message Rows
        self.messages_scroll = ctk.CTkScrollableFrame(self, fg_color="#121418", corner_radius=10, height=210)
        self.messages_scroll.pack(fill="both", expand=True, padx=18, pady=4)

        # Plus button to add row
        self.add_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.add_btn_frame.pack(fill="x", padx=18, pady=4)

        self.add_btn = ctk.CTkButton(
            self.add_btn_frame,
            text="+ Add Message",
            height=32,
            command=self._add_empty_message_row,
            fg_color="#2b313e",
            hover_color="#3d4659",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.add_btn.pack(fill="x")

        # 5. ROBLOX SPAM LIMIT & RATE GUARD METER CARD
        self.spam_card = ctk.CTkFrame(self, fg_color="#181a20", corner_radius=10)
        self.spam_card.pack(fill="x", padx=18, pady=4)

        self.spam_top_row = ctk.CTkFrame(self.spam_card, fg_color="transparent")
        self.spam_top_row.pack(fill="x", padx=12, pady=(8, 2))

        self.spam_badge = ctk.CTkLabel(
            self.spam_top_row,
            text=" SAFE ",
            fg_color="#2ecc71",
            text_color="#ffffff",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2
        )
        self.spam_badge.pack(side="left")

        self.spam_title_lbl = ctk.CTkLabel(
            self.spam_top_row,
            text="Safe Rate Limit (Complies with Roblox limits)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ecc71"
        )
        self.spam_title_lbl.pack(side="left", padx=8)

        self.stats_lbl = ctk.CTkLabel(
            self.spam_top_row,
            text="0 msgs | 0.0s | 0.0 MPS",
            font=ctk.CTkFont(size=11),
            text_color="#8da2b5"
        )
        self.stats_lbl.pack(side="right")

        self.spam_detail_lbl = ctk.CTkLabel(
            self.spam_card,
            text="Roblox limit: Maximum ~5 messages per 5s and 200 characters per message.",
            font=ctk.CTkFont(size=11),
            text_color="#bdc3c7",
            wraplength=730,
            justify="left"
        )
        self.spam_detail_lbl.pack(fill="x", padx=12, pady=(2, 8))

        # 6. ACTION & STATUS BAR (Includes Click-Start Countdown Guard)
        self.action_card = ctk.CTkFrame(self, fg_color="#181a20", corner_radius=10)
        self.action_card.pack(fill="x", padx=18, pady=(4, 12))

        self.status_lbl = ctk.CTkLabel(
            self.action_card,
            text="Ready. Press keybind from inside Roblox to start immediately.",
            font=ctk.CTkFont(size=12),
            text_color="#a4b0be"
        )
        self.status_lbl.pack(side="left", padx=14, pady=10)

        self.start_btn = ctk.CTkButton(
            self.action_card,
            text=f"START MACRO [{self.config.get('hotkey', 'F8')}]",
            height=38,
            width=230,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_start_stop_button_clicked
        )
        self.start_btn.pack(side="right", padx=12, pady=6)

        # Apply initial master enable state
        self._sync_master_inputs_state()

    # --- Configuration & State Synchronization ---

    def _apply_pin_on_top(self, pinned: bool):
        self.attributes("-topmost", pinned)

    def _on_pin_toggle(self):
        is_pinned = self.pin_switch_var.get()
        self._apply_pin_on_top(is_pinned)
        self.config["always_on_top"] = is_pinned
        save_config(self.config)

    def _load_messages_from_config(self):
        messages_data = self.config.get("messages", [])
        is_master = self.master_enable_var.get()
        master_val = self._get_master_interval_ms()

        for idx, item in enumerate(messages_data):
            row = MessageRow(
                self.messages_scroll,
                row_index=idx,
                text=item.get("text", ""),
                interval_ms=item.get("interval_ms", 1000),
                on_delete=self._delete_message_row,
                on_change=self._on_message_data_changed,
                is_master_active=is_master,
                master_val_ms=master_val
            )
            row.pack(fill="x", pady=3)
            self.message_rows.append(row)

    def _add_empty_message_row(self):
        idx = len(self.message_rows)
        is_master = self.master_enable_var.get()
        master_val = self._get_master_interval_ms()
        
        row = MessageRow(
            self.messages_scroll,
            row_index=idx,
            text="",
            interval_ms=master_val if is_master else 1000,
            on_delete=self._delete_message_row,
            on_change=self._on_message_data_changed,
            is_master_active=is_master,
            master_val_ms=master_val
        )
        row.pack(fill="x", pady=3)
        self.message_rows.append(row)
        self._renumber_rows()
        self._refresh_spam_analysis()
        row.entry.focus()

    def _delete_message_row(self, row_to_del: MessageRow):
        if len(self.message_rows) <= 1:
            row_to_del.entry_var.set("")
            self._refresh_spam_analysis()
            return
            
        row_to_del.destroy()
        self.message_rows = [r for r in self.message_rows if r != row_to_del]
        self._renumber_rows()
        self._refresh_spam_analysis()

    def _renumber_rows(self):
        for idx, row in enumerate(self.message_rows):
            row.row_index = idx
            row.badge.configure(text=f"#{idx + 1}")

    def _on_message_data_changed(self):
        self._refresh_spam_analysis()

    # --- Master Interval Controls ---

    def _get_master_interval_ms(self) -> int:
        try:
            val = float(self.master_interval_var.get())
            if self.master_unit_var.get() == "s":
                return max(10, int(val * 1000))
            return max(10, int(val))
        except ValueError:
            return 1000

    def _on_master_toggle(self):
        is_enabled = self.master_enable_var.get()
        self.config["master_interval_enabled"] = is_enabled
        self._sync_master_inputs_state()
        master_val = self._get_master_interval_ms()
        for row in self.message_rows:
            row.update_master_state(is_enabled, master_val)
        self._refresh_spam_analysis()

    def _sync_master_inputs_state(self):
        is_enabled = self.master_enable_var.get()
        if is_enabled:
            self.master_entry.configure(state="normal")
            self.master_unit_menu.configure(state="normal")
            self.master_slider.configure(state="normal")
        else:
            self.master_entry.configure(state="disabled")
            self.master_unit_menu.configure(state="disabled")
            self.master_slider.configure(state="disabled")

    def _on_master_val_changed(self):
        master_val = self._get_master_interval_ms()
        try:
            slider_val = min(3000, max(50, master_val))
            self.master_slider.set(slider_val)
        except Exception:
            pass
        for row in self.message_rows:
            row.master_val_ms = master_val
        self._refresh_spam_analysis()

    def _on_slider_moved(self, value):
        ms_val = int(value)
        if self.master_unit_var.get() == "s":
            self.master_interval_var.set(f"{ms_val / 1000:.2f}".rstrip("0").rstrip("."))
        else:
            self.master_interval_var.set(str(ms_val))
        for row in self.message_rows:
            row.master_val_ms = ms_val
        self._refresh_spam_analysis()

    def _on_master_unit_switched(self, choice):
        try:
            val = float(self.master_interval_var.get())
            if choice == "s" and val >= 50:
                self.master_interval_var.set(f"{val / 1000:.2f}".rstrip("0").rstrip("."))
            elif choice == "ms" and val < 50:
                self.master_interval_var.set(str(int(val * 1000)))
        except ValueError:
            pass
        self._refresh_spam_analysis()

    # --- Mode & Settings Changes ---

    def _on_loop_mode_change(self, choice):
        if "once" in choice:
            self.config["loop_mode"] = "once"
        elif "Continuous" in choice:
            self.config["loop_mode"] = "continuous"
        elif "3x" in choice:
            self.config["loop_mode"] = "repeat"
            self.config["repeat_count"] = 3
        elif "5x" in choice:
            self.config["loop_mode"] = "repeat"
            self.config["repeat_count"] = 5
        self._refresh_spam_analysis()

    def _on_send_method_change(self, choice):
        if "Clipboard" in choice:
            self.config["send_method"] = "clipboard"
        else:
            self.config["send_method"] = "type"

    # --- Keybind Capture ---

    def _start_keybind_capture(self):
        if self.is_capturing_keybind:
            return
        self.is_capturing_keybind = True
        self.hotkey_btn.configure(text="[Press Key...]", fg_color="#e67e22")
        self.bind("<KeyPress>", self._on_key_captured)

    def _on_key_captured(self, event):
        self.unbind("<KeyPress>")
        self.is_capturing_keybind = False
        
        key_name = event.keysym.upper()
        # Clean aliases
        if key_name == "PRIOR":
            key_name = "PAGEUP"
        elif key_name == "NEXT":
            key_name = "PAGEDOWN"
        elif key_name == "GRAVE":
            key_name = "`"

        # Check if key is valid in VK lookup table
        vk = get_vk_for_keyname(key_name)
        if vk is not None and key_name not in ["ESC", "ESCAPE", "RETURN", "BACKSPACE"]:
            self.engine.set_hotkey(key_name)
            self.config["hotkey"] = key_name
            self.hotkey_btn.configure(text=f"[{key_name}]", fg_color="#2f3542")
            self.start_btn.configure(text=f"START MACRO [{key_name}]")
            save_config(self.config)
        else:
            self.hotkey_btn.configure(
                text=f"[{self.config.get('hotkey', 'F8')}]",
                fg_color="#2f3542"
            )

    # --- Roblox Spam & Rate Limit Analysis ---

    def _collect_current_data(self):
        messages = [row.get_text() for row in self.message_rows]
        intervals_s = [row.get_interval_ms() / 1000.0 for row in self.message_rows]
        is_loop = self.config.get("loop_mode") in ["continuous", "repeat"]
        return messages, intervals_s, is_loop

    def _refresh_spam_analysis(self):
        messages, intervals_s, is_loop = self._collect_current_data()
        analysis = analyze_chat_macro(messages, intervals_s, loop=is_loop)

        self.spam_badge.configure(
            text=f" {analysis['status']} ",
            fg_color=analysis["color"]
        )

        self.spam_title_lbl.configure(
            text=analysis["title"],
            text_color=analysis["color"]
        )

        msg_count = len([m for m in messages if m.strip()])
        dur = analysis["total_duration"]
        mps = analysis["burst_rate_mps"]
        self.stats_lbl.configure(text=f"{msg_count} msgs | {dur:.1f}s cycle | {mps:.1f} msg/s")

        if analysis["warnings"]:
            self.spam_detail_lbl.configure(
                text="\n• ".join(["Warnings & Info:"] + analysis["warnings"]),
                text_color=analysis["color"] if analysis["status"] != "SAFE" else "#bdc3c7"
            )
        else:
            self.spam_detail_lbl.configure(
                text="Roblox limit: Maximum ~5 messages per 5s and 200 characters per message. Your intervals are safe!",
                text_color="#bdc3c7"
            )

    # --- Macro Start / Stop Mechanics ---

    def _on_hotkey_triggered_start(self):
        """
        Triggered when the user presses the hotkey (e.g. F8) from anywhere,
        including inside Roblox while tabbed out!
        Since the user is already inside Roblox, starts immediately without countdown!
        """
        self.after(0, lambda: self._execute_macro_sequence(is_from_hotkey=True))

    def _on_start_stop_button_clicked(self):
        """Called when user clicks the UI button."""
        # 1. If currently in countdown, cancel it
        if self.countdown_job:
            self._cancel_countdown("Cancelled countdown")
            return

        # 2. If already running, stop it
        if self.engine.is_running:
            self.engine.stop("Stopped by user")
            return

        # 3. If starting via UI button, remove focus from entries and initiate 3-second countdown
        self.focus_set()  # Clear focus from any active text input!
        self._start_ui_button_countdown(3)

    def _start_ui_button_countdown(self, seconds: int):
        """Gives user time to click their Roblox game window before keystrokes begin."""
        self.countdown_remaining = seconds
        
        # Automatically attempt to focus Roblox
        focused = focus_roblox_window()

        self.start_btn.configure(
            text=f"CLICK ROBLOX! ({self.countdown_remaining}s) [Cancel]",
            fg_color="#e67e22",
            hover_color="#d35400"
        )
        focus_hint = " (Roblox focused!)" if focused else " (Click your Roblox window now!)"
        self.status_lbl.configure(
            text=f"⏳ Starting in {self.countdown_remaining}s...{focus_hint}",
            text_color="#f39c12"
        )
        self._tick_countdown()

    def _tick_countdown(self):
        if self.countdown_remaining <= 0:
            self.countdown_job = None
            self._execute_macro_sequence(is_from_hotkey=False)
            return

        self.start_btn.configure(
            text=f"CLICK ROBLOX! ({self.countdown_remaining}s) [Cancel]"
        )
        self.status_lbl.configure(
            text=f"⏳ Starting in {self.countdown_remaining}s... Click your Roblox window!",
            text_color="#f39c12"
        )
        self.countdown_remaining -= 1
        self.countdown_job = self.after(1000, self._tick_countdown)

    def _cancel_countdown(self, reason: str = "Cancelled"):
        if self.countdown_job:
            self.after_cancel(self.countdown_job)
            self.countdown_job = None
        hotkey_str = self.config.get("hotkey", "F8")
        self.start_btn.configure(
            text=f"START MACRO [{hotkey_str}]",
            fg_color="#27ae60",
            hover_color="#2ecc71"
        )
        self.status_lbl.configure(
            text=f"Status: {reason}",
            text_color="#a4b0be"
        )

    def _execute_macro_sequence(self, is_from_hotkey: bool = False):
        if self.engine.is_running:
            return

        messages = [row.get_text() for row in self.message_rows if row.get_text().strip()]
        if not messages:
            messagebox.showwarning("Empty Messages", "Please enter at least one message before starting.")
            self._cancel_countdown()
            return

        intervals_ms = [row.get_interval_ms() for row in self.message_rows if row.get_text().strip()]
        chat_key = self.chat_key_var.get().strip() or "/"
        send_method = self.config.get("send_method", "clipboard")
        loop_mode = self.config.get("loop_mode", "once")
        repeat_count = self.config.get("repeat_count", 3)

        # Validate 200 character cap
        intervals_s = [ms / 1000.0 for ms in intervals_ms]
        analysis = analyze_chat_macro(messages, intervals_s, loop=(loop_mode != "once"))
        if analysis["char_warnings"]:
            messagebox.showerror(
                "Roblox 200-Character Limit",
                "One or more messages exceed Roblox's 200-character limit!\nPlease shorten them before macroing."
            )
            self._cancel_countdown()
            return

        # Start execution
        # If started via hotkey, user is already in Roblox, use small delay
        initial_delay = 120 if is_from_hotkey else 150
        self.engine.start(
            messages=messages,
            intervals_ms=intervals_ms,
            chat_key=chat_key,
            focus_delay_ms=self.config.get("focus_delay_ms", 70),
            send_method=send_method,
            loop_mode=loop_mode,
            repeat_count=repeat_count,
            initial_delay_ms=initial_delay
        )

    # --- Thread Safe Status Callbacks ---

    def _thread_safe_status_change(self, is_running: bool, status_msg: str):
        self.after(0, lambda: self._apply_status_ui(is_running, status_msg))

    def _thread_safe_progress(self, current_idx: int, total_idx: int):
        self.after(0, lambda: self._apply_progress_ui(current_idx, total_idx))

    def _apply_status_ui(self, is_running: bool, status_msg: str):
        if is_running:
            self.start_btn.configure(
                text="STOP MACRO [ESC]",
                fg_color="#c0392b",
                hover_color="#e74c3c"
            )
            self.status_lbl.configure(
                text=f"● Active: {status_msg}",
                text_color="#2ecc71"
            )
        else:
            hotkey_str = self.config.get("hotkey", "F8")
            self.start_btn.configure(
                text=f"START MACRO [{hotkey_str}]",
                fg_color="#27ae60",
                hover_color="#2ecc71"
            )
            self.status_lbl.configure(
                text=f"Status: {status_msg}",
                text_color="#a4b0be"
            )

    def _apply_progress_ui(self, current_idx: int, total_idx: int):
        self.status_lbl.configure(
            text=f"● Sending message {current_idx} of {total_idx}...",
            text_color="#f1c40f"
        )

    # --- Cleanup & Presets Saving ---

    def _save_current_settings(self):
        self.config["chat_key"] = self.chat_key_var.get().strip() or "/"
        self.config["master_interval_enabled"] = self.master_enable_var.get()
        self.config["master_interval_ms"] = self._get_master_interval_ms()
        self.config["messages"] = [
            {"text": row.get_text(), "interval_ms": row.get_interval_ms()}
            for row in self.message_rows
            if row.get_text().strip()
        ]
        save_config(self.config)

    def _on_close(self):
        try:
            if self.countdown_job:
                self.after_cancel(self.countdown_job)
            self.engine.shutdown()
            self._save_current_settings()
        except Exception:
            pass
        self.destroy()


def main():
    app = RobloxChatMacroApp()
    app.mainloop()


if __name__ == "__main__":
    main()
