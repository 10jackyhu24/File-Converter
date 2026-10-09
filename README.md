# File Converter

以 Flask、原生 HTML/CSS/JavaScript 製作的本機檔案轉換工具。介面支援繁體中文、英文、日文，所有檔案都只在自己的電腦上處理。

## 快速啟動（Windows）

1. 安裝 [Python 3.11+](https://www.python.org/downloads/)、[FFmpeg](https://ffmpeg.org/download.html) 與 [Caddy](https://caddyserver.com/docs/install)，並將三者加入 `PATH`。
2. 雙擊 `start.bat`。第一次啟動會自動建立 `.venv` 並安裝 Python 套件。
3. 瀏覽器開啟 <https://localhost/>。`start.bat` 會同時啟動 Caddy 與僅供本機存取的 Flask 服務；關閉啟動視窗可結束兩者。

Caddy 使用本機憑證機構簽發 HTTPS 憑證。若瀏覽器顯示憑證不受信任，請以系統管理員身分執行 `caddy trust`，再重新開啟瀏覽器。首次執行時，Windows 防火牆可能詢問是否允許 Caddy 連線。

若執行 `caddy version` 時出現「blocked by your organization's Device Guard policy」，代表 Windows 應用程式控制政策阻止 Caddy 執行；WinGet 安裝成功也不代表執行已獲准。請將錯誤訊息與事件檢視器 `Microsoft-Windows-CodeIntegrity/Operational` 中對應的 3077 事件提供給裝置管理員，請其依組織政策核准 Caddy。在獲准前，`start.bat` 無法啟動 HTTPS 服務。

也可以手動啟動：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_https.py
```

## 功能

- 圖片：指定大小壓縮、轉 PDF、添加雜訊、模糊處理
- 影片：指定大小壓縮、每分鐘或自訂長度分割影片、每秒或每一幀提取圖片、提取不同品質的音檔
- 音檔：以 dB 調整音量
- PDF：指定大小壓縮（優先無損最佳化）、逐頁轉成 PNG、依拖曳順序連接
- Markdown：轉 PDF，可設定直向／橫向、1～3 欄、頁面邊界、頁碼位置及一般文字大小（小／中／大／自訂 6～16 pt），並提供「預設」與「Codebook」一鍵版面；支援中英日文、表格、對齊的程式碼行數與語法著色，以及 `$...$`／`$$...$$` LaTeX 公式
- 多檔輸出會自動打包為 ZIP
- 上傳與轉檔皆顯示實際百分比進度，影片處理會同步讀取 FFmpeg 進度
- 工作檔會在 24 小時後，於下次存取服務時自動清理

## 注意事項

- 單次請求上限為 2 GB、最多 50 個檔案。
- 影片壓縮使用雙階段 H.264 編碼，較大檔案需要較長處理時間。
- 「提取圖片」可選擇每秒一張或每一幀；逐幀模式處理時間較長，並可能產生大量圖片。
- Markdown 轉 PDF 需要 Microsoft Edge、Google Chrome 或 Chromium；Windows 通常已內建 Edge。若瀏覽器位於自訂位置，可設定 `FILE_CONVERTER_BROWSER` 環境變數。
- Flask 僅監聽 `127.0.0.1:5000`；請透過 Caddy 的 `https://localhost/` 或 `https://127.0.0.1/` 使用工具，不要直接連接 5000 埠。
- `run_https.py` 啟動時會自動偵測預設網路介面的區網 IPv4 位址，將其加入 Caddy 的 HTTPS 網站位址，並在視窗顯示可供其他裝置使用的 `https://<區網 IP>/`。換網路或換主機後重新啟動 `start.bat` 即可；其他裝置仍須信任 Caddy 的根憑證，且主機防火牆須允許 443 埠。Caddy 的根憑證通常位於 `%APPDATA%\Caddy\pki\authorities\local\root.crt`，只在信任的裝置上安裝此憑證。
