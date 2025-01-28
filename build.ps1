$APP_ENTRY_POINT = 'app.py'
$APP_NAME = 'youtube-history'
$APP_EXEC_NAME=$APP_ENTRY_POINT.Split('.')[0]
pyinstaller --onefile $APP_ENTRY_POINT && Copy-Item ".env" "dist" -Force
