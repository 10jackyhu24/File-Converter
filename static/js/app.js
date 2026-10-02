"use strict";

const translations = {
  "zh-Hant": {
    fileType: "檔案類型", image: "圖片", video: "影片", audio: "音檔", privacy: "檔案只會保留 24 小時",
    selectLanguage: "選擇語言", themeToDark: "切換至深色模式", themeToLight: "切換至淺色模式",
    mode: "轉換模式", upload: "上傳", settings: "設定", download: "下載", back: "重新選擇",
    dropTitle: "拖曳檔案到這裡", or: "或", browse: "選擇檔案", selectedFiles: "已選檔案",
    addMore: "加入更多", next: "下一步", uploadedFiles: "已上傳的檔案", dragSort: "拖曳即可調整順序",
    conversionOptions: "轉換選項", currentSetting: "目前設定", convertNow: "開始轉換", delete: "刪除",
    processing: "正在處理檔案", processingHint: "所需時間取決於檔案大小，請不要關閉頁面。",
    uploading: "正在上傳檔案…", preparing: "準備轉換…", processingFile: "正在處理", finalizing: "正在整理輸出檔案…",
    allDone: "全部完成", conversionComplete: "轉換完成！", downloadFile: "下載檔案", convertMore: "轉換其他檔案",
    uploadFailed: "上傳失敗，請再試一次。", convertFailed: "轉換失敗，請再試一次。", invalidType: "請選擇符合目前分類的檔案。",
    noFiles: "請先選擇檔案。", minTwoPdf: "連接 PDF 至少需要兩個檔案。", confirmDeleteLast: "已刪除最後一個檔案，請重新上傳。",
    hint_image: "支援 JPG、PNG、WEBP、BMP、TIFF、GIF",
    hint_video: "支援 MP4、MOV、AVI、MKV、WEBM、MPEG",
    hint_audio: "支援 MP3、WAV、M4A、AAC、OGG、FLAC、OPUS",
    hint_pdf: "支援 PDF；連接時可拖曳調整頁面順序",
    m_image_compress: "壓縮檔案大小", m_image_to_pdf: "轉 PDF", m_image_noise: "添加雜訊", m_image_blur: "模糊處理",
    m_video_compress: "壓縮檔案大小", m_video_split: "分割影片", m_video_extract_frames: "提取圖片", m_video_extract_audio: "提取音檔",
    m_audio_volume: "音量調整", m_pdf_compress: "壓縮檔案大小", m_pdf_merge: "連接 PDF", m_pdf_to_images: "轉圖片",
    title_image_compress: "壓縮圖片", title_image_to_pdf: "圖片轉 PDF", title_image_noise: "為圖片添加雜訊", title_image_blur: "模糊圖片",
    title_video_compress: "壓縮影片", title_video_split: "分割影片", title_video_extract_frames: "從影片提取圖片", title_video_extract_audio: "從影片提取音檔",
    title_audio_volume: "調整音量", title_pdf_compress: "壓縮 PDF", title_pdf_merge: "連接 PDF", title_pdf_to_images: "PDF 轉圖片",
    desc_image_compress: "上傳圖片並設定需要的檔案大小。", desc_image_to_pdf: "依照排列順序，將多張圖片合成一份 PDF。",
    desc_image_noise: "用可調整的比例為圖片加入隨機顆粒。", desc_image_blur: "套用高斯模糊，像素越高效果越強。",
    desc_video_compress: "在盡量保留畫質的前提下縮小影片檔案。", desc_video_split: "依照指定時間將影片精準分割，並將所有片段打包下載。", desc_video_extract_frames: "將影片畫面提取為高畫質 JPG 圖片並打包下載。",
    desc_video_extract_audio: "將影片中的聲音輸出成 MP3 或無損 FLAC。", desc_audio_volume: "以 dB 為單位增加或降低音檔音量。",
    desc_pdf_compress: "優先進行無損最佳化，必要時才逐級壓縮內嵌圖片，保留文字與向量清晰度。", desc_pdf_merge: "拖曳調整檔案順序，再合併成單一 PDF。", desc_pdf_to_images: "將 PDF 每一頁轉為高解析 PNG 圖片。",
    oh_target: "選擇壓縮後的檔案大小", oh_noise: "選擇雜訊強度", oh_blur: "選擇模糊程度", oh_audio: "選擇輸出音質",
    oh_volume: "設定音量變化", oh_order: "確認檔案順序", oh_ready: "確認轉換設定", oh_frames: "選擇圖片提取頻率", oh_segments: "選擇每段影片長度",
    preset_discord: "20 MB (Discord)", customSize: "自訂大小", custom: "自訂", weak: "弱", medium: "中", strong: "強",
    ratio5: "比例 5%", ratio10: "比例 10%", ratio20: "比例 20%", pixels2: "2 像素", pixels10: "10 像素", pixels30: "30 像素",
    low: "低", high: "高", lossless: "無損", kbps64: "64 kbps", kbps128: "128 kbps", kbps256: "256 kbps", losslessFlac: "FLAC 原始品質",
    volumeChange: "增加或降低", positiveHint: "正數增加、負數降低，範圍 -30～30 dB",
    single_to_pdf: "合併成一份 PDF", single_to_pdf_desc: "將依照上方檔案順序建立 PDF，每張圖片一頁。",
    single_frames: "每秒提取一張圖片", single_frames_desc: "圖片將以 JPG 格式存入 ZIP 壓縮檔。",
    frameSecond: "每秒一張", frameSecondDetail: "適合快速預覽，輸出數量較少", frameEvery: "每一幀", frameEveryDetail: "保留影片的所有畫面，可能產生大量檔案",
    instagramStory: "Instagram Story", instagramStoryDetail: "每 1 分鐘分割一段", customSegment: "自訂每段長度", customSegmentDetail: "輸入每段影片的分鐘數", minuteUnit: "分鐘",
    single_merge: "依目前順序連接", single_merge_desc: "第一個檔案會出現在合併結果的最前面。",
    single_pdf_images: "將每一頁轉為 PNG", single_pdf_images_desc: "輸出為 144 DPI 圖片並集中打包成 ZIP。",
    customValue: "自訂數值", filesUnit: "個檔案"
  },
  en: {
    fileType: "FILE TYPE", image: "Images", video: "Videos", audio: "Audio", privacy: "Files are retained for 24 hours only",
    selectLanguage: "Select language", themeToDark: "Switch to dark mode", themeToLight: "Switch to light mode",
    mode: "CONVERSION MODE", upload: "Upload", settings: "Settings", download: "Download", back: "Choose again",
    dropTitle: "Drop files here", or: "or", browse: "Browse files", selectedFiles: "Selected files",
    addMore: "Add more", next: "Next", uploadedFiles: "UPLOADED FILES", dragSort: "Drag to reorder files",
    conversionOptions: "CONVERSION OPTIONS", currentSetting: "CURRENT SETTING", convertNow: "Convert now", delete: "Delete",
    processing: "Processing your files", processingHint: "This may take a while depending on file size. Please keep this page open.",
    uploading: "Uploading files…", preparing: "Preparing conversion…", processingFile: "Processing", finalizing: "Finalizing output…",
    allDone: "ALL DONE", conversionComplete: "Conversion complete!", downloadFile: "Download file", convertMore: "Convert more files",
    uploadFailed: "Upload failed. Please try again.", convertFailed: "Conversion failed. Please try again.", invalidType: "Choose files matching the current category.",
    noFiles: "Choose at least one file first.", minTwoPdf: "Merging PDFs requires at least two files.", confirmDeleteLast: "The last file was removed. Please upload again.",
    hint_image: "Supports JPG, PNG, WEBP, BMP, TIFF and GIF",
    hint_video: "Supports MP4, MOV, AVI, MKV, WEBM and MPEG",
    hint_audio: "Supports MP3, WAV, M4A, AAC, OGG, FLAC and OPUS",
    hint_pdf: "Supports PDF; drag to set the merge order",
    m_image_compress: "Compress size", m_image_to_pdf: "Convert to PDF", m_image_noise: "Add noise", m_image_blur: "Blur",
    m_video_compress: "Compress size", m_video_split: "Split video", m_video_extract_frames: "Extract images", m_video_extract_audio: "Extract audio",
    m_audio_volume: "Adjust volume", m_pdf_compress: "Compress size", m_pdf_merge: "Merge PDFs", m_pdf_to_images: "Convert to images",
    title_image_compress: "Compress images", title_image_to_pdf: "Images to PDF", title_image_noise: "Add image noise", title_image_blur: "Blur images",
    title_video_compress: "Compress videos", title_video_split: "Split video", title_video_extract_frames: "Extract video frames", title_video_extract_audio: "Extract video audio",
    title_audio_volume: "Adjust audio volume", title_pdf_compress: "Compress PDFs", title_pdf_merge: "Merge PDFs", title_pdf_to_images: "PDF to images",
    desc_image_compress: "Upload images and choose a target file size.", desc_image_to_pdf: "Combine images into one PDF in the displayed order.",
    desc_image_noise: "Add adjustable random grain to your images.", desc_image_blur: "Apply Gaussian blur; a higher pixel value creates a stronger effect.",
    desc_video_compress: "Reduce video size while preserving as much quality as possible.", desc_video_split: "Split videos precisely at the selected interval and download all clips as a ZIP file.", desc_video_extract_frames: "Extract video frames as high-quality JPG images in a ZIP file.",
    desc_video_extract_audio: "Export the video's sound as MP3 or lossless FLAC.", desc_audio_volume: "Increase or reduce audio volume in decibels.",
    desc_pdf_compress: "Starts with lossless optimization, then gradually compresses embedded images only when needed, preserving text and vectors.", desc_pdf_merge: "Drag files into the right order, then merge them into one PDF.", desc_pdf_to_images: "Turn every PDF page into a high-resolution PNG image.",
    oh_target: "Choose the target file size", oh_noise: "Choose noise strength", oh_blur: "Choose blur strength", oh_audio: "Choose output quality",
    oh_volume: "Set the volume change", oh_order: "Confirm file order", oh_ready: "Confirm conversion settings", oh_frames: "Choose the frame extraction rate", oh_segments: "Choose the length of each clip",
    preset_discord: "20 MB (Discord)", customSize: "Custom size", custom: "Custom", weak: "Low", medium: "Medium", strong: "High",
    ratio5: "5% ratio", ratio10: "10% ratio", ratio20: "20% ratio", pixels2: "2 pixels", pixels10: "10 pixels", pixels30: "30 pixels",
    low: "Low", high: "High", lossless: "Lossless", kbps64: "64 kbps", kbps128: "128 kbps", kbps256: "256 kbps", losslessFlac: "Original-quality FLAC",
    volumeChange: "Increase or reduce", positiveHint: "Positive increases, negative reduces; -30 to 30 dB",
    single_to_pdf: "Combine into one PDF", single_to_pdf_desc: "A PDF will be created in the order above, one image per page.",
    single_frames: "Extract one image per second", single_frames_desc: "JPG images will be placed in a ZIP archive.",
    frameSecond: "One per second", frameSecondDetail: "Best for quick previews with fewer output files", frameEvery: "Every frame", frameEveryDetail: "Keeps every video frame and may create many files",
    instagramStory: "Instagram Story", instagramStoryDetail: "Split into one-minute clips", customSegment: "Custom clip length", customSegmentDetail: "Enter the number of minutes per clip", minuteUnit: "min",
    single_merge: "Merge in the current order", single_merge_desc: "The first file above will appear first in the merged result.",
    single_pdf_images: "Convert every page to PNG", single_pdf_images_desc: "144-DPI images will be bundled in a ZIP archive.",
    customValue: "Custom value", filesUnit: "files"
  },
  ja: {
    fileType: "ファイル種類", image: "画像", video: "動画", audio: "音声", privacy: "ファイルは24時間後に削除されます",
    selectLanguage: "言語を選択", themeToDark: "ダークモードに切り替え", themeToLight: "ライトモードに切り替え",
    mode: "変換モード", upload: "アップロード", settings: "設定", download: "ダウンロード", back: "選び直す",
    dropTitle: "ファイルをここにドロップ", or: "または", browse: "ファイルを選択", selectedFiles: "選択したファイル",
    addMore: "追加", next: "次へ", uploadedFiles: "アップロード済み", dragSort: "ドラッグして順番を変更",
    conversionOptions: "変換オプション", currentSetting: "現在の設定", convertNow: "変換を開始", delete: "削除",
    processing: "ファイルを処理しています", processingHint: "ファイルサイズにより時間がかかります。このページを閉じないでください。",
    uploading: "ファイルをアップロード中…", preparing: "変換を準備中…", processingFile: "処理中", finalizing: "出力ファイルを作成中…",
    allDone: "完了", conversionComplete: "変換が完了しました！", downloadFile: "ダウンロード", convertMore: "別のファイルを変換",
    uploadFailed: "アップロードに失敗しました。", convertFailed: "変換に失敗しました。", invalidType: "現在のカテゴリに合うファイルを選択してください。",
    noFiles: "先にファイルを選択してください。", minTwoPdf: "PDFの結合には2つ以上のファイルが必要です。", confirmDeleteLast: "最後のファイルを削除しました。再度アップロードしてください。",
    hint_image: "JPG、PNG、WEBP、BMP、TIFF、GIF に対応",
    hint_video: "MP4、MOV、AVI、MKV、WEBM、MPEG に対応",
    hint_audio: "MP3、WAV、M4A、AAC、OGG、FLAC、OPUS に対応",
    hint_pdf: "PDF に対応；ドラッグで結合順を変更できます",
    m_image_compress: "サイズ圧縮", m_image_to_pdf: "PDFに変換", m_image_noise: "ノイズ追加", m_image_blur: "ぼかし",
    m_video_compress: "サイズ圧縮", m_video_split: "動画を分割", m_video_extract_frames: "画像を抽出", m_video_extract_audio: "音声を抽出",
    m_audio_volume: "音量調整", m_pdf_compress: "サイズ圧縮", m_pdf_merge: "PDFを結合", m_pdf_to_images: "画像に変換",
    title_image_compress: "画像を圧縮", title_image_to_pdf: "画像をPDFに変換", title_image_noise: "画像にノイズを追加", title_image_blur: "画像をぼかす",
    title_video_compress: "動画を圧縮", title_video_split: "動画を分割", title_video_extract_frames: "動画から画像を抽出", title_video_extract_audio: "動画から音声を抽出",
    title_audio_volume: "音量を調整", title_pdf_compress: "PDFを圧縮", title_pdf_merge: "PDFを結合", title_pdf_to_images: "PDFを画像に変換",
    desc_image_compress: "画像をアップロードして目標サイズを設定します。", desc_image_to_pdf: "表示順に複数の画像を1つのPDFにまとめます。",
    desc_image_noise: "調整可能なランダムノイズを画像に追加します。", desc_image_blur: "ガウスぼかしを適用します。ピクセル値が高いほど強くなります。",
    desc_video_compress: "画質をできるだけ保ちながら動画サイズを縮小します。", desc_video_split: "指定した時間ごとに動画を正確に分割し、ZIPにまとめます。", desc_video_extract_frames: "動画のフレームを高画質JPGとして抽出しZIPにまとめます。",
    desc_video_extract_audio: "動画の音声をMP3またはFLACで書き出します。", desc_audio_volume: "dB単位で音量を上げ下げします。",
    desc_pdf_compress: "まず可逆最適化を行い、必要な場合のみ埋め込み画像を段階的に圧縮して文字とベクターを保持します。", desc_pdf_merge: "ドラッグで順番を整え、1つのPDFに結合します。", desc_pdf_to_images: "PDFの各ページを高解像度PNGに変換します。",
    oh_target: "変換後のファイルサイズ", oh_noise: "ノイズ強度", oh_blur: "ぼかし強度", oh_audio: "出力音質",
    oh_volume: "音量の変化", oh_order: "ファイル順を確認", oh_ready: "変換設定を確認", oh_frames: "画像の抽出頻度を選択", oh_segments: "各クリップの長さを選択",
    preset_discord: "20 MB (Discord)", customSize: "カスタムサイズ", custom: "カスタム", weak: "弱", medium: "中", strong: "強",
    ratio5: "比率 5%", ratio10: "比率 10%", ratio20: "比率 20%", pixels2: "2 ピクセル", pixels10: "10 ピクセル", pixels30: "30 ピクセル",
    low: "低", high: "高", lossless: "ロスレス", kbps64: "64 kbps", kbps128: "128 kbps", kbps256: "256 kbps", losslessFlac: "FLAC オリジナル品質",
    volumeChange: "上げる・下げる", positiveHint: "正数で上げ、負数で下げます（-30～30 dB）",
    single_to_pdf: "1つのPDFに結合", single_to_pdf_desc: "上の順番で、画像1枚につき1ページのPDFを作成します。",
    single_frames: "1秒ごとに画像を抽出", single_frames_desc: "JPG画像をZIPファイルにまとめます。",
    frameSecond: "1秒ごとに1枚", frameSecondDetail: "プレビュー向けで、出力ファイル数を抑えます", frameEvery: "すべてのフレーム", frameEveryDetail: "全画面を保持するため、大量のファイルになる場合があります",
    instagramStory: "Instagram Story", instagramStoryDetail: "1分ごとに分割", customSegment: "長さを指定", customSegmentDetail: "クリップごとの分数を入力", minuteUnit: "分",
    single_merge: "現在の順番で結合", single_merge_desc: "上の最初のファイルが結合結果の先頭になります。",
    single_pdf_images: "すべてのページをPNGに変換", single_pdf_images_desc: "144 DPI画像をZIPファイルにまとめます。",
    customValue: "カスタム値", filesUnit: "ファイル"
  }
};

