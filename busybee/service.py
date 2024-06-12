from typing import Any, List
from pathlib import Path
import yaml
import os
import requests
import re
import json
import jmespath
import uuid
from blinker import signal
from .config import MissingConfigurationException, find_config_file, USER_HOME_DIR, CONFIG_LOCATIONS


class BusyBee:
    _instance = None
    _config = {}
    _install_json = {}
    _mod_descriptors = {}
    tenant = {
        "id": "diku",
        "name": "Datalogisk Institut",
        "description": "Danish Library Technology Institute",
    }
    admin_user = {
        "username": "diku_admin",
        "password": "admin",
        "first_name": "",
        "last_name": "Superuser",
        "email": "admin@example.org",
        "perms_users_assign": "yes",
    }
    instIdTemplate = "busybee-redirect::{}"
    okapi_url = ""

    def __init__(self, *args, **kwargs):
        self.term_messages = signal("output")
        self.error_msg = signal("errors")

        self.__load_config()
        self.__load_mod_descriptors(False)
        self.okapi_url = self._config["okapi-url"]

    def __load_config(self):
        # Find the configuration file
        config_file_path = find_config_file(CONFIG_LOCATIONS)

        if config_file_path is None:
            pretty_list = "\n ".join(
                str(os.path.normpath(os.path.abspath(item))) for item in CONFIG_LOCATIONS)
            raise MissingConfigurationException(
                f"config file does not exist at any of these locations:\n {pretty_list}"
            )

        p = Path(config_file_path)

        with p.open("r") as f:
            config: dict[str, Any] = yaml.safe_load(f)
        self._config = config

    def __load_mod_descriptors(self, force):
        def fetch_content(path_or_url):
            # Check if the input is likely a URL
            if path_or_url.startswith(("http://", "https://")):
                self.term_messages.send(f'Getting install.json from {path_or_url}')
                try:
                    response = requests.get(path_or_url)
                    response.raise_for_status()
                    return response.text
                except requests.RequestException as e:
                    return f"Error fetching content from URL: {e}"

            # Otherwise, treat it as a file path
            try:
                with open(path_or_url, "r") as file:
                    return file.read()
            except IOError as e:
                return f"Error reading file: {e}"

        config = self._config
        if not "install-json-path" in config:
            raise Exception("install-json-path is not present")

        mod_desc_cache_path = os.path.join(USER_HOME_DIR, ".mod_descriptors.json")

        if os.path.exists(mod_desc_cache_path) and not force:
            # The file exists, so let's load its contents.
            with open(mod_desc_cache_path, "r") as json_file:
                self._mod_descriptors = json.load(json_file)
                be_modules = config["be-modules"]
                ui_modules = config["ui-modules"]
                if set(be_modules).issubset(set(self._mod_descriptors.keys())) and set(ui_modules).issubset(set(self._mod_descriptors.keys())):
                    self.term_messages.send(f'Using existing module descriptor cache at [{mod_desc_cache_path}]\nRun the "reload" command to recreate cache and reload config file')
                    return

        install_json_content = fetch_content(config["install-json-path"])
        self._install_json = json.loads(install_json_content)
        
        # Check for optional additional modules
        if "additional-json-path" in config: 
            additional_json_path = config["additional-json-path"]
            
            if os.path.exists(additional_json_path):
                print(f"Found additional modules from json path {additional_json_path}")
                additional_json_content = fetch_content(additional_json_path)
                additional_install_json = json.loads(additional_json_content)
                additional_install_json_len = len(additional_install_json)
                
                if additional_install_json_len > 0:
                    additional_json_dump = json.dumps(additional_install_json, indent=4)
                    print(f'Preparing to append additional modules: {additional_json_dump}')
                    self._install_json += additional_install_json
                    print(f"Appended {additional_install_json_len} additional modules to the list")
                else:
                    print(f"Failed to append additional modules, the list is empty")
        
        registry_url = config["registry-url"]
        for module in self._install_json:
            module_id = module["id"]
            module_name = ""
            match = re.search(r"^([\w-]*)\-\d+.\d+[.\d+]*.*", module_id)
            if match is not None:
                module_name = match.group(1)
            if (not module_name in self._config["be-modules"]) and (
                not module_name in self._config["ui-modules"]
            ):
                continue

            self.term_messages.send(f"getting module: {module_id} from FOLIO registry")
            module_desc_data = requests.get(
                f"{registry_url}/_/proxy/modules/{module_id}"
            )
            if module_desc_data.status_code != 200:
                print(f"could not load {module_id}")
                continue
            self._mod_descriptors[module_name] = {
                "id": module_id,
                "desc": module_desc_data.json(),
            }

        # cache the mod-descriptors
        with open(mod_desc_cache_path, "w") as json_file:
            json.dump(self._mod_descriptors, json_file)
        self.term_messages.send(f'Module descriptor cache created at {mod_desc_cache_path}')

    def reload(self):
        self.__load_config()
        self.__load_mod_descriptors(True)

    def set_module_env_vars(self):
        print("###############")
        print("SETTING ENVIRONMENT VARIABLES")
        print("###############")
        env_vars = self._config["env-vars"]
        envs = [{"name": name, "value": value} for name, value in env_vars.items()]
        # set okapi environment
        for item in envs:
            print(f'setting {item["name"]}')
            resp = requests.post(
                f"{self.okapi_url}/_/env",
                json=item,
                headers={"X-Okapi-Tenant": "supertenant"},
            )
            if resp.status_code != 201:
                raise Exception(f"could not create env var: {resp.text}")

    def register_modules(self):
        print("###############")
        print("REGISTERING MODULES")
        print("###############")
        modules = self._mod_descriptors

        for module in modules.values():
            module_id = module["id"]
            module_descriptor = module["desc"]
            if "mod-consortia" in modules and "mod-authtoken" in module_id:
                env_vars = module_descriptor["launchDescriptor"]["env"]
                for env_var in env_vars:
                    if env_var["name"] == "JAVA_OPTIONS":
                        env_var["value"] += " -Dallow.cross.tenant.requests=true"

            if "mod-consortia" in module_id:
                env_vars = module_descriptor["launchDescriptor"]["env"]
                system_user_password_env = {"name": "SYSTEM_USER_PASSWORD", "value": "consortia-system-user"}
                system_user_username_env = {"name": "SYSTEM_USER_NAME", "value": "consortia-system-user"}
                env_vars.append(system_user_password_env)
                env_vars.append(system_user_username_env)

            # check if module is already registered
            resp = requests.get(f"{self.okapi_url}/_/proxy/modules/{module_id}")
            # if module is not registered, register it
            if resp.status_code == 404:
                reg_resp = requests.post(
                    f"{self.okapi_url}/_/proxy/modules",
                    json=module_descriptor,
                    params={"check": "false"},
                    headers={
                        "X-Okapi-Tenant": "supertenant",
                        "Content-type": "application/json",
                        "Accept": "text/plain",
                    },
                )
                if (not reg_resp.status_code == 200) and (
                    not reg_resp.status_code == 201
                ):
                    raise Exception(f"could not register module: {reg_resp.text}")
            else:
                print(f"module {module_id} is already registered")

        pass

    def create_tenant(self, tenant_id="", tenant_name="", tenant_desc=""):
        print("###############")
        print("CREATING TENANT")
        print("###############")
        if not tenant_id:
            tenant_id = self.tenant["id"]
            tenant_name = self.tenant["name"]
            tenant_desc = self.tenant["description"]

        # check tenant
        resp = requests.get(f"{self.okapi_url}/_/proxy/tenants/{tenant_id}")
        if resp.status_code == 200:
            self.error_msg.send(f"tenant({tenant_id}) already exists")
            return

        # create tenant
        resp = requests.post(
            f"{self.okapi_url}/_/proxy/tenants",
            json={"id": tenant_id, "name": tenant_name, "description": tenant_desc},
            headers={"X-Okapi-Tenant": "supertenant"},
        )
        if resp.status_code != 201:
            self.error_msg.send(f"could not create tenant({resp.text})")
            return

        # enable okapi for tenant
        resp = requests.post(
            f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules",
            json={"id": "okapi"},
            headers={"X-Okapi-Tenant": "supertenant"},
        )
        if resp.status_code != 201:
            self.error_msg.send(f"could not enable okapi for tenant:{resp.text}")
            return

        self.term_messages.send(f"tenant({tenant_id}) has been created")

    def enable_modules_for_tenant(self, tenant_id: str = None, include_modules: List = [], exclude_modules: List = []):
        modules = self._mod_descriptors.values()
        if not tenant_id:
            tenant_id = self.tenant["id"]
        be_modules: List[str] = self._config["be-modules"]
        ui_modules: List[str] = self._config["ui-modules"]

        if exclude_modules:
            # remove excluded modules
            be_modules = [module for module in be_modules if module.strip() not in exclude_modules]
            ui_modules = [module for module in ui_modules if module.strip() not in exclude_modules]

        if include_modules:
            # include modules only
            be_modules = [module for module in be_modules if module.strip() in include_modules]
            ui_modules = [module for module in ui_modules if module.strip() in include_modules]

        def enable_be_module(module):
            module_id = module["id"]

            # check if module is already enabled
            response = requests.get(
                f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules"
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            if module_id in response.text:
                print(f"{module_id} is already enabled")
                return

            print(f"enabling module({module_id}) for tenant({tenant_id})")
            resp = requests.post(
                f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/install",
                json=[{"id": module_id, "action": "enable"}],
                params={
                    "tenantParameters": "loadReference=true,loadSample=true",
                    "deploy": "true",
                    "depCheck": "false",
                },
                headers={"X-Okapi-Tenant": "supertenant"},
            )
            if (
                resp.status_code != 201
                and resp.status_code != 200
                and "has no launchDescriptor" not in resp.text
            ):
                raise Exception(
                    f"could not create enable module({module_id}) for tenant({tenant_id}): {resp.text}"
                )
            print(f"enabled module({module_id}) for tenant({tenant_id})")

        def enable_ui_module(module):
            module_id = module["id"]
            module_descriptor = module["desc"]
            resp = requests.get(
                f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules/{module_id}"
            )

            # if module is not enabled, enable it
            if resp.status_code == 404:
                print(f"enabling ui module({module_id}) for tenant({tenant_id})")
                resp = requests.post(
                    f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules",
                    json={"id": module_id},
                    headers={"X-Okapi-Tenant": "supertenant"},
                    params={"depCheck": "false"},
                )
                if resp.status_code != 201 and resp.status_code != 200:
                    raise Exception(
                        f"could not create enable module({module_id}) for tenant({tenant_id}): {resp.text}"
                    )
            else:
                print(f"module({module_id}) is already enabled for tenant({tenant_id})")

        print("###############")
        print("ENABLING MODULES TO TENANT")
        print("###############")
        for item in be_modules:
            module = self._mod_descriptors[item]
            enable_be_module(module)

        for item in ui_modules:
            module = self._mod_descriptors[item]
            enable_ui_module(module)

    def delete_tenant(self, tenant_id: str):
        print("###############")
        print("DELETING TENANT")
        print("###############")

        # check tenant
        resp = requests.get(f"{self.okapi_url}/_/proxy/tenants/{tenant_id}")
        if resp.status_code != 200:
            self.error_msg.send(f"tenant({tenant_id}) does not exists")
            return

        # delete tenant
        resp = requests.delete(
            f"{self.okapi_url}/_/proxy/tenants/{tenant_id}",
            headers={"X-Okapi-Tenant": "supertenant"},
        )
        if resp.status_code != 204:
            self.error_msg.send(f"could not create tenant:{resp.text}")
            return

        self.term_messages.send(f"tenant({tenant_id}) has been deleted")

    def create_tenant_admin(self, tenant_id: str = None):
        admin_user = self.admin_user
        if tenant_id:
            admin_user['username'] = tenant_id + '_admin'
        else:
            tenant_id = self.tenant["id"]

        print("###############")
        print("CREATING TENANT ADMIN USER")
        print("###############")

        def set_authtoken_status(is_enabled):
            resp = requests.get(
                f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/interfaces/authtoken"
            )
            if resp.status_code != 200:
                raise Exception(f"could not determine authtoken status: {resp.text}")

            authtoken_module_json = resp.json()
            authtoken_module_id = None
            if authtoken_module_json != [] and is_enabled is False:
                # authtoken is enabled, disable it
                authtoken_module_id = authtoken_module_json[0]["id"]
                resp = requests.delete(
                    f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules/{authtoken_module_id}"
                )
                if resp.status_code != 204:
                    raise Exception(f"could not disable authtoken module: {resp.text}")
            elif authtoken_module_json == [] and is_enabled is True:
                # get authtoken module id
                resp = requests.get(
                    f"{self.okapi_url}/_/proxy/modules?filter=mod-authtoken"
                )
                resp_json = resp.json()
                if resp.status_code == 404 or (
                    resp_json == [] and resp.status_code == 200
                ):
                    raise Exception(
                        f"authtoken module is not registered here:{resp.text}"
                    )
                elif len(resp_json) > 0 and resp.status_code == 200:
                    authtoken_module_id = resp_json[0]["id"]
                # authtoken is disabled, enable it
                resp = requests.post(
                    f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/modules",
                    json={"id": authtoken_module_id},
                    params={"depCheck": "false"},
                )
                if resp.status_code != 201:
                    raise Exception(f"could not disable authtoken module: {resp.text}")

        def set_tenant_admin_permissions(okapi_url: str, tenant_id, user_id):
            resp = requests.get(
                f"{okapi_url}/perms/permissions",
                params={
                    "query": "cql.allRecords=1 not permissionName==perms.users.assign.okapi not permissionName==modperms.* not permissionName==SYS#*",
                    "length": "5000",
                },
                headers={"X-Okapi-Tenant": tenant_id},
            )

            if resp.status_code != 200:
                raise Exception(
                    f"something happened when getting all permissions: {resp.text}"
                )

            expression = jmespath.compile(
                "permissions[?length(childOf[?starts_with(@,'SYS#')]) == length(childOf)].permissionName"
            )
            top_level_perms = expression.search(resp.json())
            return top_level_perms

        def create_user_record(user_dict):
            # check for user record
            resp = requests.get(
                f"{self.okapi_url}/users?query=username%3d%3d{user_dict['username']}",
                headers={"X-Okapi-Tenant": tenant_id},
            )
            if resp.status_code != 200:
                raise Exception(f"could not get user record: {resp.text}")
            user_json = resp.json()
            if user_json["totalRecords"] == 0:
                # create user record
                resp = requests.post(
                    f"{self.okapi_url}/users",
                    headers={"X-Okapi-Tenant": tenant_id},
                    json={
                        "id": str(uuid.uuid4()),
                        "username": user_dict["username"],
                        "active": "true",
                        "personal": {
                            "lastName": user_dict["last_name"],
                            "firstName": user_dict["first_name"],
                            "email": user_dict["email"],
                        },
                    },
                )
                if resp.status_code != 201:
                    raise Exception(f"could not create user record: {resp.text}")
                else:
                    data = resp.json()
                    return data["id"]
            else:
                # set the current admin user id
                return user_json["users"][0]["id"]

        # if authtoken is enabled, disable it
        set_authtoken_status(False)

        # bootstrap admin user
        admin_user_id = create_user_record(admin_user)

        # check login record
        resp = requests.get(
            f"{self.okapi_url}/authn/credentials-existence?userId={admin_user_id}",
            headers={"X-Okapi-Tenant": tenant_id},
        )
        if resp.status_code != 200:
            raise Exception(f"could check credential existence: {resp.text}")
        cred_json = resp.json()
        if cred_json["credentialsExist"] == False:
            # create login record
            resp = requests.post(
                f"{self.okapi_url}/authn/credentials",
                headers={"X-Okapi-Tenant": tenant_id},
                json={"userId": admin_user_id, "password": admin_user["password"]},
            )
            if resp.status_code != 201:
                raise Exception(f"could not create login record: {resp.text}")

        # check permission record
        resp = requests.get(
            f"{self.okapi_url}/perms/users?query=userId%3d%3d{admin_user_id}",
            headers={"X-Okapi-Tenant": tenant_id},
        )
        if resp.status_code != 200:
            raise Exception(f"could not get permission record: {resp.text}")
        perm_json = resp.json()
        top_level_perms = set_tenant_admin_permissions(
            self.okapi_url, tenant_id, admin_user_id
        )
        if perm_json["totalRecords"] == 0:
            # create permission record
            resp = requests.post(
                f"{self.okapi_url}/perms/users",
                headers={"X-Okapi-Tenant": tenant_id},
                json={"userId": admin_user_id, "permissions": top_level_perms},
            )
            if resp.status_code != 201:
                raise Exception(f"could not create permission record: {resp.text}")

        # check for service-points-users interface
        resp = requests.get(
            f"{self.okapi_url}/_/proxy/tenants/{tenant_id}/interfaces/service-points-users",
            headers={"X-Okapi-Tenant": "supertenant"},
        )
        if resp.status_code != 200:
            raise Exception(
                f"could determine if service-points-users is enabled: {resp.text}"
            )

        serv_points_json = resp.json()
        if serv_points_json != []:
            # check for service-points-users record
            resp = requests.get(
                f"{self.okapi_url}/service-points-users?query=userId%3d%3d{admin_user_id}",
                headers={"X-Okapi-Tenant": tenant_id},
            )
            if resp.status_code != 200:
                raise Exception(
                    f"could not get service-points-users record: {resp.text}"
                )
            serv_points_rec_json = resp.json()
            if serv_points_rec_json != []:
                print("!!! create service-points-users for admin user !!!")

        # enable authtoken
        set_authtoken_status(True)

    def undeploy_module(self, module_name):
        if module_name in self._mod_descriptors.keys():
            module = self._mod_descriptors[module_name]
            self.term_messages.send(f"undeploying module {module_name}")
            del_resp = requests.delete(
                f"{self.okapi_url}/_/discovery/modules/{module['id']}",
                headers={
                    "X-Okapi-Tenant": "supertenant",
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                },
            )
            if del_resp.status_code != 204:
                self.error_msg.send(f"module could not be undeployed: {del_resp.text}")
                return
            self.term_messages.send(
                f"all module deployments & redirects of {module_name} was removed!"
            )
        else:
            self.error_msg.send(
                f"module {module_name} is not available. check config and logs."
            )

    def deploy_module(self, module_name):
        if module_name in self._mod_descriptors.keys():
            module = self._mod_descriptors[module_name]
            node_resp = requests.get(f"{self.okapi_url}/_/discovery/nodes")
            if node_resp.status_code != 200:
                self.error_msg.send(f"Could not deploy {module_name}: {node_resp.text}")
                return
            nodes = node_resp.json()
            if len(nodes) == 0:
                self.error_msg.send(f"there are no nodes available")
                return

            # TODO could have the user select which node to use
            node = nodes[0]

            self.term_messages.send(f"deploying module {module_name}")
            post_resp = requests.post(
                f"{self.okapi_url}/_/discovery/modules",
                headers={
                    "X-Okapi-Tenant": "supertenant",
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                },
                json={"srvcId": module["id"], "nodeId": node["nodeId"]},
            )
            if post_resp.status_code != 201:
                self.error_msg.send(f"module could not be deployed: {post_resp.text}")
                return
            self.term_messages.send("module is deployed!")
        else:
            self.error_msg.send(f"module {module_name} is not available.")

    def remove_redirect(self, module_name):
        if module_name in self._mod_descriptors.keys():
            module = self._mod_descriptors[module_name]
            del_resp = requests.delete(
                f"{self.okapi_url}/_/discovery/modules/{module['id']}/{self.instIdTemplate.format(module_name)}",
                headers={
                    "X-Okapi-Tenant": "supertenant",
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                },
            )
            if del_resp.status_code != 204:
                self.error_msg.send(
                    f"module redirect could not be removed: {del_resp.text}"
                )
                return
            self.term_messages.send("module redirect has removed!")
            return
        else:
            self.error_msg.send(f"module {module_name} is not available.")

    def add_redirect(self, module_name, http_location):
        if module_name in self._mod_descriptors.keys():
            module = self._mod_descriptors[module_name]
            self.term_messages.send(f"redirecting {module_name} to {http_location}")
            post_resp = requests.post(
                f"{self.okapi_url}/_/discovery/modules",
                headers={
                    "X-Okapi-Tenant": "supertenant",
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                },
                json={"srvcId": module["id"], "instId": self.instIdTemplate.format(module_name), "url": http_location},
            )
            if post_resp.status_code != 201:
                self.error_msg.send(f"module could not be redirected: {post_resp.text}")
                return
            self.term_messages.send("module has been redirected!")
        else:
            self.error_msg.send(f"module {module_name} is not available.")
