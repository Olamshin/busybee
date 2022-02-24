def output_reader(proc_name, proc):
        for line in iter(proc.stdout.readline, b''):
            print(f"{proc_name}: {line.decode('utf-8')}")

from .module import Module
from .okapi import Okapi