const categoryConfig = {
  image: {
    accept: ".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.gif",
    extensions: ["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"],
    modes: [
      { id: "compress", label: "m_image_compress", title: "title_image_compress", desc: "desc_image_compress", heading: "oh_target", field: "target_mb", defaultValue: 20,
        options: [{ value: 20, label: "preset_discord", detail: "20 MB" }, { value: "custom", label: "customSize", detail: "customValue", input: { unit: "MB", min: .1, max: 2048, step: .1, initial: 10 } }] },
      { id: "to_pdf", label: "m_image_to_pdf", title: "title_image_to_pdf", desc: "desc_image_to_pdf", heading: "oh_order", single: ["single_to_pdf", "single_to_pdf_desc"] },
      { id: "noise", label: "m_image_noise", title: "title_image_noise", desc: "desc_image_noise", heading: "oh_noise", field: "ratio", defaultValue: 5,
        options: [{ value: 5, label: "weak", detail: "ratio5" }, { value: 10, label: "medium", detail: "ratio10" }, { value: 20, label: "strong", detail: "ratio20" }, { value: "custom", label: "custom", detail: "customValue", input: { unit: "%", min: 0, max: 100, step: 1, initial: 15 } }] },
      { id: "blur", label: "m_image_blur", title: "title_image_blur", desc: "desc_image_blur", heading: "oh_blur", field: "pixels", defaultValue: 2,
        options: [{ value: 2, label: "weak", detail: "pixels2" }, { value: 10, label: "medium", detail: "pixels10" }, { value: 30, label: "strong", detail: "pixels30" }, { value: "custom", label: "custom", detail: "customValue", input: { unit: "px", min: 0, max: 100, step: 1, initial: 15 } }] }
    ]
  },
  video: {
    accept: ".mp4,.mov,.avi,.mkv,.webm,.m4v,.mpeg,.mpg",
    extensions: ["mp4", "mov", "avi", "mkv", "webm", "m4v", "mpeg", "mpg"],
    modes: [
      { id: "compress", label: "m_video_compress", title: "title_video_compress", desc: "desc_video_compress", heading: "oh_target", field: "target_mb", defaultValue: 20,
        options: [{ value: 20, label: "preset_discord", detail: "20 MB" }, { value: "custom", label: "customSize", detail: "customValue", input: { unit: "MB", min: .1, max: 2048, step: .1, initial: 100 } }] },
      { id: "split", label: "m_video_split", title: "title_video_split", desc: "desc_video_split", heading: "oh_segments", field: "segment_minutes", defaultValue: 1,
        options: [{ value: 1, label: "instagramStory", detail: "instagramStoryDetail" }, { value: "custom", label: "customSegment", detail: "customSegmentDetail", input: { unitKey: "minuteUnit", min: .01, max: 1440, step: .01, initial: 5 } }] },
      { id: "extract_frames", label: "m_video_extract_frames", title: "title_video_extract_frames", desc: "desc_video_extract_frames", heading: "oh_frames", field: "frame_mode", defaultValue: "second",
        options: [{ value: "second", label: "frameSecond", detail: "frameSecondDetail" }, { value: "all", label: "frameEvery", detail: "frameEveryDetail" }] },
      { id: "extract_audio", label: "m_video_extract_audio", title: "title_video_extract_audio", desc: "desc_video_extract_audio", heading: "oh_audio", field: "bitrate", defaultValue: 128,
        options: [{ value: 64, label: "low", detail: "kbps64" }, { value: 128, label: "medium", detail: "kbps128" }, { value: 256, label: "high", detail: "kbps256" }, { value: "lossless", label: "lossless", detail: "losslessFlac" }, { value: "custom", label: "custom", detail: "customValue", input: { unit: "kbps", min: 16, max: 512, step: 1, initial: 192 } }] }
    ]
  },
  audio: {
    accept: ".mp3,.wav,.m4a,.aac,.ogg,.flac,.opus", extensions: ["mp3", "wav", "m4a", "aac", "ogg", "flac", "opus"],
    modes: [
      { id: "volume", label: "m_audio_volume", title: "title_audio_volume", desc: "desc_audio_volume", heading: "oh_volume", field: "db", defaultValue: "custom",
        options: [{ value: "custom", label: "volumeChange", detail: "positiveHint", input: { unit: "dB", min: -30, max: 30, step: .5, initial: 3 } }] }
    ]
  },
  pdf: {
    accept: ".pdf", extensions: ["pdf"],
    modes: [
      { id: "compress", label: "m_pdf_compress", title: "title_pdf_compress", desc: "desc_pdf_compress", heading: "oh_target", field: "target_mb", defaultValue: 20,
        options: [{ value: 20, label: "preset_discord", detail: "20 MB" }, { value: "custom", label: "customSize", detail: "customValue", input: { unit: "MB", min: .1, max: 2048, step: .1, initial: 10 } }] },
      { id: "to_images", label: "m_pdf_to_images", title: "title_pdf_to_images", desc: "desc_pdf_to_images", heading: "oh_ready", single: ["single_pdf_images", "single_pdf_images_desc"] },
      { id: "merge", label: "m_pdf_merge", title: "title_pdf_merge", desc: "desc_pdf_merge", heading: "oh_order", single: ["single_merge", "single_merge_desc"] }
    ]
  }
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const elements = {
  categoryNav: $("#categoryNav"), modeTabs: $("#modeTabs"), fileInput: $("#fileInput"), dropzone: $("#dropzone"),
  pendingFiles: $("#pendingFiles"), pendingList: $("#pendingList"), pendingCount: $("#pendingCount"), addMoreButton: $("#addMoreButton"),
  nextButton: $("#nextButton"), uploadView: $("#uploadView"), convertView: $("#convertView"), backButton: $("#backButton"),
  pageTitle: $("#pageTitle"), pageDescription: $("#pageDescription"), eyebrow: $("#eyebrow"), fileHint: $("#fileHint"),
  fileCards: $("#fileCards"), fileCount: $("#fileCount"), optionsHeading: $("#optionsHeading"), optionList: $("#optionList"),
  selectionSummary: $("#selectionSummary"), convertButton: $("#convertButton"), languageButton: $("#languageButton"), languageCode: $("#languageCode"),
  languagePicker: $("#languagePicker"), languageMenu: $("#languageMenu"), themeButton: $("#themeButton"),
  progressModal: $("#progressModal"), resultModal: $("#resultModal"), resultFile: $("#resultFile"), downloadButton: $("#downloadButton"),
  progressBar: $("#progressBar"), progressPercent: $("#progressPercent"), progressStatus: $("#progressStatus"),
  startOverButton: $("#startOverButton"), toastRegion: $("#toastRegion"), sidebar: $("#sidebar"), mobileMenu: $("#mobileMenu")
};

const savedLocale = localStorage.getItem("file-converter-locale");
const state = {
  locale: translations[savedLocale] ? savedLocale : "zh-Hant",
  theme: document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  category: "image",
  mode: "compress",
  view: "upload",
  pendingFiles: [],
  uploadedFiles: [],
  jobId: null,
  selectedValue: 20,
  customValues: {},
  dragIndex: null
};

function t(key) {
  return translations[state.locale][key] || translations["zh-Hant"][key] || key;
}

function currentCategory() { return categoryConfig[state.category]; }
function currentMode() { return currentCategory().modes.find((item) => item.id === state.mode); }
function modeKey() { return `${state.category}.${state.mode}`; }

function applyTranslations() {
  document.documentElement.lang = state.locale === "zh-Hant" ? "zh-Hant" : state.locale;
  $$('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
  elements.languageCode.textContent = state.locale === "zh-Hant" ? "繁" : state.locale === "en" ? "EN" : "日";
  elements.languageButton.setAttribute("aria-label", t("selectLanguage"));
  elements.languageButton.title = t("selectLanguage");
  elements.languageMenu.querySelectorAll("[data-locale]").forEach((button) => {
    button.classList.toggle("active", button.dataset.locale === state.locale);
  });
  updateThemeButton();
  renderModeTabs();
  updateHeadings();
  if (state.view === "convert") {
    renderFileCards();
    renderOptions();
  } else {
    renderPendingFiles();
  }
}

function updateThemeButton() {
  const label = state.theme === "dark" ? t("themeToLight") : t("themeToDark");
  elements.themeButton.setAttribute("aria-label", label);
  elements.themeButton.title = label;
}

function setTheme(theme) {
  state.theme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = state.theme;
  document.querySelector('meta[name="theme-color"]').content = state.theme === "dark" ? "#0d171a" : "#12343b";
  localStorage.setItem("file-converter-theme", state.theme);
  updateThemeButton();
}

function closeLanguageMenu() {
  elements.languageMenu.classList.add("hidden");
  elements.languageButton.setAttribute("aria-expanded", "false");
}

function updateHeadings() {
  const mode = currentMode();
  elements.pageTitle.textContent = t(mode.title);
  elements.pageDescription.textContent = t(mode.desc);
  elements.eyebrow.textContent = `${state.category.toUpperCase()} CONVERTER`;
  elements.fileHint.textContent = t(`hint_${state.category}`);
  elements.fileInput.accept = currentCategory().accept;
  elements.optionsHeading.textContent = t(mode.heading);
}

function renderModeTabs() {
  elements.modeTabs.innerHTML = "";
  currentCategory().modes.forEach((mode) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `mode-tab${mode.id === state.mode ? " active" : ""}`;
    button.textContent = t(mode.label);
    button.addEventListener("click", () => setMode(mode.id));
    elements.modeTabs.append(button);
  });
}

function setCategory(category) {
  if (category === state.category) {
    elements.sidebar.classList.remove("open");
    return;
  }
  revokePreviews();
  state.category = category;
  state.mode = categoryConfig[category].modes[0].id;
  state.pendingFiles = [];
  state.uploadedFiles = [];
  state.jobId = null;
  setView("upload");
  resetModeSelection();
  $$(".category-button").forEach((button) => button.classList.toggle("active", button.dataset.category === category));
  elements.sidebar.classList.remove("open");
  renderModeTabs();
  renderPendingFiles();
  updateHeadings();
}

function setMode(mode) {
  state.mode = mode;
  resetModeSelection();
  renderModeTabs();
  updateHeadings();
  if (state.view === "convert") renderOptions();
}

function resetModeSelection() {
  const mode = currentMode();
  state.selectedValue = mode.defaultValue ?? null;
  if (mode.options) {
    const custom = mode.options.find((option) => option.input);
    if (custom && state.customValues[modeKey()] === undefined) state.customValues[modeKey()] = custom.input.initial;
  }
}

function extensionOf(name) { return name.includes(".") ? name.split(".").pop().toLowerCase() : ""; }

function addFiles(fileList) {
  const valid = [...fileList].filter((file) => currentCategory().extensions.includes(extensionOf(file.name)));
  if (valid.length !== fileList.length) showToast(t("invalidType"));
  const existing = new Set(state.pendingFiles.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
  valid.forEach((file) => {
    const signature = `${file.name}:${file.size}:${file.lastModified}`;
    if (!existing.has(signature) && state.pendingFiles.length < 50) {
      state.pendingFiles.push(file);
      existing.add(signature);
    }
  });
  renderPendingFiles();
}

function renderPendingFiles() {
  const hasFiles = state.pendingFiles.length > 0;
  elements.pendingFiles.classList.toggle("hidden", !hasFiles);
  elements.pendingCount.textContent = hasFiles ? `(${state.pendingFiles.length})` : "";
  elements.nextButton.disabled = !hasFiles;
  elements.pendingList.innerHTML = "";
  state.pendingFiles.forEach((file, index) => {
    const item = document.createElement("div");
    item.className = "pending-item";
    item.innerHTML = `<span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span><button type="button" aria-label="${t("delete")}">×</button>`;
    item.querySelector("button").addEventListener("click", () => {
      state.pendingFiles.splice(index, 1);
      renderPendingFiles();
    });
    elements.pendingList.append(item);
  });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const number = bytes / (1024 ** index);
  return `${number.toFixed(index === 0 || number >= 10 ? 0 : 1)} ${units[index]}`;
}

function uploadRequest(form) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload");
    xhr.responseType = "json";
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) setProgress(event.loaded / event.total * 100, t("uploading"));
    });
    xhr.addEventListener("load", () => {
      const result = xhr.response || {};
      if (xhr.status < 200 || xhr.status >= 300 || !result.ok) {
        reject(new Error(result.error || t("uploadFailed")));
        return;
      }
      resolve(result);
    });
    xhr.addEventListener("error", () => reject(new Error(t("uploadFailed"))));
    xhr.addEventListener("abort", () => reject(new Error(t("uploadFailed"))));
    xhr.send(form);
  });
}

