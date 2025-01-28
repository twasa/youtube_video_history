from google_api import Google

def main():
    try:
        google_service = Google()
        google_service.setup()
        google_service.video_history_creation()
    except Exception as e:
        print(str(e))

if __name__ == '__main__':
    main()
