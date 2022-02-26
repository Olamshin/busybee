import cmd2
import yaml
from pathlib import Path

from cmd2 import with_argparser
from busybee import global_vars, modules

Module = modules.Module
DebugInfo = modules.module.DebugInfo


class BusyBee(cmd2.Cmd):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = ">>"

        p = Path(__file__).with_name('.busybee.yml')
        with p.open("r") as f:
            config = yaml.safe_load(f)
        modules.init_folio_modules(config)
        global_vars.CONFIG_YAML = config

        self.poutput('Ready for your commands!')
        self.register_postloop_hook(modules.terminate_folio_modules)

    def module_name_choice_provider(self):
        return global_vars.MODULES.keys()

    debug_argparser = cmd2.Cmd2ArgumentParser()
    debug_argparser.add_argument('-m', '--module', type=str, required=True, help='name of the module',
                                 choices_provider=module_name_choice_provider)
    debug_argparser.add_argument('-p', '--port', type=int, required=True, help='port that will be used for debug')
    debug_argparser.add_argument('-s', '--suspend', action='store_true', help='wait for debugger to connect')

    @with_argparser(debug_argparser)
    def do_debug(self, args):
        """set a module to debug mode"""
        module_name = args.module
        debug_port = args.port
        suspend = args.suspend
        if module_name in global_vars.MODULES:
            self.poutput(f'redeploying module {module_name} with debug port {debug_port} and suspend is {suspend}')
            module: Module = global_vars.MODULES[module_name]
            module.with_debug_info(DebugInfo(port=debug_port, should_suspend=suspend))
            self.poutput('redeployment complete!')
        else:
            self.perror(f'module {module_name} is not available. check config and logs.')

    redeploy_argparser = cmd2.Cmd2ArgumentParser()
    redeploy_argparser.add_argument('-m', '--module', type=str, required=True, help='name of the module',
                                    choices_provider=module_name_choice_provider)

    @with_argparser(redeploy_argparser)
    def do_redeploy(self, args):
        module_name = args.module
        if module_name in global_vars.MODULES:
            self.poutput(f'redeploying module {module_name}')
            module: Module = global_vars.MODULES[module_name]
            module.redeploy()
            self.poutput('redeployment complete!')
        else:
            self.perror(f'module {module_name} is not available. check config and logs.')
