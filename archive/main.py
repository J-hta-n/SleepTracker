from datetime import datetime
import logging
import pytz
import os
import httpx
from fastapi import FastAPI, Request


TELEBOT_URL = os.environ.get("TELEBOT_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
async def get_root():
    return {"Root": "Server is running!"}


@app.get("/setWebhook")
async def set_webhook():
    async with httpx.AsyncClient() as request:
        response = await request.post(
            TELEBOT_URL + "/setWebhook?url=" + WEBHOOK_URL + "/message"
        )
        logger.info(TELEBOT_URL + "/setWebhook?url=" + WEBHOOK_URL + "/message")
        data = response.json()
    return data


@app.post("/message")
async def handle_message(request: Request):
    req = await request.json()
    command, context = parse_request(req)
    response = await execute_command(command, context)
    return response


class Commands:
    SLEEP = "sleep"
    WAKE_UP = "wakeup"
    choices = {SLEEP, WAKE_UP}


def parse_command(text: str):
    if not text or not text.startswith("/") or text[1:] not in Commands.choices:
        return None
    return text[1:]


def parse_request(req):
    text: str = req["message"]["text"]
    chat_id: int = req["message"]["chat"]["id"]
    date: datetime = datetime.fromtimestamp(
        req["message"]["date"], tz=pytz.timezone("Asia/Singapore")
    )
    command: str = parse_command(text)
    return (
        command,
        {
            "chat_id": chat_id,
            "date": date,
        },
    )


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as request:
        response = await request.post(
            f"{TELEBOT_URL}/sendMessage?chat_id={chat_id}&text={text}"
        )
        data = response.json()
    return data


async def execute_command(command: str, context):
    if not command:
        msg = "Invalid command; refer to help for more info"
        await send_message(context["chat_id"], msg)
        return {"error": msg}
    if command == Commands.SLEEP:
        await handle_record_sleep(context)
    return {"msg": "command executed successfully"}


async def handle_record_sleep(context):
    chat_id = context["chat_id"]
    await send_message(chat_id, msg)
