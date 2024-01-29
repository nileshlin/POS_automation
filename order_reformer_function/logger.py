import os

debug_level = os.getenv("DEBUG_LEVEL")
if debug_level is None:
    debug_level = "INFO"
print(f"LOG Level: {debug_level}")

class Logger:
    def __init__(self, class_name):
        self._class_name = class_name

    def _print_message(self, message: str, is_error=False):
        if is_error:
            print(f"ERROR - [{self._class_name[0:30]}]: {message}")
        else:
            print(f"{debug_level.upper()} - [{self._class_name[0:20]}]: {message}")

    def info(self, message: str):
        self._print_message(message, False)

    def debug(self, message: str):
        if debug_level.upper() == "DEBUG":
            self._print_message(message, False)

    def error(self, message: str):
        self._print_message(message, True)
