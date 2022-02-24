import time
import socket
import yaml
from pathlib import Path
from typing import Dict

MOD_REGISTRY_URL = "http://folio-registry.aws.indexdata.com"
LOCAL_OKAPI_URL = "http://host.docker.internal:3000"
TENANT_ID = "diku"
tenant_name = 'Datalogisk Institut'
tenant_desc = 'Danish Library Technology Institute'
ADMIN_USER_ID = None
ADMIN_USER = {
    "username": "diku_admin",
    "password": "admin",
    "first_name": "",
    "last_name": "Superuser",
    "email": "admin@example.org",
    "perms_users_assign": "yes"
}
MINIMAL_MOD_NAMES = ['mod-data-import',
                     'mod-source-record-manager',
                     'mod-source-record-storage',
                     'mod-data-import-converter-storage']

MINIMAL_MOD_DATA = []

OKAPI_ENV = [
    {"name": "DB_HOST", "value": f"host.docker.internal"},
    {"name": "DB_PORT", "value": f"5432"},
    {"name": "DB_DATABASE", "value": f"okapi"},
    {"name": "DB_USERNAME", "value": f"folio_admin"},
    {"name": "DB_PASSWORD", "value": f"password"},
    {"name": "DB_MAXPOOLSIZE", "value": f"20"},
    {"name": "KAFKA_HOST", "value": f"host.docker.internal"},
    {"name": "KAFKA_PORT", "value": f"9092"},
    {"name": "ENV", "value": f"dev"},
    {"name": "ELASTICSEARCH_URL", "value": f"http://host.docker.internal:9200"},
    {"name": "OKAPI_URL", "value": LOCAL_OKAPI_URL},
    {"name": "JAVA_DEBUG", "value": f"true"}
]
CONFIG_YAML: dict = None


def main():
    my_env = {}
    my_env['DB_PASSWORD'] = 'password'
    my_env['DB_USERNAME'] = 'folio_admin'
    my_env['DB_DATABASE'] = 'okapi'
    my_env['DB_HOST'] = 'host.docker.internal'
    my_env['DB_PORT'] = '5432'
    my_env['OKAPI_URL'] = LOCAL_OKAPI_URL
    my_env['KAFKA_HOST'] = 'host.docker.internal'
    my_env['KAFKA_PORT'] = '9092'

    p = Path(__file__).with_name('.busybee.yml')
    with p.open("r") as f:
        CONFIG_YAML = yaml.safe_load(f)

    # start okapi
    import folio_mods
    import steps

    modules_config: dict = CONFIG_YAML.get('modules')
    modules: Dict[str, folio_mods.Module] = {}
    for module_name, module_config in modules_config.items():
        if module_name.casefold() == 'okapi'.casefold():
            modules[module_name] = folio_mods.Okapi(
                module_config.get('descriptor_location', None),
                module_config.get('jar_location'),
                module_config.get('port')).start(
                    my_env, module_config.get('show_output', False))
        else:
            modules[module_name] = folio_mods.Module(
                module_name,
                module_config.get('descriptor_location', None),
                module_config.get('jar_location'),
                module_config.get('port')).start(
                    my_env, module_config.get('show_output', False))

    try:
        time.sleep(10)
        # check that okapi or mock server is enabled
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        from urllib.parse import urlparse
        result = sock.connect_ex((urlparse(LOCAL_OKAPI_URL).hostname,
                                  urlparse(LOCAL_OKAPI_URL).port))
        if not result == 0:
            raise Exception(
                "Okapi url not valid. Check that okapi or mock server is running")

        # register modules
        for module in modules.values():
            steps.register_module(LOCAL_OKAPI_URL, module)

        # deploy modules to urls
        for module in modules.values():
            steps.deploy_module_to_http_loc(LOCAL_OKAPI_URL, module)

        # create tenant
        steps.create_tenant(
            LOCAL_OKAPI_URL, {'id': "diku", 'name': 'Datalogisk Institut', 'description': 'Danish Library Technology Institute'})

        # set env vars for modules
        steps.set_module_env_vars(LOCAL_OKAPI_URL, OKAPI_ENV)

        # enable modules for tenant
        steps.enable_modules_for_tenant(
            LOCAL_OKAPI_URL, TENANT_ID, modules.values())

        # wait for keyboard input
        while(True):
            user_input = input("Type exit to quit\n")
            if user_input.casefold() == 'exit'.casefold():
                break
    finally:
        for module in modules.values():
            module.terminate()

if __name__ == "__main__":
    main()
