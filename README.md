# jcb_bot
Convert JCB currency through telegram bot

[Demo](https://t.me/jcb_convert_bot)

Setup dependency
----
```
pip -r requirements.txt
```

Usage
----
```
usage: jcb_bot [-h] [--port PORT] [--url URL] token

JCB currency telegram bot

positional arguments:
  token        telegram token

optional arguments:
  -h, --help   show this help message and exit
  --port PORT  bot server TCP port
  --url URL    specify telegram bot webhook url
```

* Remember to setup your webhook to telegram
```
curl https://api.telegram.org/bot<TOKEN>/setWebhook?url=<Webhook_URL>
```
