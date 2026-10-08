"""
test_suite.py - Unit tests for Spam Analyzer and Config Manager
"""

import unittest
import os
from spam_analyzer import analyze_chat_macro, ROBLOX_MAX_CHAR_LIMIT
from config_manager import load_config, save_config, DEFAULT_CONFIG, get_config_path


class TestSpamAnalyzer(unittest.TestCase):
    def test_safe_burst(self):
        messages = ["Hello", "Good game", "Nice play"]
        intervals = [1.2, 1.5, 2.0]
        res = analyze_chat_macro(messages, intervals, loop=False)
        self.assertEqual(res["status"], "SAFE")
        self.assertTrue(res["is_safe"])
        self.assertEqual(len(res["char_warnings"]), 0)

    def test_danger_rapid_burst(self):
        # 6 messages with 0.1s interval (under 500ms and > 5 in 5s)
        messages = ["msg1", "msg2", "msg3", "msg4", "msg5", "msg6"]
        intervals = [0.1] * 6
        res = analyze_chat_macro(messages, intervals, loop=False)
        self.assertEqual(res["status"], "DANGER")
        self.assertFalse(res["is_safe"])
        self.assertTrue(any("FLOOD WARNING" in w for w in res["warnings"]))

    def test_char_limit_exceeded(self):
        long_message = "A" * 205
        messages = ["Normal", long_message]
        intervals = [1.0, 1.0]
        res = analyze_chat_macro(messages, intervals, loop=False)
        self.assertEqual(res["status"], "DANGER")
        self.assertEqual(len(res["char_warnings"]), 1)
        self.assertEqual(res["char_warnings"][0]["length"], 205)

    def test_caution_moderate_burst(self):
        messages = ["test1", "test2", "test3"]
        intervals = [0.6, 0.7, 0.6]
        res = analyze_chat_macro(messages, intervals, loop=False)
        self.assertEqual(res["status"], "CAUTION")


class TestConfigManager(unittest.TestCase):
    def test_load_and_save(self):
        config = load_config()
        self.assertIn("hotkey", config)
        self.assertIn("messages", config)
        
        # Test modifying and saving
        test_msg = [{"text": "Test custom message", "interval_ms": 999}]
        config["messages"] = test_msg
        saved = save_config(config)
        self.assertTrue(saved)
        
        reloaded = load_config()
        self.assertEqual(reloaded["messages"][0]["text"], "Test custom message")


if __name__ == "__main__":
    unittest.main()
