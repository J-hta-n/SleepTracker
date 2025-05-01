# Python environment

- Switch to python 3.10.1, then create a virtual environment, activate it, then install depedencies

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

# SleepTracker

- To serve webhook locally and interact with telegram API, first start server with `fastapi dev main.py` (ensure it runs on localhost port 8000),
  then run `ngrok http http://localhost:8000` and set WEBHOOK_URL to be the public domain given by ngrok
