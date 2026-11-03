"""Desktop translations. Protocol values and saved paths never depend on language."""
import locale

LANGUAGES = {"繁體中文": "zh_TW", "English": "en"}
ENGLISH = {
    "示波器截圖 · ScopeCapture": "Oscilloscope Capture · ScopeCapture",
    "把示波器畫面，存到這台電腦": "Oscilloscope screenshots",
    "第一次先搜尋並選擇儀器；下次開啟會記住你的選擇。": "Find and select a scope once. Your selection is remembered next time.",
    "1  選擇示波器": "1  Select an oscilloscope",
    "搜尋網段": "Subnet",
    "搜尋示波器": "Find scopes",
    "停止搜尋": "Stop search",
    "搜尋指定網段的儀器（TCP 5025）。不同網段可自行輸入，或在下方直接輸入 IP。": "Search a subnet over TCP 5025. Enter another subnet, or connect directly by IP below.",
    "型號": "Model",
    "序號（辨識哪一台）": "Serial number",
    "IP 位址": "IP address",
    "截圖支援": "Screenshot support",
    "直接輸入 IP": "Connect by IP",
    "辨識並選取": "Identify & select",
    "尚未選擇示波器": "No oscilloscope selected",
    "2  儲存圖片": "2  Save screenshots",
    "選擇資料夾…": "Choose folder…",
    "開啟資料夾": "Open folder",
    "截圖完成後自動開啟圖片": "Open the image after capture",
    "截圖背景": "Background",
    "黑底（螢幕原貌）": "Black (screen colors)",
    "白底（適合列印）": "White (print friendly)",
    "擷取截圖": "Capture screenshot",
    "請搜尋示波器，或輸入示波器的 IP。": "Find an oscilloscope, or enter its IP address.",
    "已載入上次選擇；按「擷取截圖」時會確認儀器型號與序號。": "Last selection loaded. The model and serial number will be checked before capture.",
    "無法記住設定": "Could not save preferences",
    "目前仍可使用，但下次不會保留這次設定。\n\n{error}": "You can keep using the app, but these preferences may not be remembered.\n\n{error}",
    "可擷取": "Supported",
    "尚未支援": "Not supported",
    "目前選擇：{model}  /  {serial}  /  {host}": "Selected: {model}  /  {serial}  /  {host}",
    "網段格式": "Invalid subnet",
    "請輸入 IPv4 網段（最多 1024 個位址），例如 192.168.1.0/24。": "Enter an IPv4 subnet with at most 1024 addresses, for example 192.168.1.0/24.",
    "正在搜尋 {network}…": "Searching {network}…",
    "正在停止搜尋…": "Stopping search…",
    "IP 格式": "Invalid IP address",
    "請輸入示波器的 IPv4 位址，例如 192.168.1.100。": "Enter the oscilloscope's IPv4 address, for example 192.168.1.100.",
    "正在辨識 {host}…": "Identifying {host}…",
    "選擇截圖儲存資料夾": "Choose a screenshot folder",
    "無法開啟資料夾": "Could not open folder",
    "儲存位置": "Save location",
    "請先選擇儲存資料夾。": "Choose a folder for screenshots first.",
    "正在確認 {model} / {serial} 並讀取畫面…": "Checking {model} / {serial} and reading the screen…",
    "搜尋中：已檢查 {done} / {total} 個位址。請從清單選擇要使用的儀器。": "Searching: {done} / {total} addresses checked. Select your instrument from the list.",
    "未完成。請確認示波器已開機、接上網路，且 IP／搜尋網段正確。": "Not completed. Check power, network connection, and the IP address or subnet.",
    "操作未完成": "Operation not completed",
    "已停止搜尋，本次找到 {count} 台儀器。清單保留上次選擇；找不到時可直接輸入 IP。": "Search stopped. Found {count} instrument(s). Last selection is kept; you can also enter an IP.",
    "搜尋完成，本次找到 {count} 台儀器。清單保留上次選擇；找不到時可直接輸入 IP。": "Search complete. Found {count} instrument(s). Last selection is kept; you can also enter an IP.",
    "已辨識並記住這台儀器。可以擷取截圖。": "Instrument identified and remembered. Ready to capture.",
    "已辨識並記住這台儀器。這個型號尚未支援截圖。": "Instrument identified and remembered. Screenshots are not supported for this model yet.",
    "截圖已儲存：{path}": "Screenshot saved: {path}",
    "圖片已儲存": "Image saved",
    "無法自動開啟圖片，可從儲存資料夾查看。\n\n{error}": "Could not open the image automatically. You can find it in the screenshot folder.\n\n{error}",
    "請等目前操作完成；搜尋中可按「停止搜尋」。": "Wait for the current operation to finish. You can stop an active search.",
    "儀器未回覆有效的型號與序號。": "The instrument did not return a valid model and serial number.",
    "儀器回覆逾時。": "The instrument did not respond in time.",
    "儀器在資料傳完前中斷連線。": "The instrument disconnected before the transfer was complete.",
    "儀器文字回覆過長。": "The instrument's text response is too long.",
    "儀器未回覆有效的截圖背景設定。": "The instrument did not return a valid Ink Saver setting.",
    "儀器未套用指定的截圖背景設定。": "The instrument did not apply the requested screenshot background.",
    "截圖背景必須是 black 或 white。": "The screenshot background must be black or white.",
    "截圖連線中斷或回覆不完整，未繼續傳送還原指令。儀器的省墨設定可能已改變，請在面板確認。": "The screenshot connection failed or its response was incomplete. No further commands were sent. Ink Saver may have changed; check it on the instrument's front panel.",
    "無法確認已還原儀器的省墨設定；請在面板確認後重試截圖。": "Could not confirm that Ink Saver was restored. Check the setting on the instrument's front panel before trying again.",
    "儀器未回覆 PNG 資料，請確認型號與遠端控制設定。": "The instrument did not return PNG data. Check its model and remote-control settings.",
    "儀器回覆的資料長度格式錯誤。": "The instrument returned an invalid binary-block length.",
    "儀器回覆的圖片大小異常。": "The instrument returned an invalid image size.",
    "圖片資料結尾格式錯誤。": "The image response has an invalid terminator.",
    "收到的資料不是 PNG 圖片。": "The received data is not a PNG image.",
    "圖片資料校驗失敗，請重新截圖。": "The image checksum failed. Capture the screen again.",
    "PNG 圖片標頭無效。": "The PNG image header is invalid.",
    "圖片資料不完整，請重新截圖。": "The image is incomplete. Capture the screen again.",
    "請輸入 IPv4 網段，範圍最多 1024 個位址，例如 192.168.1.0/24。": "Enter an IPv4 subnet with at most 1024 addresses, for example 192.168.1.0/24.",
    "這個型號尚未支援截圖。目前支援 Keysight EDUX1052A/G、DSOX1202A/G、DSOX1204A/G。": "Screenshots are not supported for this model. Supported models: Keysight EDUX1052A/G, DSOX1202A/G, DSOX1204A/G.",
    "這個 IP 的儀器與記住的型號／序號不同。請重新搜尋並選擇正確的示波器。": "The model or serial number at this IP does not match your saved selection. Search again and select the correct oscilloscope.",
    "系統操作失敗（錯誤代碼 {code}）。請檢查網路連線、儲存位置及存取權限。": "A system operation failed (error code {code}). Check the network connection, save location, and access permissions.",
}
_SOURCE = {value: key for key, value in ENGLISH.items()}


def default_language():
    try:
        return "zh_TW" if (locale.getlocale()[0] or "").lower().startswith("zh") else "en"
    except (ValueError, TypeError):
        return "en"


def translate(message, language="zh_TW", **values):
    source = _SOURCE.get(message, message)
    template = ENGLISH.get(source, source) if language == "en" else source
    return template.format(**values) if values else template


def error_text(error, language):
    message = str(error)
    if message in ENGLISH:
        return translate(message, language)
    # Windows system errors follow the OS language. Give English users an
    # English explanation and the error code, rather than untranslated OS text.
    if language == "en" and isinstance(error, OSError):
        if isinstance(error, TimeoutError):
            return translate("儀器回覆逾時。", language)
        return translate("系統操作失敗（錯誤代碼 {code}）。請檢查網路連線、儲存位置及存取權限。",
                         language, code=getattr(error, "winerror", None) or error.errno or type(error).__name__)
    return message
