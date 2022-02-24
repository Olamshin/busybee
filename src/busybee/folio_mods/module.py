import subprocess
import threading
import os
import shutil
from . import output_reader


class Module():

    def __init__(self, name, descriptor_location, jar_location, http_port):
        self.name = name
        self.descriptor_location = descriptor_location
        self.descriptor_json = None
        self.jar_location = jar_location
        self.jar_file_name = os.path.basename(jar_location)
        self.http_port = http_port
        self.cmd = f'''java \
-Dhttp.port={self.http_port} \
-jar {self.jar_file_name}
'''
        self.proc: subprocess.Popen[bytes] = None

    def start(self, env, show_output=False):
        shutil.copyfile(self.jar_location, self.jar_file_name,
                        follow_symlinks=True)
        self.proc = subprocess.Popen(self.cmd,
                                     env=env,
                                     stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT if show_output else subprocess.DEVNULL,
                                     shell=True)
        if(show_output):
            t = threading.Thread(target=output_reader,
                                 args=(self.name, self.proc,))
            t.start()

        return self

    def terminate(self):
        self.proc.terminate()
