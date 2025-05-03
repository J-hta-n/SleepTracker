import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from http import HTTPStatus

import httpx
import pytz
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler
from telegram.ext._contexttypes import ContextTypes

TELEBOT_TOKEN = os.environ.get("TELEBOT_TOKEN")
TELEBOT_URL = os.environ.get("TELEBOT_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Reference: https://www.freecodecamp.org/news/how-to-build-and-deploy-python-telegram-bot-v20-webhooks/
telebot = Application.builder().token(TELEBOT_TOKEN).updater(None).build()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with telebot:
        await telebot.start()
        yield
        await telebot.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get_root():
    return {"TestKey": "Server is running!"}


@app.get("/setWebhook")
async def set_webhook():
    async with httpx.AsyncClient() as request:
        response = await request.post(
            TELEBOT_URL + "setWebhook?url=" + WEBHOOK_URL + "message"
        )
        data = response.json()
    return data


@app.post("/message")
async def process_update(request: Request):
    req = await request.json()
    update = Update.de_json(req, telebot.bot)
    print(json.dumps(update.to_dict(), indent=1))
    await telebot.process_update(update)
    return Response(status_code=HTTPStatus.OK)


async def record_sleep(update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("")


telebot.add_handler(CommandHandler("sleep", record_sleep))

# @app.post("/message")
# async def handle_message(request: Request):
#     req = await request.json()
#     date, text = parse_telebot_post_request(req)
#     async with httpx.AsyncClient() as request:
#         response = await request.post(
#             TELEBOT_URL +
#             "sendMessage?url="
#         )
#         data = response.json()
#     #

#     return {"received": req}

# async def parse_telebot_post_request(req):
#     date = datetime.fromtimestamp(req["message"]["date"], tz=pytz.timezone('Asia/Singapore'))
#     iso8601_date = date.isoformat()
#     text = req["message"]["text"]
#     print(json.dumps(req, indent=1))
#     return iso8601_date, text
