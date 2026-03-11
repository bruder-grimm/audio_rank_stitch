
""" A class that simply logs to the terminal, with a timestamp and a log level. """
import datetime
from enum import Enum
import inspect

class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

class Logger():
    def __init__(self, level: LogLevel = LogLevel.INFO):
        self.level = level

    def debug(self, message: str):
        self.log(LogLevel.DEBUG, message)

    def info(self, message: str):
        self.log(LogLevel.INFO, message)

    def warn(self, message: str):
        self.log(LogLevel.WARNING, message)

    def error(self, message: str):
        file = inspect.stack()[1].filename
        caller = inspect.stack()[1].function
        line_no = inspect.stack()[1].lineno
        self.log(LogLevel.ERROR, f"[{file}.{caller}:{line_no}] {message}")

    def log(self, level: LogLevel, message: str):
        if self.level.value <= level.value:
            timestamp = datetime.datetime.now().isoformat()
            print(f"[{timestamp}] [{level.name}] {message}")