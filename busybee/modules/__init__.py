from abc import abstractmethod
from typing import Optional

class DebugInfo:
    def __init__(self, port, should_suspend):
        self.port = port
        self.suspend = should_suspend

class ModuleInterface():

    descriptor_json: dict
    descriptor_location: str
    http_port: int
    
    @abstractmethod
    def start(self, env: Optional[dict], show_output: Optional[bool]=False):
        pass

    @abstractmethod
    def with_debug_info(self, debug_info: DebugInfo):
        pass

    @abstractmethod
    def redeploy(self):
        pass

    @abstractmethod
    def down(self):
        pass

    @abstractmethod
    def terminate(self, shouldWait=True):
        pass

    @abstractmethod
    async def terminate_async(self):
        pass

from .module import Module
from .okapi import Okapi
from .util import init_folio_modules, terminate_folio_modules, util_create_tenant
