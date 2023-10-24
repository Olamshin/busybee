
import re
import os
import json
import requests
from busybee.global_vars import GlobalVars

MOD_REGISTRY_URL = "http://folio-registry.aws.indexdata.com"
UI_MODULE_DATA = {}

def get_module_descriptors(ui_modules: list):
    print('##########################')
    print('Getting Module Descriptors')
    print('##########################')
    cache_file = os.path.join(GlobalVars.BASE_DIR, '.mod_descriptors.json')
    module_descriptors = {}
    if(not os.path.exists(cache_file)):
        with open("/Users/okolawole/git/folio/platform-complete/install.json", "r") as f:
            data = json.load(f)
            for module in data:
                # derive module name
                module_id = ''
                module_name = ''
                match = re.search(r'^([\w-]*)\-\d+.\d+[.\d+]*.*', module['id'])
                if match is not None:
                    module_id = match.group(0)
                    module_name = match.group(1)

                if module_name in ui_modules:
                    print(f"FOUND UI MODULE: {module_name}")
                    module_desc_data = requests.get(
                        f"{MOD_REGISTRY_URL}/_/proxy/modules/{module_id}")
                    if module_desc_data.status_code != 200:
                        continue

                    json_data = json.loads(module_desc_data.text)
                    module_descriptors[module_name] = {
                        'id': module_id, 'desc': json_data}
        with open(cache_file, 'w') as f:
            f.write(json.dumps(module_descriptors))
    else:
        with open(cache_file, 'r') as f:
            module_descriptors = json.load(f)
                
    return module_descriptors


def register_ui_module(okapi_url: str, mod_descriptor):
        module_id = mod_descriptor['id']
        # check if module is already registered
        resp = requests.get(
            f"{okapi_url}/_/proxy/modules/{module_id}")

        # if module is not registered, register it
        if resp.status_code == 404:
            reg_resp = requests.post(
                f"{okapi_url}/_/proxy/modules",
                json=mod_descriptor['desc'],
                params={'check': 'false'},
                headers={"X-Okapi-Tenant": "supertenant",
                         'Content-type': 'application/json', 'Accept': 'text/plain'})
            if reg_resp.status_code == 201:
                print(f'#### {mod_descriptor["id"]} registered')
            else:
                raise Exception(f'could not register ui module: {reg_resp.text}')

        return resp.status_code


def register_ui_modules(okapi_url: str, ui_modules: list):
    global UI_MODULE_DATA
    UI_MODULE_DATA = get_module_descriptors(ui_modules)
    for mod_descr in UI_MODULE_DATA.values():
        register_ui_module(okapi_url, mod_descr)

def enable_ui_modules_for_tenant(okapi_url, tenant_id):
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    httpSession = requests.Session()
    retries = Retry(total=5, backoff_factor=2,
                    status_forcelist=[400, 500, 502, 503, 504],
                    method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"])
    httpSession.mount('http://', HTTPAdapter(max_retries=retries))
    print('###############')
    print('ENABLING UI MODULES FOR TENANT')
    print('###############')
    # deploy minimal modules to the tenant
    for module in UI_MODULE_DATA.values():
        resp = requests.get(
        f"{okapi_url}/_/proxy/tenants/{tenant_id}/modules/{module['id']}")

        # if module is not enabled, enable it
        if resp.status_code == 404:
            print(f"enabling ui module({module['id']}) for tenant({tenant_id})")
            resp = httpSession.post(f"{okapi_url}/_/proxy/tenants/{tenant_id}/modules",
                                json={"id": module['id']},
                                headers={"X-Okapi-Tenant": "supertenant"})
            if resp.status_code != 201 and resp.status_code != 200:
                raise Exception(
                    f"could not create enable module({module['id']}) for tenant({tenant_id}): {resp.text}")
        else:
            print(f"module({module['id']}) is already enabled for tenant({tenant_id})")