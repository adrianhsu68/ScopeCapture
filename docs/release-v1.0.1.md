ScopeCapture v1.0.1 fixes the default language on first launch on Chinese Windows systems.

## Fixed

- Read the Windows user UI language using GetUserDefaultUILanguage instead of relying on Python's regional locale name.
- Chinese display languages now select Traditional Chinese on a fresh installation; other display languages select English.
- Handle names such as Chinese (Traditional)_Taiwan in the locale fallback if the Windows API is unavailable.
- Preserve existing saved language choices.
- Add regression tests for Windows language IDs, differing regional/UI languages, fallback behavior, and a fresh app launch.

Download ScopeCapture-Windows-x64.zip, extract it, and replace the old EXE. The ZIP contains bilingual guides and license notices. SHA256SUMS.txt includes checksums for the EXE and ZIP. The EXE remains unsigned.

Hardware support is unchanged: DSOX1204A is hardware-tested and EDUX1052A has been confirmed working on hardware by a user. Other listed models still await hardware verification.

## 繁體中文

修正繁中 Windows 新使用者首次開啟卻顯示英文的問題：改以 Windows 顯示語言判斷，並補上回歸測試。已儲存的語言選擇會保留。下載 ZIP 解壓縮後替換舊 EXE 即可。

EDUX1052A 已由使用者實機確認可用，這項標示維持不變。
