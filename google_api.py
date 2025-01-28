import os.path
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
        self.video_response = None
        self.scopes = []
        self.flow = None
        self.credential = None
        self.config = None

    def setup(self):
        self.config = dotenv_values(".env")
        if not self.config:
            raise Exception("No configuration file found.")
        self.data_fields = self.config.get("DATA_FIELDS").split(",")
        self.api_key = self.config.get("GOOGLE_API_KEY", None)
        for scope in self.config.get("GOOGLE_SCOPES").split(","):
            self.scopes.append(f"https://www.googleapis.com/auth/{scope}")
        oauth2_credental = self.config.get("GOOGLE_CREDENTIAL_FILE")
        if not os.path.isfile(oauth2_credental):
            raise Exception("No credential file found.")
        try:
            self.flow = InstalledAppFlow.from_client_secrets_file(oauth2_credental, self.scopes)
            self.credential = self.flow.run_local_server(port=0)
            self.youtube_api = self.get_youtube_service()
            self.sheet_api = self.get_sheets_service()
            self.driver_api = self.get_google_driver_service()
        except Exception as e:
            raise Exception(f"Google API setup error: {str(e)}")

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

    def google_drive_folder_creation(self, folder_name: str) -> str:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        try:
            file = self.driver_api.files().create(body=file_metadata, fields="id").execute()
            print(f"Folder ID: {file.get('id')}")
            return file.get("id")
        except HttpError as e:
            raise Exception(f"Google drive folder creation error: {str(e)}")

    def google_sheet_creation(self, sheet_name: str) -> str:
        spreadsheet = {
            "properties": {
                "title": sheet_name
            }
        }
        try:
            spreadsheet = self.sheet_api.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
            return spreadsheet.get("spreadsheetId")
        except HttpError as e:
            raise Exception(f"Google spreadsheets file creation error: {str(e)}")

    def list_google_sheets(self) -> list:
        query = "mimeType = 'application/vnd.google-apps.spreadsheet'"
        try:
            response = self.driver_api.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
        except HttpError as e:
            raise Exception(f"Google drive list spreadsheet file error: {str(e)}")
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
            return file_items

    def youtube_channel_response_validation(self, channel_response) -> str:
        result_counts = jmespath.search("pageInfo.totalResults", channel_response)
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
                maxResults=100,
                pageToken=next_page_token
            )
            try:
                self.video_response = request.execute()
            except HttpError as e:
                raise Exception(f"Youtube video compose error: {str(e)}")
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

    def get_channel_id_by_username(self):
        """
        Fetch the YouTube channel ID using the username or custom URL.
        Args:
            username_or_custom_url (str): The username or custom URL of the YouTube channel.
        Returns:
            str: The channel ID if found, or None.
        """
        # Call the YouTube API to search for the channel
        username_or_custom_url = input("Enter the username or custom URL of the YouTube channel: ")
        request = self.youtube_api.search().list(
            part="snippet",
            q=username_or_custom_url,
            type="channel",
            maxResults=1  # Only fetch the first result
        )
        try:
            response = request.execute()
        except HttpError as err:
            print(f"Error: {err}")

        if response.get("items"):
            channel_id = response["items"][0]["id"]["channelId"]
            return channel_id
        else:
            print("Channel not found!")
            return None

    def get_channel_videos(self):
        request = self.youtube_api.channels().list(
            part="contentDetails",
            id=self.config.get("YOUTUBE_CHANNEL_ID") or self.get_channel_id_by_username()
        )
        try:
            response = request.execute()
        except HttpError as e:
            raise Exception(f"Youtube channel content get error: {str(e)}")
        if self.youtube_channel_response_validation(response) is False:
            return []
        playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return self.playlist_metadata_compose(playlist_id)

    def get_spreadsheet_id_by_name(self, spreadsheet_id, sheet_name):
        # Retrieve spreadsheet metadata
        try:
            response = self.sheet_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = response.get('sheets', [])
        except HttpError as e:
            raise Exception(f"Google get sheet id by name error: {str(e)}")
        # Iterate through the sheets to find the matching name
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        # Return None if no match is found
        print(f"Sheet with name '{sheet_name}' not found.")
        return None

    def update_row_height(self, spreadsheet_id, sheet_name, start_row=1, end_row=10, column=4, width=480, height=480):
        sheet_id = self.get_spreadsheet_id_by_name(spreadsheet_id, sheet_name)
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
        try:
            self.sheet_api.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
        except HttpError as e:
            raise Exception(f"Google spreadsheets row update error: {str(e)}")

    def spreadsheet_create(self, spreadsheet_name: str):
        spreadsheet_body = {"properties": {"title": spreadsheet_name}}
        try:
            response = self.sheet_api.spreadsheets().create(body=spreadsheet_body, fields="spreadsheetId").execute()
            print(f"Spreadsheet ID: {(response.get('spreadsheetId'))}")
            return response.get("spreadsheetId")
        except HttpError as e:
            raise Exception(f"Google spreadsheets create error: {str(e)}")

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
        except HttpError as e:
            raise Exception(f"Write Google Spreadsheets Error: {str(e)}")

    def video_history_creation(self):
        if video_list := self.get_channel_videos():
            video_length = len(video_list)
            spreadsheet_items = self.list_google_sheets()
            spreadsheet_file_name = input("Enter the name of the spreadsheet: ")
            if spreadsheet_file_name not in jmespath.search("[*].name", spreadsheet_items):
                spreadsheet_id = self.spreadsheet_create(spreadsheet_file_name)
            else:
                spreadsheet_id = jmespath.search(f"[?name=='{spreadsheet_file_name}'].id | [0]", spreadsheet_items)
            self.insert_data_into_sheet(spreadsheet_id, video_list)
            self.update_row_height(spreadsheet_id, self.config.get("GOOGLE_SHEET_TAB_NAME"), start_row=1, end_row=video_length)
        else:
            print("No videos found in channel id: {}".format(self.config.get("YOUTUBE_CHANNEL_ID")))