async function uploadFiles() {
  if (!state.pendingFiles.length) return showToast(t("noFiles"));
  const form = new FormData();
  form.append("category", state.category);
  state.pendingFiles.forEach((file) => form.append("files", file, file.name));
  showProgress(0, t("uploading"));
  try {
    const result = await uploadRequest(form);
    setProgress(100, t("uploading"));
    state.jobId = result.job_id;
    state.uploadedFiles = result.files.map((file, index) => ({
      ...file,
      preview: state.category === "image" ? URL.createObjectURL(state.pendingFiles[index]) : null
    }));
    elements.progressModal.classList.add("hidden");
    setView("convert");
    renderFileCards();
    renderOptions();
  } catch (error) {
    elements.progressModal.classList.add("hidden");
    showToast(error.message || t("uploadFailed"));
  }
}

function setView(view) {
  state.view = view;
  const isUpload = view === "upload";
  elements.uploadView.classList.toggle("hidden", !isUpload);
  elements.convertView.classList.toggle("hidden", isUpload);
  elements.backButton.classList.toggle("hidden", isUpload);
  const steps = $$(".step");
  steps.forEach((step) => step.classList.toggle("active", Number(step.dataset.step) <= (isUpload ? 1 : 2)));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderFileCards() {
  elements.fileCards.innerHTML = "";
  elements.fileCount.textContent = `${state.uploadedFiles.length}`;
  state.uploadedFiles.forEach((file, index) => {
    const card = document.createElement("article");
    card.className = "file-card";
    card.draggable = true;
    card.dataset.index = index;
    const preview = file.preview
      ? `<img src="${file.preview}" alt="">`
      : `<svg><use href="#icon-${state.category === "pdf" ? "pdf" : state.category === "video" ? "video" : state.category === "audio" ? "audio" : "file"}"></use></svg>`;
    card.innerHTML = `
      <div class="file-preview">${preview}</div>
      <button class="more-button" type="button" aria-label="More"><svg><use href="#icon-more"></use></svg></button>
      <div class="file-menu hidden"><button type="button">${t("delete")}</button></div>
      <div class="file-details"><div class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div><div class="file-size">${formatBytes(file.size)}</div></div>`;
    const menu = card.querySelector(".file-menu");
    card.querySelector(".more-button").addEventListener("click", (event) => {
      event.stopPropagation();
      $$(".file-menu").forEach((other) => { if (other !== menu) other.classList.add("hidden"); });
      menu.classList.toggle("hidden");
    });
    menu.querySelector("button").addEventListener("click", () => deleteUploadedFile(file.id));
    card.addEventListener("dragstart", () => { state.dragIndex = index; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => { state.dragIndex = null; card.classList.remove("dragging"); $$(".file-card").forEach((item) => item.classList.remove("drag-over")); });
    card.addEventListener("dragover", (event) => { event.preventDefault(); if (state.dragIndex !== index) card.classList.add("drag-over"); });
    card.addEventListener("dragleave", () => card.classList.remove("drag-over"));
    card.addEventListener("drop", (event) => {
      event.preventDefault();
      card.classList.remove("drag-over");
      if (state.dragIndex === null || state.dragIndex === index) return;
      const [moved] = state.uploadedFiles.splice(state.dragIndex, 1);
      state.uploadedFiles.splice(index, 0, moved);
      renderFileCards();
    });
    elements.fileCards.append(card);
  });
}

async function deleteUploadedFile(fileId) {
  try {
    const response = await fetch(`/api/jobs/${state.jobId}/files/${fileId}`, { method: "DELETE" });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.ok) throw new Error(result.error || t("convertFailed"));
    const index = state.uploadedFiles.findIndex((file) => file.id === fileId);
    if (index >= 0) {
      if (state.uploadedFiles[index].preview) URL.revokeObjectURL(state.uploadedFiles[index].preview);
      state.uploadedFiles.splice(index, 1);
    }
    if (!state.uploadedFiles.length) {
      showToast(t("confirmDeleteLast"));
      startOver();
      return;
    }
    renderFileCards();
  } catch (error) {
    showToast(error.message);
  }
}

function inputUnit(input) {
  return input.unitKey ? t(input.unitKey) : input.unit;
}

function renderOptions() {
  const mode = currentMode();
  elements.optionsHeading.textContent = t(mode.heading);
  elements.optionList.innerHTML = "";
  if (mode.single) {
    const single = document.createElement("div");
    single.className = "single-option";
    single.innerHTML = `<span class="single-option-icon"><svg><use href="#icon-check"></use></svg></span><div><strong>${t(mode.single[0])}</strong><p>${t(mode.single[1])}</p></div>`;
    elements.optionList.append(single);
    elements.selectionSummary.textContent = t(mode.single[0]);
    return;
  }

  mode.options.forEach((option) => {
    const selected = String(state.selectedValue) === String(option.value);
    const row = document.createElement("div");
    row.className = `option-row${selected ? " selected" : ""}`;
    row.tabIndex = 0;
    row.setAttribute("role", "radio");
    row.setAttribute("aria-checked", selected ? "true" : "false");
    let input = "";
    if (option.input) {
      const value = state.customValues[modeKey()] ?? option.input.initial;
      input = `<label class="custom-field"><input type="number" min="${option.input.min}" max="${option.input.max}" step="${option.input.step}" value="${value}" aria-label="${t("customValue")}"><span>${inputUnit(option.input)}</span></label>`;
    }
    row.innerHTML = `<span class="radio-dot"></span><span class="option-copy"><strong>${t(option.label)}</strong><small>${t(option.detail)}</small></span>${input}`;
    const select = () => { state.selectedValue = option.value; renderOptions(); };
    row.addEventListener("click", (event) => { if (!event.target.matches("input")) select(); });
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
    const inputElement = row.querySelector("input");
    if (inputElement) {
      inputElement.addEventListener("focus", () => { state.selectedValue = option.value; row.classList.add("selected"); });
      inputElement.addEventListener("input", () => {
        state.selectedValue = option.value;
        state.customValues[modeKey()] = inputElement.value;
        updateSelectionSummary();
      });
      inputElement.addEventListener("click", (event) => event.stopPropagation());
    }
    elements.optionList.append(row);
  });
  updateSelectionSummary();
}

function updateSelectionSummary() {
  const mode = currentMode();
  const option = mode.options?.find((item) => String(item.value) === String(state.selectedValue));
  if (!option) return;
  if (option.input) {
    elements.selectionSummary.textContent = `${state.customValues[modeKey()] ?? option.input.initial} ${inputUnit(option.input)}`;
  } else {
    elements.selectionSummary.textContent = `${t(option.label)} · ${t(option.detail)}`;
  }
}

function conversionOptions() {
  const mode = currentMode();
  if (!mode.field) return {};
  const option = mode.options.find((item) => String(item.value) === String(state.selectedValue));
  let value = state.selectedValue;
  if (option?.input) {
    value = Number(state.customValues[modeKey()] ?? option.input.initial);
    if (!Number.isFinite(value) || value < option.input.min || value > option.input.max) {
      throw new Error(`${t("customValue")}: ${option.input.min}–${option.input.max} ${inputUnit(option.input)}`);
    }
  }
  return { [mode.field]: value };
}

async function convertFiles() {
  if (!state.uploadedFiles.length) return showToast(t("noFiles"));
  if (state.category === "pdf" && state.mode === "merge" && state.uploadedFiles.length < 2) return showToast(t("minTwoPdf"));
  let options;
  try { options = conversionOptions(); } catch (error) { return showToast(error.message); }
  showProgress(0, t("preparing"));
  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: state.jobId, mode: state.mode, file_ids: state.uploadedFiles.map((file) => file.id), options })
    });
    const queued = await response.json().catch(() => ({}));
    if (!response.ok || !queued.ok) throw new Error(queued.error || t("convertFailed"));
    const result = await waitForConversion(queued.status_url);
    setProgress(100, t("finalizing"));
    elements.progressModal.classList.add("hidden");
    elements.resultFile.textContent = `${result.filename} · ${formatBytes(result.size)}`;
    elements.downloadButton.href = result.download_url;
    elements.resultModal.classList.remove("hidden");
    $$(".step").forEach((step) => step.classList.add("active"));
  } catch (error) {
    elements.progressModal.classList.add("hidden");
    showToast(error.message || t("convertFailed"));
  }
}

