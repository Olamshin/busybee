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
    CMD_ENV_OPS = "Environment Operations"
    CMD_TENANT_OPS = "Tenant Operations"
    CMD_MODULE_OPS = "Module Operations"


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

    @cmd2.with_category(CMD_ENV_OPS)
    def do_start(self, arg):
        """Initializes the environment and creates a tenant with enabled modules"""
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
    @cmd2.with_category(CMD_MODULE_OPS)
    def do_deploy(self, args: Namespace):
        """Deploys a specified module. Usage: deploy -m MODULE_NAME"""
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
    @cmd2.with_category(CMD_MODULE_OPS)
    def do_undeploy(self: 'BusyBeeCli', args: Namespace):
        """Undeploys a specified module. Usage: undeploy -m MODULE_NAME"""
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
    @cmd2.with_category(CMD_ENV_OPS)
    def do_redirect(self: "BusyBeeCli", args: Namespace):
        """Manages HTTP redirects for a module. Usage: redirect -m MODULE_NAME [-l LOCATION | -rm]"""
        module_name = args.module
        http_location = args.location
        remove_redirect = args.remove

        if remove_redirect:
            return self.busybee.remove_redirect(module_name=module_name)

        if http_location is not None:
            self.busybee.remove_redirect(module_name=module_name)
            self.busybee.add_redirect(module_name=module_name, http_location=http_location)

    @cmd2.with_category(CMD_ENV_OPS)
    def do_reload(self: "BusyBeeCli", args: Namespace):
        """Reloads the config file and rebuilds the mod descriptors cache"""
        self.busybee.reload()

    create_tenant_argparser = cmd2.Cmd2ArgumentParser()
    create_tenant_argparser.add_argument(
        "-id",
        "--identifier",
        type=str,
        required=True,
        help="id of the tenant",
    )
    create_tenant_argparser.add_argument(
        "-n",
        "--name",
        type=str,
        required=False,
        help="name of the tenant",
    )
    create_tenant_argparser.add_argument(
        "-d",
        "--description",
        type=str,
        required=False,
        help="description of the tenant",
    )
    group = create_tenant_argparser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "-i",
        "--include-modules",
        type=str,
        required=False,
        help="comma separated list of modules to enable in the tenant",
    )
    group.add_argument(
        "-e",
        "--exclude-modules",
        type=str,
        required=False,
        help="comma separated list of modules to disable in the tenant",
    )
    @cmd2.with_argparser(create_tenant_argparser)  # type: ignore
    @cmd2.with_category(CMD_TENANT_OPS)
    def do_create_tenant(self: "BusyBeeCli", args: Namespace):
        """Create a new tenant with modules in BusyBee configuration file.
        Usage: create_tenant -id TENANT_ID [-n TENANT_NAME] [-d TENANT_DESCRIPTION] [-i INCLUDED_MODULES | -e EXCLUDED_MODULES]
        Example: create_tenant -id test1 -e mod-copycat,mod-login-saml"""
        self.busybee.create_tenant(args.identifier, args.name, args.description)
        self.busybee.enable_modules_for_tenant(
            args.identifier,
            [] if args.include_modules is None else str(args.include_modules).split(","),
            [] if args.exclude_modules is None else str(args.exclude_modules).split(","),
        )
        self.busybee.create_tenant_admin(args.identifier)

    delete_tenant_argparser = cmd2.Cmd2ArgumentParser()
    delete_tenant_argparser.add_argument(
        "-id",
        "--identifier",
        type=str,
        required=True,
        help="id of the tenant",
    )
    @cmd2.with_argparser(delete_tenant_argparser)
    @cmd2.with_category(CMD_TENANT_OPS)
    def do_delete_tenant(self: 'BusyBeeCli', args: Namespace):
        """Deletes a tenant. Usage: delete_tenant -id TENANT_ID"""
        self.busybee.delete_tenant(args.identifier)
