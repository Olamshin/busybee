from argparse import Namespace
import os
from time import sleep
from typing import Any
import cmd2
import yaml
from pathlib import Path

from cmd2 import with_argparser
from busybee import modules, EVENT_LOOP
from busybee.global_vars import GlobalVars
from blinker import signal


class BusyBee(cmd2.Cmd):

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BusyBee, cls).__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = ">>"

        # create internal directory if it does not exist
        os.makedirs(GlobalVars.BASE_DIR, exist_ok=True)

        p = Path(os.path.join(GlobalVars.BASE_DIR, ".busybee.yml"))
        if(not os.path.exists(p)):
            raise Exception(f"config file does exist at {p}")
        
        with p.open("r") as f:
            config: dict[str, Any] = yaml.safe_load(f)
        GlobalVars.CONFIG_YAML = config
        modules.init_folio_modules(config)

        self.poutput('Ready for your commands!')
        self.register_postloop_hook(modules.terminate_folio_modules)

        self.term_messages = signal('term_messages')
        self.term_messages.connect(self.poutput)

    def module_name_choice_provider(self):
        return GlobalVars.MODULES.keys()

    debug_argparser = cmd2.Cmd2ArgumentParser()
    debug_argparser.add_argument('-m', '--module', type=str, required=True, help='name of the module',
                                 choices_provider=module_name_choice_provider)
    debug_argparser.add_argument('-p', '--port', type=int, required=True, help='port that will be used for debug')
    debug_argparser.add_argument('-s', '--suspend', action='store_true', help='wait for debugger to connect')

    @with_argparser(debug_argparser)
    def do_debug(self: cmd2.Cmd, args: Namespace) -> None:
        """set a module to debug mode"""
        module_name = args.module
        debug_port = args.port
        suspend = args.suspend
        if module_name in GlobalVars.MODULES:
            self.poutput(f'redeploying module {module_name} with debug port {debug_port} and suspend is {suspend}')
            module: modules.ModuleInterface = GlobalVars.MODULES[module_name]
            module.with_debug_info(modules.DebugInfo(port=debug_port, should_suspend=suspend))
            module.terminate()
            module.start(None, True)
            
            self.poutput('redeployment complete!')
        else:
            self.perror(f'module {module_name} is not available. check config and logs.')

    redeploy_argparser = cmd2.Cmd2ArgumentParser()
    redeploy_argparser.add_argument('-m', '--module', type=str, required=True, help='name of the module',
                                    choices_provider=module_name_choice_provider)

    @with_argparser(redeploy_argparser)
    def do_redeploy(self: cmd2.Cmd, args: Namespace):
        module_name = args.module
        if module_name in GlobalVars.MODULES:
            self.poutput(f'redeploying module {module_name}')
            module: modules.ModuleInterface = GlobalVars.MODULES[module_name]
            module.redeploy()
            self.poutput('redeployment complete!')
        else:
            self.perror(f'module {module_name} is not available. check config and logs.')

    down_argparser = cmd2.Cmd2ArgumentParser()
    down_argparser.add_argument('-m', '--module', type=str, required=True, help='name of the module',
                                    choices_provider=module_name_choice_provider)

    @with_argparser(down_argparser)
    def do_down(self: cmd2.Cmd, args: Namespace):
        module_name = args.module
        if module_name in GlobalVars.MODULES:
            self.poutput(f'downing module {module_name}')
            module: modules.ModuleInterface = GlobalVars.MODULES[module_name]
            module.down()
            self.poutput('module is down!')
        else:
            self.perror(f'module {module_name} is not available. check config and logs.')

    create_tenant_argparser = cmd2.Cmd2ArgumentParser()
    create_tenant_argparser.add_argument('-n', '--name', type=str, required=True, help='name of the tenant')
    create_tenant_argparser.add_argument('-a', '--admin', type=str, required=False, help='name of the admin user')
    @with_argparser(create_tenant_argparser)
    def do_create_tenant(self: cmd2.Cmd, args: Namespace):
        tenant_name = args.name
        tenant_admin_name = args.admin or "diku_admin"
        modules.util_create_tenant(tenant_name, tenant_admin_name)


    def do_quit(self, arg):
        for (module_name, module) in GlobalVars.MODULES.items():
            self.poutput(f'stopping module... {module_name}')
            module.terminate(shouldWait=True)
        EVENT_LOOP.stop()
        while(EVENT_LOOP.is_running()):
            sleep(1)
        
        return True
        

