import requests


def set_module_env_vars(okapi_url: str, envs: list):
    print('###############')
    print('SETTING MODULE ENVIRONMENT VARIABLES')
    print('###############')
    # set okapi environment
    for item in envs:
        resp = requests.post(f"{okapi_url}/_/env",
                             json=item,
                             headers={"X-Okapi-Tenant": "supertenant"})
        if resp.status_code != 201:
            raise Exception(f"could not create env var: {resp.text}")
