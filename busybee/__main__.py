from .cli import BusyBeeCli
import sys

if __name__ == "__main__":
    app = BusyBeeCli()
    sys.exit(app.cmdloop())