async function waitForConversion(statusUrl) {
  while (true) {
    const response = await fetch(statusUrl, { cache: "no-store" });
    const status = await response.json().catch(() => ({}));
    if (!response.ok || !status.ok) throw new Error(status.error || t("convertFailed"));
    if (status.status === "failed") throw new Error(status.error || t("convertFailed"));
    if (status.status === "completed") return status;

    let label = t("preparing");
    if (status.status === "processing") {
      label = status.filename ? `${t("processingFile")}：${status.filename}` : t("processing");
    } else if (status.status === "finalizing") {
      label = t("finalizing");
    }
    setProgress(status.progress || 0, label);
    await new Promise((resolve) => window.setTimeout(resolve, 350));
  }
}

function setProgress(percent, statusText) {
  const value = Math.max(0, Math.min(100, Number(percent) || 0));
  elements.progressBar.style.width = `${value}%`;
  elements.progressPercent.textContent = `${Math.round(value)}%`;
  elements.progressStatus.textContent = statusText || t("preparing");
  elements.progressBar.parentElement.setAttribute("aria-valuenow", String(Math.round(value)));
}

function showProgress(percent = 0, statusText = t("preparing")) {
  setProgress(percent, statusText);
  elements.progressModal.classList.remove("hidden");
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

function startOver() {
  elements.resultModal.classList.add("hidden");
  revokePreviews();
  state.pendingFiles = [];
  state.uploadedFiles = [];
  state.jobId = null;
  elements.fileInput.value = "";
  setView("upload");
  renderPendingFiles();
}

function revokePreviews() {
  state.uploadedFiles.forEach((file) => { if (file.preview) URL.revokeObjectURL(file.preview); });
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value);
  return element.innerHTML;
}

