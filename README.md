# BusyBee

CLI tool for managing and deploying FOLIO modules to Okapi.

## Quick Start
```bash
pip install -r requirements.txt
python -m busybee
```

## Build Executable
```bash
python build.py  # Output in dist/
```

## Configuration

Config file location: `~/.busybee/config.yml`

### Module Descriptor Transformations

Transform module descriptors before posting to Okapi:

```yaml
module-transformations:
  defaults:
    docker-args:
      HostConfig:
        Memory: 1073741824  # 1 GB default

  modules:
    mod-source-record-manager:
      docker-args:
        HostConfig:
          Memory: 2147483648  # 2 GB
          Binds:
            action: append
            values:
              - "/host/path:/container/path:rw"
      env:
        - name: MY_VAR
          value: my_value
          action: set  # set (default), add, or append
      when:
        modules-present: [mod-pubsub]  # conditional
```

## Commands

| Command | Description |
|---------|-------------|
| `start` | Initialize environment and create tenant with modules |
| `deploy -m MODULE` | Deploy a module |
| `undeploy -m MODULE` | Undeploy a module |
| `redirect -m MODULE -l URL` | Redirect module to URL |
| `redirect -m MODULE -rm` | Remove redirect |
| `reload` | Reload config and rebuild descriptor cache |
| `create_tenant -id ID [-e EXCLUDED]` | Create tenant |
| `delete_tenant -id ID` | Delete tenant |
