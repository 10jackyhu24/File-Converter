# File Converter

以 Flask、原生 HTML/CSS/JavaScript 製作的本機檔案轉換工具。介面支援繁體中文、英文、日文，所有檔案都只在自己的電腦上處理。

## 快速啟動（Windows）

1. 安裝 [Python 3.11+](https://www.python.org/downloads/) 與 [FFmpeg](https://ffmpeg.org/download.html)，並將兩者加入 `PATH`。
2. 雙擊 `start.bat`。第一次啟動會自動建立 `.venv` 並安裝 Python 套件。
3. 瀏覽器開啟 <http://127.0.0.1:5000>。

也可以手動啟動：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## 功能

- 圖片：指定大小壓縮、轉 PDF、添加雜訊、模糊處理
- 影片：指定大小壓縮、每秒提取圖片、提取不同品質的音檔
- 音檔：以 dB 調整音量
- PDF：依拖曳順序連接、逐頁轉成 PNG
- 多檔輸出會自動打包為 ZIP
- 工作檔會在 24 小時後，於下次存取服務時自動清理

## 注意事項

- 單次請求上限為 2 GB、最多 50 個檔案。
- 影片壓縮使用雙階段 H.264 編碼，較大檔案需要較長處理時間。
- 「提取圖片」每秒擷取一張 JPG；長影片可能產生大量圖片。
- 開發伺服器僅綁定 `127.0.0.1`，不會公開到區域網路。
