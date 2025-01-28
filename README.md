# youtube_video_history
This is a simple Python app for fetch Youtube channel data and write back to Google spreadsheets

## dependencies
- python-dotenv
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib 

## Google API scopes
- youtube.readonly
- drive
- spreadsheets

## requirements
- A Google cloud account

## google cloud credential 申請
- 前往 Google Cloud Console (https://console.cloud.google.com/)
- 使用 Google 帳戶登入
- 建立新專案
    - 點擊左上角的下拉選單並選擇「新增專案」。
    - 輸入專案名稱（如 YouTube OAuth App），然後點擊 建立
選擇專案
    - 點擊右上角的下拉選單，選擇剛剛建立的專案。
- 啟用相關API
    - 點擊左側選單的 API 和服務 > 啟用 API 和服務
    - 搜索並啟用
        - YouTube Data API v3
        - Google Sheets API
        - Google Drive API
- 建立 OAuth 憑證
    - 進入憑證頁面 點擊左側選單的 API 和服務 > 憑證
    - 點擊 建立憑證 按鈕，選擇 OAuth 用戶端 ID
    - 設定同意畫面
        - 選擇 外部
        - 輸入應用名稱、支援電子郵件
        - 儲存並完成
    - 選擇應用類型
        - 桌面應用程式：適用於桌面應用
    - 下載憑證資訊
        - 建立完成後，會生成一組用戶端 ID 和用戶端密鑰
        - 點擊 下載 JSON，保存憑證檔案覆蓋 credentials.json

## Execution workflow
- Download google cloud credential and save as credentials.json
- Execute app.exe
- Enter the username or custom URL of the YouTube channel
- Enter the name of the spreadsheet
