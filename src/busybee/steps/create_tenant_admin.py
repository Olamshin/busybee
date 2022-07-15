import requests
import uuid
import jmespath


def create_tenant_admin(okapi_url: str, tenant_id: str, admin_user: dict):
    print('############## #')
    print('CREATING TENANT ADMIN USER')
    print('###############')
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

    httpSession = requests.Session()
    retries = Retry(total=5, backoff_factor=2,
                    status_forcelist=[400, 500, 502, 503, 504],
                    method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"])
    httpSession.mount('http://', HTTPAdapter(max_retries=retries))

    def set_authtoken_status(is_enabled):
        resp = httpSession.get(
            f"{okapi_url}/_/proxy/tenants/{tenant_id}/interfaces/authtoken")
        if resp.status_code != 200:
            raise Exception(
                f"could not determine authtoken status: {resp.text}")

        authtoken_module_json = resp.json()
        authtoken_module_id = None
        if authtoken_module_json != [] and is_enabled is False:
            # authtoken is enabled, disable it
            authtoken_module_id = authtoken_module_json[0]['id']
            resp = httpSession.post(f"{okapi_url}/_/proxy/tenants/{tenant_id}/install",
                                    json=[{'id': authtoken_module_id, 'action': 'disable'}])
            if resp.status_code != 200:
                raise Exception(
                    f"could not disable authtoken module: {resp.text}")
        elif (authtoken_module_json == [] and is_enabled is True):
            # get authtoken module id
            resp = httpSession.get(
                f"{okapi_url}/_/proxy/modules?filter=mod-authtoken")
            resp_json = resp.json()
            if resp.status_code == 404 or (resp_json == [] and resp.status_code == 200):
                raise Exception(
                    f"authtoken module is not registered here:{resp.text}")
            elif len(resp_json) > 0 and resp.status_code == 200:
                authtoken_module_id = resp_json[0]["id"]
            # authtoken is disabled, enable it
            resp = httpSession.post(f"{okapi_url}/_/proxy/tenants/{tenant_id}/install",
                                    json=[{'id': authtoken_module_id, 'action': 'enable'}])
            if resp.status_code != 200:
                raise Exception(
                    f"could not disable authtoken module: {resp.text}")

    def create_user_record(user_dict):
        # check for user record
        resp = httpSession.get(f"{okapi_url}/users?query=username%3d%3d{user_dict['username']}",
                               headers={"X-Okapi-Tenant": tenant_id})
        if resp.status_code != 200:
            raise Exception(f"could not get user record: {resp.text}")
        user_json = resp.json()
        if user_json['totalRecords'] == 0:
            # create user record
            resp = httpSession.post(f"{okapi_url}/users",
                                    headers={"X-Okapi-Tenant": tenant_id},
                                    json={
                                        "id": str(uuid.uuid4()),
                                        "username": user_dict['username'],
                                        "active": 'true',
                                        "personal": {
                                            "lastName": user_dict['last_name'],
                                            "firstName": user_dict['first_name'],
                                            "email": user_dict['email']
                                        }
                                    })
            if resp.status_code != 201:
                raise Exception(f"could not create user record: {resp.text}")
            else:
                data = resp.json()
                return data['id']
        else:
            # set the current admin user id
            return user_json['users'][0]["id"]

    # if authtoken is enabled, disable it
    set_authtoken_status(False)

    # bootstrap admin user
    admin_user_id = create_user_record(admin_user)

    # check login record
    resp = httpSession.get(f"{okapi_url}/authn/credentials-existence?userId={admin_user_id}",
                           headers={"X-Okapi-Tenant": tenant_id})
    if resp.status_code != 200:
        raise Exception(f"could check credential existence: {resp.text}")
    cred_json = resp.json()
    if cred_json['credentialsExist'] == False:
        # create login record
        resp = httpSession.post(f"{okapi_url}/authn/credentials",
                             headers={"X-Okapi-Tenant": tenant_id},
                             json={
                                 "userId": admin_user_id,
                                 "password": admin_user['password']
                             })
        if resp.status_code != 201:
            raise Exception(f"could not create login record: {resp.text}")

    # check permission record
    resp = httpSession.get(f"{okapi_url}/perms/users?query=userId%3d%3d{admin_user_id}",
                           headers={"X-Okapi-Tenant": tenant_id})
    if resp.status_code != 200:
        raise Exception(f"could not get permission record: {resp.text}")
    perm_json = resp.json()
    top_level_perms = set_tenant_admin_permissions(okapi_url, tenant_id, admin_user_id)
    if perm_json['totalRecords'] == 0:
        # create permission record
        resp = httpSession.post(f"{okapi_url}/perms/users",
                             headers={"X-Okapi-Tenant": tenant_id},
                             json={
                                 "userId": admin_user_id,
                                 "permissions": top_level_perms
                             })
        if resp.status_code != 201:
            raise Exception(f"could not create permission record: {resp.text}")

    # check for service-points-users interface
    resp = httpSession.get(f"{okapi_url}/_/proxy/tenants/{tenant_id}/interfaces/service-points-users",
                           headers={"X-Okapi-Tenant": "supertenant"})
    if resp.status_code != 200:
        raise Exception(
            f"could determine if service-points-users is enabled: {resp.text}")

    serv_points_json = resp.json()
    if serv_points_json != []:
        # check for service-points-users record
        resp = httpSession.get(f"{okapi_url}/service-points-users?query=userId%3d%3d{admin_user_id}",
                               headers={"X-Okapi-Tenant": tenant_id})
        if resp.status_code != 200:
            raise Exception(
                f"could not get service-points-users record: {resp.text}")
        serv_points_rec_json = resp.json()
        if serv_points_rec_json != []:
            print('!!! create service-points-users for admin user !!!')

    # enable authtoken
    set_authtoken_status(True)

def set_tenant_admin_permissions(okapi_url: str, tenant_id, user_id):
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

    httpSession = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[400, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    httpSession.mount("http://", HTTPAdapter(max_retries=retries))

    resp = httpSession.get(
        f"{okapi_url}/perms/permissions",
        params={
            "query": "cql.allRecords=1 not permissionName==okapi.* not permissionName==perms.users.assign.okapi not permissionName==modperms.* not permissionName==SYS#*",
            "length": "5000",
        },
        headers={"X-Okapi-Tenant": tenant_id},
    )

    if resp.status_code != 200:
        raise Exception(f"something happened when getting all permissions: {resp.text}")

    expression = jmespath.compile("permissions[?length(childOf[?starts_with(@,'SYS#')]) == length(childOf)].permissionName")
    top_level_perms = expression.search(resp.json())
    return top_level_perms

# set_tenant_admin_permissions('http://localhost:9130', 'diku', )

    
