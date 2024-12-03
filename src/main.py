import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

from parsers import WorkUaParser, RobotaUaParser
from telegram_bot import TelegramResumeBot

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)

if __name__ == "__main__":
    work_ua_parser = WorkUaParser()
    robota_ua_parser = RobotaUaParser()

    bot = TelegramResumeBot(work_ua_parser, robota_ua_parser)
    bot.run()
