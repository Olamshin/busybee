import asyncio
import logging
import subprocess
import threading
import os
import shutil
import logging
import shlex
from logging.handlers import RotatingFileHandler
from time import sleep
from typing import Optional

from busybee.global_vars import GlobalVars
from busybee.modules import DebugInfo, ModuleInterface
from busybee import EVENT_LOOP

from blinker import signal

term_messages = signal('term_messages')


os.makedirs(GlobalVars.LOG_DIR, exist_ok=True)

CHUNK_SIZE = 1024  # 1KB

async def log_output(stream, log_func):
    while True:
        data = await stream.read(CHUNK_SIZE)
        if data:
            try:
                log_func(data.decode('utf-8', errors='replace'))
            except UnicodeDecodeError as e:
                print(f"Error at position {e.start}: {e.reason}")
        else:
            break

async def run_command(command, env_vars: dict, logger: logging.Logger, cancel_event=None):
    if env_vars is None:
        env_vars = {}

    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env_vars
    )
    
    if cancel_event:
        output_task = asyncio.create_task(log_output(proc.stdout, logger.info))
        while not cancel_event.is_set():
            await asyncio.sleep(1)
        if cancel_event.is_set():
            proc.terminate()
            output_task.cancel()
            try:
                await output_task
            except asyncio.exceptions.CancelledError:
                term_messages.send("logging tasks were cancelled")
    else:
        await log_output(proc.stdout, logger.info)

class Module(ModuleInterface):

    def __init__(self, name, descriptor_location, jar_location, http_port):
        self.name = name
        self.descriptor_location = descriptor_location
        self.descriptor_json = {}
        self.jar_location = jar_location
        self.jar_file_name = os.path.basename(jar_location)
        self.http_port: int = http_port
        self.debug_info: Optional[DebugInfo] = None
        self.proc: Optional[subprocess.Popen[bytes]] = None
        self.exit_event = asyncio.Event()
        self.last_env_vars = None
        self.last_show_output = None
        self.future = None
        self.last_env_vars = None

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.log_handler = RotatingFileHandler(os.path.join(GlobalVars.LOG_DIR, f'{name}.log'), maxBytes=1000000, backupCount=10)
        self.logger.addHandler(self.log_handler)

    def start(self, env: dict, show_output: Optional[bool]=False):
        if env is not None:
            self.last_env_vars = env
        self.last_show_output = show_output
        # copy jars from various locations
        os.makedirs(GlobalVars.JAR_DIR, exist_ok=True)
        shutil.copyfile(self.jar_location, os.path.join(GlobalVars.JAR_DIR, self.jar_file_name),
                        follow_symlinks=True)

        cmd = self.build_cmd()
        print(cmd)
        args = shlex.split(cmd)
        if self.name in GlobalVars.CONFIG_YAML['java17-modules']:
            env['JAVA_HOME'] = GlobalVars.CONFIG_YAML['java17-home']
        else:
            env['JAVA_HOME'] = GlobalVars.CONFIG_YAML['java11-home']

        self.exit_event = asyncio.Event()
        self.future = asyncio.run_coroutine_threadsafe(run_command(args, env, self.logger, self.exit_event), EVENT_LOOP)

        return self

    def with_debug_info(self, debug_info: DebugInfo):
        self.debug_info = debug_info
        return self

    def down(self):
        self.terminate()
        self.proc = None

    def redeploy(self):
        self.terminate()
        if((self.last_env_vars is not None)):
            self.start(self.last_env_vars, self.last_show_output)
        else: 
            raise Exception("module has not been started")

    def build_cmd(self):
        result = 'java '
        result += f'-Dhttp.port={self.http_port} '
        result += f'-Dserver.port={self.http_port} '
        # result += '-javaagent:/Users/okolawole/Downloads/jars/opentelemetry-javaagent.jar '
        # result += f'-Dotel.resource.attributes=service.name={self.name},service.namespace=olamide '
        # result += f'-Dotel.exporter.otlp.endpoint=http://olamimacmini:14317 '
        # result += f'-Dotel.exporter.otlp.headers="uptrace-dsn=http://project2_secret_token@localhost:14317/2" '
        # result += f'-Dotel.traces.exporter=otlp '
        # result += f'-Dotel.logs.exporter=otlp '
        # result += '-Dotel.metrics.exporter=none '
        # result += '-Dotel.traces.sampler=traceidratio '
        # result += '-Dotel.traces.sampler.arg=1 '
        # result += '-Dotel.instrumentation.common.default-enabled=false '
        # result += '-Dotel.javaagent.extensions=/Users/okolawole/git/folio/opentelemetry-folio-instrumentation/opentelemetry-folio/javaagent/build/libs/folio-otel-javaagent-extensions-1.0-SNAPSHOT-all.jar '
        # result += '-Dotel.instrumentation.folio.enabled=true '
        # result += '-Dotel.instrumentation.jdbc.enabled=true '
        # result += '-Dotel.instrumentation.log4j-appender.enabled=true '
        # result += '-Dotel.instrumentation.opentelemetry-api.enabled=true '
        # result += '-Dotel.javaagent.debug=false '
        # if self.name in GlobalVars.CONFIG_YAML['spring-modules']:
        #     result += '-Dotel.instrumentation.kafka.enabled=true '
        #     result += '-Dotel.instrumentation.hibernate.enabled=true '
        #     result += '-Dotel.instrumentation.spring-data.enabled=true '
        #     result += '-Dotel.instrumentation.spring-web.enabled=true '
        # if self.name == 'mod-search':
        #     result += '-Dotel.instrumentation.elasticsearch-rest.enabled=true '
        if self.debug_info is not None:
            result += f'-agentlib:jdwp=transport=dt_socket,server=y,' \
                      f'suspend={"y" if self.debug_info.suspend else "n"}' \
                      f',address=0.0.0.0:{self.debug_info.port} '
        result += f'-jar {os.path.join(GlobalVars.JAR_DIR, self.jar_file_name)}'
        return result

    def terminate(self, shouldWait=True):
        self.exit_event.set()
        if shouldWait and self.future is not None:
            while(not self.future.done()):
                sleep(0.1)
        return self
    
    async def terminate_async(self):
        self.exit_event.set()