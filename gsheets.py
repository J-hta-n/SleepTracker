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
RANGE = os.environ.get("RANGE")

credientials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gsheets = build("sheets", "v4", credentials=credientials).spreadsheets()

def fetch_rows():
  try:
    result = (
        gsheets.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=RANGE)
        .execute()
    )
    return True
  except HttpError as err:
    return False