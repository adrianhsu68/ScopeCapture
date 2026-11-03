ScopeCapture v1.0.0 is the first public release of a small bilingual Windows app for saving Keysight oscilloscope screenshots.

## Download

Download **ScopeCapture-Windows-x64.zip**, extract it, and run **ScopeCapture.exe**. The ZIP includes English/Chinese user guides and license notices. Python, VISA, and Keysight IO Libraries are not required on the target computer.

## Included

- IPv4 subnet discovery and direct IP connection over TCP 5025.
- Instrument selection and remembered preferences, with model/serial checks before capture.
- Black/white backgrounds with Ink Saver restoration.
- Timestamped color PNGs and optional automatic image opening.
- English and Traditional Chinese, switchable without restarting.

## Verification and limits

- DSOX1204A: hardware-tested discovery, capture, backgrounds, and restoration.
- EDUX1052A: confirmed working on hardware by a user.
- EDUX1052G, DSOX1202A/G, DSOX1204G: implemented from the shared programming guide; hardware verification pending.
- Windows x64 only; USB connections are not implemented. The EXE is unsigned.
- SHA256SUMS.txt contains checksums for both the EXE and ZIP.

## 繁體中文

第一個公開版本，提供免安裝 Windows 截圖工具、繁中／英文切換、儀器搜尋與記憶、黑白背景及自動存圖。下載 ZIP 解壓縮後執行 EXE 即可，不需要另外安裝 Python 或 VISA。

DSOX1204A 已完成實機驗證，EDUX1052A 已由使用者確認可用；其餘列出的型號尚待實機驗證。本版尚無數位簽章，亦未實作 USB 連線。
