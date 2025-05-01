# Python environment

- Switch to python 3.10.1, then create a virtual environment, activate it, then install depedencies

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

# Pre-commit hook

- If pre-commit is not yet installed run ` pre-commit install`
- Run `pre-commit run --all` before every commit

# Running SleepTracker

- To serve webhook locally, first obtain WEBHOOK_URL by running `ngrok http <PORT>` and copying the public domain given by ngrok to your local env file
- Then start the server with `python3 bot.py` on a separate terminal, which sets the webhook upon bot instantiation
