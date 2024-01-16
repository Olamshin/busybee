from argparse import Namespace
from json import JSONDecodeError
import cmd2
import os
import sys
from blinker import signal
from .service import BusyBee
from .config import gen_config, MissingConfigurationException

class BusyBeeCli(cmd2.Cmd):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BusyBeeCli, cls).__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = ">>"

        self.term_messages = signal('output')
        self.error_msg = signal('errors')
        self.term_messages.connect(self.poutput)
        self.error_msg.connect(self.perror)

        try:
            self.busybee = BusyBee()
        except MissingConfigurationException as e:
            self.perror(f'Could not start BusyBee: {e}')
            config_path = os.path.normpath(os.path.abspath(gen_config()))
            self.poutput(f'Update configuration file generated at {config_path}')
            sys.exit()
        except JSONDecodeError as e:
            error_message = "A JSONDecodeError occurred: " + str(e)
            error_message += "\nThe problematic JSON string is:\n" + e.doc
            self.perror(error_message)
            sys.exit()
        except Exception as e:
            self.perror(f'Could not start BusyBee: {e}')
            sys.exit()
            

        self.poutput("Ready for your commands!")

    ########################
    ### Commandline methods
    ########################

    def module_name_choice_provider(self):
        return self.busybee._mod_descriptors.keys()

    def do_start(self, arg):
        self.busybee.set_module_env_vars()
        self.busybee.register_modules()
        self.busybee.create_tenant()
        self.busybee.enable_modules_for_tenant()
        self.busybee.create_tenant_admin()

    deploy_argparser = cmd2.Cmd2ArgumentParser()
    deploy_argparser.add_argument(
        "-m",
        "--module",
        type=str,
        required=True,
        help="name of the module",
        choices_provider=module_name_choice_provider,
    )

    @cmd2.with_argparser(deploy_argparser)  # type: ignore
    def do_deploy(self, args: Namespace):
        module_name = args.module
        return self.busybee.deploy_module(module_name=module_name)
        

    undeploy_argparser = cmd2.Cmd2ArgumentParser()
    undeploy_argparser.add_argument(
        "-m",
        "--module",
        type=str,
        required=True,
        help="name of the module",
        choices_provider=module_name_choice_provider,
    )

    @cmd2.with_argparser(undeploy_argparser)  # type: ignore
    def do_undeploy(self: 'BusyBeeCli', args: Namespace):
        module_name = args.module
        self.busybee.undeploy_module(module_name=module_name)

    redirect_argparser = cmd2.Cmd2ArgumentParser()
    redirect_argparser.add_argument(
        "-m",
        "--module",
        type=str,
        required=True,
        help="Name of the module",
        choices_provider=module_name_choice_provider,
    )
    group = redirect_argparser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--location", type=str, help="HTTP location for module")
    group.add_argument("-rm", "--remove", action="store_true", help="Remove redirect")

    @cmd2.with_argparser(redirect_argparser)  # type: ignore
    def do_redirect(self: "BusyBeeCli", args: Namespace):
        module_name = args.module
        http_location = args.location
        remove_redirect = args.remove

        if remove_redirect:
            return self.busybee.remove_redirect(module_name=module_name)
        
        if http_location is not None:
            self.busybee.remove_redirect(module_name=module_name)
            self.busybee.add_redirect(module_name=module_name, http_location=http_location)