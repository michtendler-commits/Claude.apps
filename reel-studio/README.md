# Reel Studio

A personal text-to-video app on OpenAI's Sora 2 API. You need an OpenAI API key with billing set up.

## Run it on a Mac

1. Put `index.html` and `server.py` in the same folder (for example, Downloads).
2. Open **Terminal** (press Cmd+Space, type "Terminal", press Return).
3. Type `python3 ~/Downloads/server.py` and press Return.
   If macOS offers to install "command line developer tools", click **Install**, wait for it to finish, then run the command again.
4. Your browser opens at http://localhost:8787. Paste your OpenAI API key and start generating.

Keep the Terminal window open while you use the app. Press Ctrl+C in it to stop.

`server.py` passes the app's requests to OpenAI for it, because browsers often block pages opened
from a file (`file://...`) from calling OpenAI directly.
