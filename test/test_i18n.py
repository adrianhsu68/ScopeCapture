"""Check language switching, error translation, and saved user data together."""
import ast
from pathlib import Path
import string
import tkinter as tk
import unittest
from unittest.mock import patch

from scopecapture.desktop import App
from scopecapture.i18n import ENGLISH, error_text, translate


class TranslationTests(unittest.TestCase):
    def test_backend_errors_have_english_messages_and_matching_placeholders(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "scopecapture" / "desktop_core.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
                message = node.exc.args[0]
                if isinstance(message, ast.Constant) and isinstance(message.value, str):
                    self.assertIn(message.value, ENGLISH)
                    self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in error_text(ValueError(message.value), "en")))
        fields = lambda text: {name for _, name, _, _ in string.Formatter().parse(text) if name}
        for source, english in ENGLISH.items():
            self.assertEqual(fields(source), fields(english), source)
            self.assertEqual(translate(translate(english, "zh_TW"), "en"), english)

    def test_system_errors_are_readable_in_english(self):
        self.assertIn("error code 13", error_text(PermissionError(13, "存取被拒"), "en"))
        self.assertIn("in time", error_text(TimeoutError("逾時"), "en"))

    def test_switching_preserves_selection_paths_and_translates_errors(self):
        selected = {"host": "192.0.2.10", "vendor": "KEYSIGHT TECHNOLOGIES", "model": "EDUX1052A", "serial": "EXAMPLE", "firmware": "1.0"}
        settings = {"selected": selected, "folder": "C:/測試/截圖", "language": "zh_TW", "background": "white"}
        with patch("scopecapture.desktop.load_settings", return_value=settings), patch("scopecapture.desktop.save_settings") as save, patch("scopecapture.desktop.suggested_networks", return_value=[]):
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root)
                app.set_status("截圖已儲存：{path}", path="C:/測試/截圖/example.png")
                app.language_name.set("English")
                app.switch_language()
                self.assertEqual(app.capture_button.cget("text"), "Capture screenshot")
                self.assertEqual(app.tree.item(app.tree.selection()[0], "values")[-1], "Supported")
                self.assertEqual(app.status.get(), "Screenshot saved: C:/測試/截圖/example.png")
                self.assertEqual(save.call_args.args[0]["language"], "en")
                self.assertEqual(save.call_args.args[0]["folder"], settings["folder"])
                self.assertEqual(save.call_args.args[0]["selected"], selected)
                self.assertEqual(app.background.get(), "white")
                app.host.set("invalid")
                with patch("scopecapture.desktop.messagebox.showerror") as dialog:
                    app.connect()
                    self.assertEqual(dialog.call_args.args[0], "Invalid IP address")
                with patch("scopecapture.desktop.messagebox.showerror") as dialog:
                    app.events.put(("error", ValueError("圖片資料不完整，請重新截圖。")))
                    app.poll()
                    self.assertEqual(dialog.call_args.args[:2], ("Operation not completed", "The image is incomplete. Capture the screen again."))
                app.language_name.set("繁體中文")
                app.switch_language()
                self.assertEqual(app.capture_button.cget("text"), "擷取截圖")
                self.assertEqual(app.folder.get(), settings["folder"])
            finally:
                root.destroy()
