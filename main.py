from google_api import Google

def main():
    google_service = Google()
    google_service.setup()
    google_service.video_history_creation()


if __name__ == '__main__':
    main()
