from .cli import BusyBee
import sys

if __name__ == "__main__":
    app = BusyBee()
    sys.exit(app.cmdloop())