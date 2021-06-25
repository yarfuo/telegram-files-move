## Simple file telegram synchronization utility

This utility finds files which have not been changed for 15 minutes
and removes them and uploads to Telegram. Created for task when I need to upload big
access logs.

Created with MTProto API to bypass low file size limits.

### Installation
```bash
python3 -m venv --python=python3.7 venv
source ./venv/bin/activate
pip3 install -r requirements.txt
python3 main.py \
  --chat-id 674973662 \
  --bot-token '123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  --filename-regex '.*\.zip' \
  --path 'path' \
```

### Notes
- File uploads optimized by `cryptg` module.
- File telegram size limit is 2 GB for now.

### Thanks to
- https://github.com/pallets/click
- https://github.com/LonamiWebs/Telethon/ for the beautiful telegram library
- Thanks to others in `requirements.txt`
