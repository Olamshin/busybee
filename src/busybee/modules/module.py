import logging
import subprocess
import threading
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler

class DebugInfo:
    def __init__(self, port, should_suspend):
        self.port = port
        self.suspend = should_suspend


def output_reader(proc_name, proc):
    log_dir = "logs"
    logger = logging.getLogger(proc_name)
    logger.setLevel(logging.INFO)
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(os.path.join(log_dir, f'{proc_name}.log'), maxBytes=1000000, backupCount=10)
    logger.addHandler(handler)
    for line in iter(proc.stdout.readline, b''):
        logger.info(line.decode('utf-8'))


class Module:

    def __init__(self, name, descriptor_location, jar_location, http_port):
        self.name = name
        self.descriptor_location = descriptor_location
        self.descriptor_json = None
        self.jar_location = jar_location
        self.jar_file_name = os.path.basename(jar_location)
        self.http_port: int = http_port
        self.debug_info: DebugInfo = None
        self.proc: subprocess.Popen[bytes] = None

        self.last_env_vars = None
        self.last_show_output = None

    def start(self, env, show_output=False):
        self.last_env_vars = env
        shutil.copyfile(self.jar_location, self.jar_file_name,
                        follow_symlinks=True)
        cmd = self.build_cmd()
        print(cmd)
        self.proc = subprocess.Popen(cmd,
                                     env=env,
                                     stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT if show_output else subprocess.DEVNULL,
                                     shell=True)
        if show_output:
            t = threading.Thread(target=output_reader,
                                 args=(self.name, self.proc,))
            t.start()

        return self

    def with_debug_info(self, debug_info: DebugInfo):
        self.debug_info = debug_info
        self.terminate()
        self.start(self.last_env_vars, self.last_show_output)
        return self

    def redeploy(self):
        self.terminate()
        self.start(self.last_env_vars, self.last_show_output)

    def build_cmd(self):
        result = 'java '
        result += f'-Dhttp.port={self.http_port} '
        if self.debug_info is not None:
            result += f'-agentlib:jdwp=transport=dt_socket,server=y,' \
                      f'suspend={"y" if self.debug_info.suspend else "n"}' \
                      f',address=0.0.0.0:{self.debug_info.port} '
        result += f'-jar {self.jar_file_name}'
        return result

    def terminate(self):
        self.proc.terminate()
        return self
