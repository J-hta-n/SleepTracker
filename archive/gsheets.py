import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# DEVELOPER DOCS:
# https://developers.google.com/identity/protocols/oauth2/service-account#python
# https://developers.google.com/sheets/api/guides/values
SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE")
SCOPES = os.environ.get("SCOPES").split(",")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
CREDENTIALS = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)


class Sheets:
    def __init__(self) -> None:
        self.sheets = (
            build("sheets", "v4", credentials=CREDENTIALS).spreadsheets().values()
        )
        self.sheet_name = "sleepdata"
        self.first_col = "A"
        self.last_col = "D"
        self.cur_row = self.initialise_cur_row()

    def initialise_cur_row(self):
        return int(
            self.sheets.get(
                spreadsheetId=SPREADSHEET_ID, range=f"{self.sheet_name}!A1:A1"
            )
            .execute()
            .get("values")[0][0]
        )

    def increment_cur_row(self):
        self.cur_row += 1
        body = {"values": [[self.cur_row]]}
        self.sheets.update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{self.sheet_name}!A1:A1",
            valueInputOption="RAW",
            body=body,
        ).execute()

    def get_cur_row_range(self):
        return f"{self.sheet_name}!{self.first_col}{self.cur_row}:{self.last_col}{self.cur_row}"

    def fetch_cur_row(self):
        range = self.get_cur_row_range()
        res = (
            self.sheets.get(spreadsheetId=SPREADSHEET_ID, range=range)
            .execute()
            .get("values", [])
        )
        return res[0] if len(res) > 0 else None

    def append_row(self, row):
        body = {"values": [row]}
        self.increment_cur_row()
        range = self.get_cur_row_range()
        res = (
            self.sheets.append(
                spreadsheetId=SPREADSHEET_ID,
                range=range,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
            .get("values", [])
        )
        # logger.info(f"Appended row succcessfully: {res.get('updatedCells')}")
        return res

    # def ad_row(self):
    # def fetch_rows(self):
    #     try:
    #         result = (
    #             self.sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE).execute()
    #         )
    #         return True
    #     except HttpError as err:
    #         return False


sheets = Sheets()
