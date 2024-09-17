# Overview

BusyBee is a command-line interface application designed to manage and deploy FOLIO modules in a dynamic and efficient manner. Built on Python and utilizing the cmd2 library, BusyBee offers a range of commands for deploying, undeploying, and managing redirects for different modules.

## Features

- Module Descriptors Caching: Caches module descriptors to improve performance and efficiency.
- Tenant and User Management: Supports creating tenants and tenant admin users, including setting permissions and environment variables.
- Module Deployment and Management: Facilitates deploying, undeploying, and managing modules, including HTTP redirection.
- Autocompletion of commands and module names on the CLI.

## Usage

```shell
pip install -r requirements.txt
python -m busybee
```

> Upgrade dependencies using `pip install -r requirements.txt -U`.

## Build Executable From Source

To build executable from source, clone the repository and install the required dependencies:

```shell
python build.py
```

Executable will be located in the `dist` folder.

## Configuration

Upon first run, if the configuration is missing, BusyBee CLI will generate a template configuration file at a specified path. Update this file with the necessary details before proceeding.

## Available Commands

- `start`: Initializes the environment and creates a tenant with enabled modules.
- `deploy`: Deploys a specified module. Usage:

```shell
deploy -m MODULE_NAME
```

- `undeploy`: Undeploys a specified module. Usage:

```shell
undeploy -m MODULE_NAME
```

- `redirect`: Manages HTTP redirects for a module. Usage:

> MODULE_NAME should be present in the BusyBee configuration file.

```shell
redirect -m MODULE_NAME [-l LOCATION | -rm]
```

- `reload`: Reloads the config file and rebuilds the mod descriptors cache. Usage:

```shell
reload
```

- `create_tenant`: Create a new tenant with modules in BusyBee configuration file. Usage:

```shell
create_tenant -id TENANT_ID [-n TENANT_NAME] [-d TENANT_DESCRIPTION] [-i INCLUDED_MODULES | -e EXCLUDED_MODULES]
```

> Example: `create_tenant -id test1 -e mod-copycat,mod-login-saml`

- `delete_tenant`: Deletes a tenant. Usage:

```shell
delete_tenant -id TENANT_ID
```

- `help`: Show available commands
- `quit`: Exit the application
