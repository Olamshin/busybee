import os
import requests
import json

from folio_mods.module import Module

def register_module(okapi_url, module: Module, check_deps=False) -> dict:
    module_descriptor: dict = None
    module_descriptor_location = module.descriptor_location

    if module_descriptor_location is None:
        return

    if os.path.exists(module_descriptor_location):
        with open(module_descriptor_location, "r") as f:
            module_descriptor = json.load(f)
    else:
        raise Exception("not a valid location for a module descriptor")
    
    print(f'registering module from location: {module_descriptor_location}')

    # check if module is already registered
    resp = requests.get(
        f"{okapi_url}/_/proxy/modules/{module_descriptor['id']}")

    # if module is not registered, register it
    if resp.status_code == 404:
        reg_resp = requests.post(
            f"{okapi_url}/_/proxy/modules",
            json=module_descriptor,
            params={'check': str(check_deps).lower()},
            headers={"X-Okapi-Tenant": "supertenant",
                        'Content-type': 'application/json', 'Accept': 'text/plain'})
        if (not reg_resp.status_code == 200) and (not reg_resp.status_code == 201):
            raise Exception(f'could not register module: {reg_resp.text}')

    print(f"module({module_descriptor['id']}) registered")

    # return module descriptor
    module.descriptor_json = module_descriptor
    return module_descriptor