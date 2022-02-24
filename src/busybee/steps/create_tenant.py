import requests

def create_tenant(okapi_url: str, tenant: dict):
    print('###############')
    print('CREATING TENANT')
    print('###############')

    tenant_id = tenant['id']
    tenant_name = tenant['name']
    tenant_desc = tenant['description']

    # check tenant
    resp = requests.get(f"{okapi_url}/_/proxy/tenants/{tenant_id}")
    if resp.status_code == 200:
        return

    # create tenant
    resp = requests.post(f"{okapi_url}/_/proxy/tenants",
                         json={"id": tenant_id,
                               "name": tenant_name,
                               "description": tenant_desc},
                         headers={"X-Okapi-Tenant": "supertenant"})
    if resp.status_code != 201:
        raise Exception(f"could not create tenant:{resp.text}")

    # enable okapi for tenant
    resp = requests.post(f"{okapi_url}/_/proxy/tenants/{tenant_id}/modules",
                         json={"id": "okapi"},
                         headers={"X-Okapi-Tenant": "supertenant"})
    if resp.status_code != 201:
        raise Exception(f"could not enable okapi for tenant:{resp.text}")