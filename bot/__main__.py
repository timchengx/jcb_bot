import argparse
import csv
import requests
import logging
import io
import threading

from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler, MessageHandler, RegexHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class argconfig():
    _instance = None

    @staticmethod
    def check_port(port):
        try:
            number = int(port)
            if number < 0 or number > 65535:
                raise Exception
        except:
            raise argparse.ArgumentTypeError('Port should be in 0~65535')

    def __new__(cls):
        if not cls._instance:
            _instance = argparse.ArgumentParser(prog='jcb_bot'
                                                ,description='JCB currency telegram bot')
            #remember to change back to required
            _instance.add_argument('token', help='telegram token')
            _instance.add_argument('--port', help='bot server TCP port', default=8447, type=argconfig.check_port)
            _instance.add_argument('--url', help='specify telegram bot webhook url')
        return _instance


class JCB:
    rate_url = 'https://www.jcb.jp/uploads/{0}.csv'

    def __init__(self):
        self.data = dict()
        self.last_attempt_time = int(0)

        day = datetime.now()
        day_str = day.strftime('%Y%m%d')
        while not self.getTable(day_str):
            day -= timedelta(days=1)
            day_str = day.strftime('%Y%m%d')

    def convert_latest(self, origin, to, value):
        date = self.get_latest_date()
        return self.convert(date, origin, to, value)

    def convert(self, date, origin, to ,value):
        if not origin in self.data[date]:
            raise KeyError(origin)
        if not to in self.data[date]:
            raise KeyError(to)
        usd_rate = self.data[date][origin][0]
        target_rate = self.data[date][to][1]

        return (value / usd_rate) * target_rate

    def get_latest_date(self):
        day = datetime.now()
        day_str = day.strftime('%Y%m%d')

        if day_str in self.data:
            return day_str

        delta = day.timestamp() - self.last_attempt_time
        if delta > 3600:  # 1 hour
            self.last_attempt_time = day.timestamp()
            if self.getTable(day_str):
                return day_str

        day -= timedelta(days=1)
        day_str = day.strftime('%Y%m%d')
        while not day_str in self.data:
            if self.getTable(day_str):
                return day_str
            day -= timedelta(days=1)
            day_str = day.strftime('%Y%m%d')
        
        return day_str

    def getTable(self, date):
        conn = requests.get(JCB.rate_url.format(date), allow_redirects=False)
        if conn.status_code is not requests.codes.ok:
            return False
        if 'Content-Type' not in conn.headers:
            return False
        if conn.headers['Content-Type'] != 'text/plain':
            return False

        raw_data = csv.reader(io.StringIO(conn.text))
        table = dict()
        for pair in raw_data:
            entry = [float(pair[2]), float(pair[4])]
            table[pair[5]] = entry
        self.data[date] = table

        return True


class BotCommand:

    def __init__(self):
        self.data_module = JCB()

    def convert_currency(self, bot, update):
        text = update.message.text.split()
        date = self.data_module.get_latest_date()
        result = ' '
        try:
            value = self.data_module.convert(date, text[0].upper(),
                                            text[1].upper(), float(text[2]))
            value = round(value, 7)
            result = str(value) + ' (' + date + ')'
        except KeyError as k:
            result = 'Unknown currency ' + str(k)
        finally:
            bot.send_message(update.message.chat.id, result,
                            reply_to_message_id=update.message.message_id)

    def convert_jpy_twd(self, bot, update):
        text = float(update.message.text)
        date = self.data_module.get_latest_date()
        value = self.data_module.convert(date, 'JPY', 'TWD', text)
        value = round(value, 7)
        bot.send_message(update.message.chat.id, str(value) + ' (' + date + ')',
                        reply_to_message_id=update.message.message_id)

    def convert_currency_with_rate(self, bot, update):
        text = update.message.text.split()
        date = self.data_module.get_latest_date()
        result = ' '
        try:
            value = self.data_module.convert(date, text[0].upper(),
                                            text[1].upper(), float(text[2]))
            value = value * ((100 + float(text[3])) / 100)
            value = round(value, 7)
            result = str(value) + ' (' + date + ')'
        except KeyError as k:
            result = 'Unknown currency ' + str(k)
        finally:
            bot.send_message(update.message.chat.id, result,
                            reply_to_message_id=update.message.message_id)
        

    def convert_jpy_twd_with_rate(self, bot, update):
        text = update.message.text.split()
        date = self.data_module.get_latest_date()
        value = self.data_module.convert(date, 'JPY', 'TWD', float(text[0]))
        value = value * ((100 + float(text[1])) / 100)
        value = round(value, 7)
        bot.send_message(update.message.chat.id, str(value) + ' (' + date + ')',
                        reply_to_message_id=update.message.message_id)


    def help(self, bot, update):
        update.message.reply_text('<from> <to> <value>\n' +
                                  '<value> (JPY to TWD)\n' +
                                  '<from> <to> <value> <rate> (apply convert rate)\n' +
                                  '<value> <rate> (JPY to TWD with convert rate)\n' +
                                  '--------\n' +
                                  'JPY USD 100\n' +
                                  '100\n' +
                                  'JPY USD 100 1.5\n' +
                                  '100 1.5')                                                                                                                 
                                      

    def error(self, bot, update):
        update.message.reply_text('???')


def main():
    parser = argconfig()
    args = parser.parse_args()

    command = BotCommand()

    update = Updater(args.token)
    update.dispatcher.add_handler(RegexHandler(r'[a-zA-Z]{3} [a-zA-Z]{3} [0-9]+\.*[0-9]*$',
                                                command.convert_currency))
    update.dispatcher.add_handler(RegexHandler(r'[a-zA-Z]{3} [a-zA-Z]{3} [0-9]+\.*[0-9]* -+[0-9]+\.*[0-9]*$',
                                                command.convert_currency_with_rate))
    update.dispatcher.add_handler(RegexHandler(r'[0-9]+\.*[0-9]*$',
                                                command.convert_jpy_twd))
    update.dispatcher.add_handler(RegexHandler(r'[0-9]+\.*[0-9]* -+[0-9]+\.*[0-9]*$',
                                                command.convert_jpy_twd_with_rate))
    update.dispatcher.add_handler(CommandHandler('help', command.help))
    update.dispatcher.add_handler(MessageHandler(Filters.all, command.error))
    update.dispatcher.add_error_handler(command.error)

    update.start_webhook(listen='0.0.0.0', port=args.port, webhook_url=args.url)


if __name__ == '__main__':
    main()