elements.categoryNav.addEventListener("click", (event) => {
  const button = event.target.closest(".category-button");
  if (button) setCategory(button.dataset.category);
});
elements.dropzone.addEventListener("click", () => elements.fileInput.click());
elements.addMoreButton.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => { addFiles(elements.fileInput.files); elements.fileInput.value = ""; });
["dragenter", "dragover"].forEach((name) => elements.dropzone.addEventListener(name, (event) => { event.preventDefault(); elements.dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => elements.dropzone.addEventListener(name, (event) => { event.preventDefault(); elements.dropzone.classList.remove("dragging"); }));
elements.dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));
elements.nextButton.addEventListener("click", uploadFiles);
elements.convertButton.addEventListener("click", convertFiles);
elements.backButton.addEventListener("click", startOver);
elements.startOverButton.addEventListener("click", startOver);
elements.themeButton.addEventListener("click", () => setTheme(state.theme === "dark" ? "light" : "dark"));
elements.languageButton.addEventListener("click", () => {
  const opening = elements.languageMenu.classList.contains("hidden");
  elements.languageMenu.classList.toggle("hidden", !opening);
  elements.languageButton.setAttribute("aria-expanded", opening ? "true" : "false");
});
elements.languageMenu.addEventListener("click", (event) => {
  const button = event.target.closest("[data-locale]");
  if (!button) return;
  state.locale = button.dataset.locale;
  localStorage.setItem("file-converter-locale", state.locale);
  closeLanguageMenu();
  applyTranslations();
});
elements.mobileMenu.addEventListener("click", () => elements.sidebar.classList.toggle("open"));
document.addEventListener("click", (event) => {
  if (!event.target.closest(".file-card")) $$(".file-menu").forEach((menu) => menu.classList.add("hidden"));
  if (!event.target.closest(".language-picker")) closeLanguageMenu();
  if (window.innerWidth <= 700 && !event.target.closest(".sidebar") && !event.target.closest(".mobile-menu")) elements.sidebar.classList.remove("open");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.languageMenu.classList.contains("hidden")) {
    closeLanguageMenu();
    elements.languageButton.focus();
  }
});
window.addEventListener("beforeunload", revokePreviews);

resetModeSelection();
setTheme(state.theme);
applyTranslations();
renderPendingFiles();
