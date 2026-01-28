import signal
import sys
import os

def signal_handler(sig, frame):
    print('\nBot stopped gracefully!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
print("Press Ctrl+C to stop the bot")
signal.pause()