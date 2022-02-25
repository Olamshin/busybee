import sys
from busybee import BusyBee

if __name__ == "__main__":
    app = BusyBee()
    sys.exit(app.cmdloop())