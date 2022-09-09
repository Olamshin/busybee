import logging
import subprocess
import threading
import os
import shutil
import logging
import shlex
from logging.handlers import RotatingFileHandler
from time import sleep

from busybee.global_vars import LOG_DIR, JAR_DIR, OTEL_TRACES_EXPORTER, OTEL_EXPORTER_JAEGER_ENDPOINT


class DebugInfo:
    def __init__(self, port, should_suspend):
        self.port = port
        self.suspend = should_suspend


def output_reader(logger, proc, exit_event):
        for line in iter(proc.stdout.readline, b''):
            if exit_event.is_set():
                break
            logger.info(line.decode('utf-8'))


os.makedirs(LOG_DIR, exist_ok=True)

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
        self.exit_event: threading.Event = threading.Event()

        self.last_env_vars = None
        self.last_show_output = None

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.log_handler = RotatingFileHandler(os.path.join(LOG_DIR, f'{name}.log'), maxBytes=1000000, backupCount=10)
        self.logger.addHandler(self.log_handler)

    def start(self, env, show_output=False):
        self.last_env_vars = env
        self.last_show_output = show_output
        # copy jars from various locations
        os.makedirs(JAR_DIR, exist_ok=True)
        shutil.copyfile(self.jar_location, os.path.join(JAR_DIR, self.jar_file_name),
                        follow_symlinks=True)

        cmd = self.build_cmd()
        print(cmd)
        args = shlex.split(cmd)
        self.proc = subprocess.Popen(args,
                                     env=env,
                                     stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT if show_output else subprocess.DEVNULL,
                                     shell=False)
        if show_output:
            self.exit_event = threading.Event()
            t = threading.Thread(target=output_reader,
                                 args=(self.logger, self.proc, self.exit_event))
            t.start()

        return self

    def with_debug_info(self, debug_info: DebugInfo):
        self.debug_info = debug_info
        self.terminate()
        self.start(self.last_env_vars, self.last_show_output)
        return self

    def down(self):
        self.terminate()
        self.proc = None

    def redeploy(self):
        self.terminate()
        self.start(self.last_env_vars, self.last_show_output)

    def build_cmd(self):
        result = 'java '
        result += f'-Dhttp.port={self.http_port} '
        result += f'-Dserver.port={self.http_port} '
        result += '-javaagent:/Users/okolawole/Downloads/jars/aws-opentelemetry-agent.jar '
        result += f'-Dotel.resource.attributes=service.name={self.name},service.namespace=olamide '
        result += f'-Dotel.exporter.jaeger.endpoint={OTEL_EXPORTER_JAEGER_ENDPOINT} '
        result += f'-Dotel.traces.exporter={OTEL_TRACES_EXPORTER} '
        result += '-Dotel.metrics.exporter=none '
        result += '-Dotel.traces.sampler=traceidratio '
        result += '-Dotel.traces.sampler.arg=1 '
        result += '-Dotel.instrumentation.common.default-enabled=false '
        result += '-Dotel.javaagent.extensions=/Users/okolawole/git/folio/opentelemetry-folio-instrumentation/opentelemetry-folio/javaagent/build/libs/folio-otel-javaagent-extensions-1.0-SNAPSHOT-all.jar '
        result += '-Dotel.instrumentation.folio.enabled=true '
        result += '-Dotel.instrumentation.netty.enabled=false '
        result += '-Dotel.instrumentation.opentelemetry-api.enabled=false '
        result += '-Dotel.instrumentation.kafka.enabled=false '
        result += '-Dotel.javaagent.debug=false '
        if self.debug_info is not None:
            result += f'-agentlib:jdwp=transport=dt_socket,server=y,' \
                      f'suspend={"y" if self.debug_info.suspend else "n"}' \
                      f',address=0.0.0.0:{self.debug_info.port} '
        result += f'-jar {os.path.join(JAR_DIR, self.jar_file_name)}'
        return result

    def terminate(self, shouldWait=True):
        self.exit_event.set()
        if self.proc:
            self.proc.terminate()
        if shouldWait:
            sleep(3)
        return self
