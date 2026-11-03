"""Bilingual screenshot application for Windows."""
from dataclasses import asdict
import ipaddress
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .i18n import LANGUAGES, default_language, error_text, translate

from .desktop_core import (Device, capture, load_settings, probe, save_settings,
                           scan, suggested_networks)


class App:
    def __init__(self, root, persist=True):
        self.root = root
        self.settings = load_settings()
        self.persist = persist
        self.language = self.settings.get("language", "zh_TW" if self.settings else default_language())
        self._status_spec = None
        self.devices = {}
        self.selected = None
        self.busy = False
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.last_file = None
        self.remember_warning = False
        root.title(self.tr("示波器截圖 · ScopeCapture") + " v" + __version__)
        root.geometry("1000x720")
        root.minsize(920, 660)
        root.option_add("*Font", ("Microsoft JhengHei UI", 10))
        style = ttk.Style(root)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        style.configure("Treeview", rowheight=30, font=("Microsoft JhengHei UI", 10))
        style.configure("Treeview.Heading", font=("Microsoft JhengHei UI", 10, "bold"))
        style.configure("Capture.TButton", font=("Microsoft JhengHei UI", 17, "bold"), padding=12)

        body = ttk.Frame(root, padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text=self.tr("把示波器畫面，存到這台電腦"), font=("Microsoft JhengHei UI", 21, "bold")).pack(side="left")
        self.language_name = tk.StringVar(value=next(name for name, code in LANGUAGES.items() if code == self.language))
        self.language_input = ttk.Combobox(header, textvariable=self.language_name, values=list(LANGUAGES), state="readonly", width=12)
        self.language_input.pack(side="right")
        self.language_input.bind("<<ComboboxSelected>>", self.switch_language)
        ttk.Label(header, text="語言 / Language").pack(side="right", padx=10)
        ttk.Label(body, text=self.tr("第一次先搜尋並選擇儀器；下次開啟會記住你的選擇。"), padding=(0, 5, 0, 16)).grid(row=1, column=0, sticky="w")

        box = ttk.LabelFrame(body, text=self.tr("1  選擇示波器"), padding=12)
        box.grid(row=2, column=0, sticky="nsew")
        box.columnconfigure(0, weight=1)
        box.rowconfigure(2, weight=1)
        networks = suggested_networks()
        self.network = tk.StringVar(value=self.settings.get("network", networks[0] if networks else "192.168.1.0/24"))
        line = ttk.Frame(box)
        line.grid(row=0, column=0, sticky="ew")
        line.columnconfigure(1, weight=1)
        ttk.Label(line, text=self.tr("搜尋網段")).grid(row=0, column=0, padx=(0, 10))
        self.network_input = ttk.Combobox(line, textvariable=self.network, values=networks, width=28)
        self.network_input.grid(row=0, column=1, sticky="ew")
        self.search_button = ttk.Button(line, text=self.tr("搜尋示波器"), command=self.search)
        self.search_button.grid(row=0, column=2, padx=(10, 0))
        self.stop_button = ttk.Button(line, text=self.tr("停止搜尋"), command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=(6, 0))
        ttk.Label(box, text=self.tr("搜尋指定網段的儀器（TCP 5025）。不同網段可自行輸入，或在下方直接輸入 IP。"), padding=(0, 7)).grid(row=1, column=0, sticky="w")

        table = ttk.Frame(box)
        table.grid(row=2, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("model", "serial", "ip", "support"), show="headings", selectmode="browse", height=5)
        for name, label, width in (("model", "型號", 155), ("serial", "序號（辨識哪一台）", 210), ("ip", "IP 位址", 145), ("support", "截圖支援", 110)):
            self.tree.heading(name, text=self.tr(label))
            self.tree.column(name, width=width, minwidth=110)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.choose)

        manual = ttk.Frame(box, padding=(0, 10, 0, 0))
        manual.grid(row=3, column=0, sticky="ew")
        ttk.Label(manual, text=self.tr("直接輸入 IP")).pack(side="left")
        self.host = tk.StringVar()
        self.host_input = ttk.Entry(manual, textvariable=self.host, width=22)
        self.host_input.pack(side="left", padx=10)
        self.connect_button = ttk.Button(manual, text=self.tr("辨識並選取"), command=self.connect)
        self.connect_button.pack(side="left")
        self.current = tk.StringVar(value=self.tr("尚未選擇示波器"))
        ttk.Label(box, textvariable=self.current, padding=(0, 10, 0, 0)).grid(row=4, column=0, sticky="w")

        output = ttk.LabelFrame(body, text=self.tr("2  儲存圖片"), padding=12)
        output.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        output.columnconfigure(0, weight=1)
        self.folder = tk.StringVar(value=self.settings.get("folder", str(Path.home() / "Pictures" / "ScopeCaptures")))
        self.folder_input = ttk.Entry(output, textvariable=self.folder)
        self.folder_input.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(output, text=self.tr("選擇資料夾…"), command=self.browse)
        self.browse_button.grid(row=0, column=1, padx=(10, 0))
        self.open_folder_button = ttk.Button(output, text=self.tr("開啟資料夾"), command=self.open_folder)
        self.open_folder_button.grid(row=0, column=2, padx=(6, 0))
        self.auto_open = tk.BooleanVar(value=self.settings.get("auto_open", True))
        self.auto_check = ttk.Checkbutton(output, text=self.tr("截圖完成後自動開啟圖片"), variable=self.auto_open, command=self.remember)
        self.auto_check.grid(row=1, column=0, sticky="w", pady=(8, 0))
        palette = ttk.Frame(output, padding=(0, 8, 0, 0))
        palette.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(palette, text=self.tr("截圖背景")).pack(side="left", padx=(0, 12))
        self.background = tk.StringVar(value=self.settings.get("background", "black"))
        self.black_button = ttk.Radiobutton(palette, text=self.tr("黑底（螢幕原貌）"), variable=self.background,
                                           value="black", command=self.remember)
        self.black_button.pack(side="left", padx=(0, 18))
        self.white_button = ttk.Radiobutton(palette, text=self.tr("白底（適合列印）"), variable=self.background,
                                           value="white", command=self.remember)
        self.white_button.pack(side="left")

        self.capture_button = ttk.Button(body, text=self.tr("擷取截圖"), style="Capture.TButton", command=self.take, state="disabled")
        self.capture_button.grid(row=4, column=0, sticky="ew", pady=(16, 10))
        self.status = tk.StringVar(value=self.tr("請搜尋示波器，或輸入示波器的 IP。"))
        ttk.Label(body, textvariable=self.status, wraplength=820).grid(row=5, column=0, sticky="w")
        self.progress = ttk.Progressbar(body, mode="determinate")
        self.progress.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        remembered = self.settings.get("selected")
        if remembered:
            device = Device(**remembered)
            self.add(device, select=True)
            self.set_status("已載入上次選擇；按「擷取截圖」時會確認儀器型號與序號。")
        if self._status_spec is None:
            self.set_status("請搜尋示波器，或輸入示波器的 IP。")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(80, self.poll)

    def tr(self, message, **values):
        return translate(message, self.language, **values)

    def set_status(self, message, **values):
        self._status_spec = message, values
        self.status.set(self.tr(message, **values))

    def show_error(self, title, message, **options):
        messagebox.showerror(self.tr(title), self.tr(message), **options)

    def show_warning(self, title, message, **options):
        messagebox.showwarning(self.tr(title), self.tr(message), **options)

    def refresh_current(self):
        if self.selected:
            d = self.selected
            self.current.set(self.tr("目前選擇：{model}  /  {serial}  /  {host}", model=d.model, serial=d.serial, host=d.host))
        else:
            self.current.set(self.tr("尚未選擇示波器"))

    def switch_language(self, _event=None):
        if self.busy:
            return
        self.language = LANGUAGES[self.language_name.get()]
        self.root.title(self.tr("示波器截圖 · ScopeCapture") + " v" + __version__)
        def visit(widget):
            try:
                text = widget.cget("text")
                if text:
                    widget.configure(text=self.tr(str(text)))
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                visit(child)
        visit(self.root)
        for name, label in (("model", "型號"), ("serial", "序號（辨識哪一台）"), ("ip", "IP 位址"), ("support", "截圖支援")):
            self.tree.heading(name, text=self.tr(label))
        for key, d in self.devices.items():
            self.tree.item(key, values=(d.model, d.serial, d.host, self.tr("可擷取" if d.supported else "尚未支援")))
        self.refresh_current()
        if self._status_spec:
            message, values = self._status_spec
            self.status.set(self.tr(message, **values))
        self.remember()

    def remember(self):
        doc = {"network": self.network.get(), "folder": self.folder.get(), "auto_open": self.auto_open.get(),
               "background": self.background.get(), "language": self.language}
        if self.selected:
            doc["selected"] = asdict(self.selected)
        if not self.persist:
            return
        try:
            save_settings(doc)
        except OSError as exc:
            if not self.remember_warning:
                self.remember_warning = True
                self.show_warning("無法記住設定", self.tr("目前仍可使用，但下次不會保留這次設定。\n\n{error}", error=error_text(exc, self.language)), parent=self.root)

    def add(self, device, select=False):
        # Same serial at a new IP updates the old row; same IP with a new
        # identity gets a separate row so a remembered choice is not replaced.
        key = repr(device.identity)
        self.devices[key] = device
        values = (device.model, device.serial, device.host, self.tr("可擷取" if device.supported else "尚未支援"))
        if self.tree.exists(key):
            self.tree.item(key, values=values)
        else:
            self.tree.insert("", "end", iid=key, values=values)
        if select or (self.selected and self.selected.identity == device.identity):
            self.tree.selection_set(key)
            self.tree.focus(key)
            self.tree.see(key)
            self.selected = device
            self.host.set(device.host)
            self.refresh_current()
            self.remember()
        self.update_capture()

    def choose(self, _event=None):
        rows = self.tree.selection()
        if not rows:
            return
        self.selected = self.devices[rows[0]]
        d = self.selected
        self.host.set(d.host)
        self.refresh_current()
        self.remember()
        self.update_capture()

    def update_capture(self):
        self.capture_button.configure(state="normal" if self.selected and self.selected.supported and not self.busy else "disabled")

    def set_busy(self, busy, searching=False):
        self.busy = busy
        for widget in (self.search_button, self.connect_button, self.network_input, self.host_input,
                       self.folder_input, self.browse_button, self.auto_check, self.black_button, self.white_button):
            widget.configure(state="disabled" if busy else "normal")
        self.language_input.configure(state="disabled" if busy else "readonly")
        self.stop_button.configure(state="normal" if busy and searching else "disabled")
        self.update_capture()

    def work(self, operation):
        def run():
            try:
                self.events.put(("done", operation()))
            except Exception as exc:
                self.events.put(("error", exc))
        threading.Thread(target=run, daemon=True).start()

    def search(self):
        if self.busy:
            return
        try:
            net = ipaddress.ip_network(self.network.get().strip(), strict=False)
            if net.version != 4 or net.prefixlen < 22:
                raise ValueError()
        except ValueError:
            self.show_error("網段格式", "請輸入 IPv4 網段（最多 1024 個位址），例如 192.168.1.0/24。", parent=self.root)
            return
        self.network.set(str(net))
        self.remember()
        self.cancel.clear()
        self.set_busy(True, searching=True)
        self.progress.configure(value=0)
        self.set_status("正在搜尋 {network}…", network=net)
        def operation():
            found = 0
            def report(done, total, device):
                nonlocal found
                if device:
                    found += 1
                self.events.put(("scan", (done, total, device)))
            scan(str(net), self.cancel, report)
            return ("search", found, self.cancel.is_set())
        self.work(operation)

    def stop(self):
        self.cancel.set()
        self.stop_button.configure(state="disabled")
        self.set_status("正在停止搜尋…")

    def connect(self):
        if self.busy:
            return
        try:
            host = str(ipaddress.IPv4Address(self.host.get().strip()))
        except ValueError:
            self.show_error("IP 格式", "請輸入示波器的 IPv4 位址，例如 192.168.1.100。", parent=self.root)
            return
        self.set_busy(True)
        self.set_status("正在辨識 {host}…", host=host)
        self.work(lambda: ("connect", probe(host, timeout=4)))

    def browse(self):
        folder = filedialog.askdirectory(parent=self.root, title=self.tr("選擇截圖儲存資料夾"))
        if folder:
            self.folder.set(folder)
            self.remember()

    def open_folder(self):
        try:
            folder = Path(self.folder.get()).expanduser()
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder.resolve()))
        except OSError as exc:
            self.show_error("無法開啟資料夾", error_text(exc, self.language), parent=self.root)

    def take(self):
        if self.busy or not self.selected:
            return
        if not self.folder.get().strip():
            self.show_error("儲存位置", "請先選擇儲存資料夾。", parent=self.root)
            return
        device, folder = self.selected, self.folder.get().strip()
        auto_open = self.auto_open.get()
        background = self.background.get()
        self.remember()
        self.set_busy(True)
        self.set_status("正在確認 {model} / {serial} 並讀取畫面…", model=device.model, serial=device.serial)
        self.work(lambda: ("capture", capture(device, folder, background=background), auto_open))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "scan":
                    done, total, device = value
                    self.progress.configure(value=100 * done / total)
                    if device:
                        self.add(device)
                    if not self.cancel.is_set():
                        self.set_status("搜尋中：已檢查 {done} / {total} 個位址。請從清單選擇要使用的儀器。", done=done, total=total)
                elif kind == "error":
                    self.set_busy(False)
                    self.set_status("未完成。請確認示波器已開機、接上網路，且 IP／搜尋網段正確。")
                    self.show_error("操作未完成", error_text(value, self.language), parent=self.root)
                else:
                    self.set_busy(False)
                    if value[0] == "search":
                        _, count, stopped = value
                        if not stopped:
                            self.progress.configure(value=100)
                        self.set_status("已停止搜尋，本次找到 {count} 台儀器。清單保留上次選擇；找不到時可直接輸入 IP。" if stopped else "搜尋完成，本次找到 {count} 台儀器。清單保留上次選擇；找不到時可直接輸入 IP。", count=count)
                    elif value[0] == "connect":
                        self.add(value[1], select=True)
                        self.set_status("已辨識並記住這台儀器。可以擷取截圖。" if value[1].supported else "已辨識並記住這台儀器。這個型號尚未支援截圖。")
                    else:
                        self.last_file = value[1]
                        self.set_status("截圖已儲存：{path}", path=self.last_file)
                        if value[2]:
                            try:
                                os.startfile(str(self.last_file.resolve()))
                            except OSError as exc:
                                self.show_warning("圖片已儲存", self.tr("無法自動開啟圖片，可從儲存資料夾查看。\n\n{error}", error=error_text(exc, self.language)), parent=self.root)
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def close(self):
        if self.busy:
            self.set_status("請等目前操作完成；搜尋中可按「停止搜尋」。")
            return
        self.remember()
        self.root.destroy()


def main():
    root = tk.Tk()
    if "--smoke-test" in sys.argv:
        # Exercise the bundled Tcl/Tk and all widgets without network or settings writes.
        app = App(root, persist=False)
        root.update()
        root.destroy()
        return
    App(root)
    root.mainloop()
