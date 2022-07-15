import socket
import time
import busybee
from .module import Module
from .okapi import Okapi
from ..steps import (
    register_module,
    deploy_module_to_http_loc,
    create_tenant,
    set_module_env_vars,
    enable_modules_for_tenant,
    create_tenant_admin,
    register_ui_modules,
    enable_ui_modules_for_tenant
)


def init_folio_modules(config):
    # start okapi
    modules_config: dict = config.get("modules")
    for module_name, module_config in modules_config.items():
        env: dict = busybee.global_vars.ENV_VARS.copy()

        if module_name.casefold() == "okapi".casefold():
            busybee.global_vars.MODULES[module_name] = Okapi(
                module_config.get("descriptor_location", None),
                module_config.get("jar_location"),
                module_config.get("port"),
            ).start(env, module_config.get("show_output", False))
        else:
            busybee.global_vars.MODULES[module_name] = Module(
                module_name,
                module_config.get("descriptor_location", None),
                module_config.get("jar_location"),
                module_config.get("port"),
            ).start(env, module_config.get("show_output", False))
        time.sleep(1)
    try:
        print("waiting for modules to spin up")
        time.sleep(15)
        # check that okapi or mock server is enabled
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        from urllib.parse import urlparse

        result = sock.connect_ex(
            (
                urlparse(busybee.global_vars.LOCAL_OKAPI_URL).hostname,
                urlparse(busybee.global_vars.LOCAL_OKAPI_URL).port,
            )
        )
        if not result == 0:
            raise Exception(
                "Okapi url not valid. Check that okapi or mock server is running"
            )

        # register modules
        for module in busybee.global_vars.MODULES.values():
            register_module(busybee.global_vars.LOCAL_OKAPI_URL, module)

        # register ui modules
        ui_modules: list = config.get("ui-modules")
        register_ui_modules(busybee.global_vars.LOCAL_OKAPI_URL, ui_modules)

        # deploy modules to urls
        for module in busybee.global_vars.MODULES.values():
            deploy_module_to_http_loc(busybee.global_vars.LOCAL_OKAPI_URL, module)

        # create tenant
        create_tenant(
            busybee.global_vars.LOCAL_OKAPI_URL,
            {
                "id": "diku",
                "name": "Datalogisk Institut",
                "description": "Danish Library Technology Institute",
            },
        )

        # set env vars for modules
        set_module_env_vars(
            busybee.global_vars.LOCAL_OKAPI_URL, busybee.global_vars.OKAPI_ENV
        )

        # enable modules for tenant
        enable_modules_for_tenant(
            busybee.global_vars.LOCAL_OKAPI_URL,
            busybee.global_vars.TENANT_ID,
            busybee.global_vars.MODULES.values(),
        )

        enable_ui_modules_for_tenant(
            busybee.global_vars.LOCAL_OKAPI_URL,
            busybee.global_vars.TENANT_ID)

        # create admin user
        create_tenant_admin(
            busybee.global_vars.LOCAL_OKAPI_URL,
            busybee.global_vars.TENANT_ID,
            busybee.global_vars.ADMIN_USER,
        )

        # enable modules for tenant again, creating the admin user needed some modules disabled
        enable_modules_for_tenant(
            busybee.global_vars.LOCAL_OKAPI_URL,
            busybee.global_vars.TENANT_ID,
            busybee.global_vars.MODULES.values(),
        )
    except:
        terminate_folio_modules()
        raise


def terminate_folio_modules() -> None:
    for module in busybee.global_vars.MODULES.values():
        module.terminate(False)
