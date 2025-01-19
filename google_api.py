import jmespath
from datetime import datetime
from typing import Optional
from dotenv import dotenv_values

from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow


class Google(object):
    def __new__(cls):
        cls._instance = None
        if cls._instance is None:
            cls._instance = super(Google, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.youtube_api = None
        self.sheet_api = None
        self.driver_api = None
        self.api_key = None
        self.channel_response = None
        self.video_response = None
        self.scopes = []
        self.flow = None
        self.credential = None


    def setup(self):
        self.config = dotenv_values('.env')
        self.data_fields = self.config.get("DATA_FIELDS").split(",")
        self.api_key = self.config.get("GOOGLE_API_KEY", None)
        for scope in self.config.get("GOOGLE_SCOPES").split(","):
            self.scopes.append(f"https://www.googleapis.com/auth/{scope}")
        self.flow = InstalledAppFlow.from_client_secrets_file(self.config.get("GOOGLE_CREDENTIAL_FILE"), self.scopes)
        self.credential = self.flow.run_local_server(port=0)
        self.youtube_api = self.get_youtube_service()
        self.sheet_api = self.get_sheets_service()
        self.driver_api = self.get_google_driver_service()

    def config_reload(self):
        self.config = dotenv_values('.env')

    def get_youtube_service(self) -> Resource:
        return build(
            serviceName="youtube",
            version=self.config.get("YOUTUBE_API_VERSION"),
            credentials=self.credential
        )

    def get_sheets_service(self) -> Resource:
        return build(
            serviceName="sheets",
            version=self.config.get("GOOGLE_SHEET_API_VERSION"),
            credentials=self.credential
        )
    
    def get_google_driver_service(self) -> Resource:
        return build(
            serviceName="drive",
            version=self.config.get("DRIVE_API_VERSION"),
            credentials=self.credential
        )

    def list_google_sheets(self) -> list:
        query = "mimeType = 'application/vnd.google-apps.spreadsheet'"
        response = self.driver_api.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
        file_data = response.get('files', [])
        file_items = []
        if not file_data:
            return []
        else:
            for item in file_data:
                file_items.append(
                    {
                        "name": item["name"],
                        "id": item["id"]
                    }
                )
            file_names = jmespath.search('[].name', file_items)
            for file_name in file_names:
                print(file_name)
            file_name = input("file name: ")
            data = {"file_items": file_items}
            return jmespath.search(f"file_items[?name == '{file_name}'].id", data)

    def youtube_channel_response_validation(self) -> str:
        result_counts = jmespath.search("pageInfo.totalResults", self.channel_response)
        return result_counts > 0

    def datetime_string_to_iso_format(self, datetime_string: str) -> Optional[str]:
        try:
            return datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M:%SZ").isoformat()
        except ValueError:
            return None


    def playlist_metadata_compose(self, playlist_id) -> list:
        video_list = []
        next_page_token = None
        video_list.append(self.data_fields)
        while True:
            request = self.youtube_api.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            self.video_response = request.execute()
            # https://developers.google.com/youtube/v3/docs/videos?#resource
            for item in self.video_response["items"]:
                channel_title = item["snippet"]["channelTitle"]  # Video view count
                video_title = item["snippet"]["title"]  # Video title
                video_url = f"https://www.youtube.com/watch?v={item["snippet"]["resourceId"]["videoId"]}"  # Video URL
                video_image_url = '=IMAGE("{}", 3)'.format(item["snippet"]["thumbnails"]["high"]["url"])
                video_published_at = self.datetime_string_to_iso_format(item["snippet"]["publishedAt"])  # Video published date
                video_list.append(
                    [
                        channel_title,
                        video_title,
                        video_url,
                        video_image_url,
                        video_published_at
                    ]
                )

            # Check if there"s another page of results
            next_page_token = self.video_response.get("nextPageToken")
            if not next_page_token:
                break
        return video_list


    def get_channel_videos(self):
        request = self.youtube_api.channels().list(
            part="contentDetails",
            id=self.config.get("YOUTUBE_CHANNEL_ID")
        )
        self.channel_response = request.execute()
        if self.youtube_channel_response_validation() is False:
            return []
        playlist_id = self.channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return self.playlist_metadata_compose(playlist_id)

    def get_sheet_id_by_name(self, spreadsheet_id, sheet_name):
        # Retrieve spreadsheet metadata
        response = self.sheet_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = response.get('sheets', [])
        
        # Iterate through the sheets to find the matching name
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        # Return None if no match is found
        print(f"Sheet with name '{sheet_name}' not found.")
        return None

    def update_row_height(self, spreadsheet_id, sheet_name, start_row=1, end_row=10, column=4, width=480, height=480):
        sheet_id = self.get_sheet_id_by_name(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return
        requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_row,
                        "endIndex": end_row,
                    },
                    "properties": {
                        "pixelSize": height
                    },
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column,
                        "endIndex": column,
                    },
                    "properties": {
                        "pixelSize": width
                    },
                    "fields": "pixelSize"
                }
            }
        ]
        body = {"requests": requests}
        self.sheet_api.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()

    def insert_data_into_sheet(self, spreadsheet_id, video_list):
        range_name = "{}!{}".format(
            self.config.get("GOOGLE_SHEET_TAB_NAME"),
            self.config.get("GOOGLE_SHEET_START_POSITION")
        )
        value_input_option = "USER_ENTERED"
        request_body = {"values": video_list}
        # Call the Sheets API to insert video_list
        try:
            self.sheet_api.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=request_body
            ).execute()
        except HttpError as err:
            print(f"Error: {err}")

    def video_history_creation(self):
        if video_list := self.get_channel_videos():
            video_length = len(video_list)
            spreadsheet_ids = self.list_google_sheets()
            self.insert_data_into_sheet(spreadsheet_ids[0], video_list)
            self.update_row_height(spreadsheet_ids[0], self.config.get("GOOGLE_SHEET_TAB_NAME"), start_row=1, end_row=video_length)
        else:
            print("No videos found in channel id: {}".format(self.config.get("YOUTUBE_CHANNEL_ID")))
