from typing import Dict

MOD_REGISTRY_URL = "http://folio-registry.aws.indexdata.com"
LOCAL_OKAPI_URL = "http://localhost:9130"
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
    {"name": "DB_HOST", "value": f"vagrant"},
    {"name": "DB_PORT", "value": f"5432"},
    {"name": "DB_DATABASE", "value": f"okapi"},
    {"name": "DB_USERNAME", "value": f"folio_admin"},
    {"name": "DB_PASSWORD", "value": f"password"},
    {"name": "DB_MAXPOOLSIZE", "value": f"20"},
    {"name": "KAFKA_HOST", "value": f"vagrant"},
    {"name": "KAFKA_PORT", "value": f"9092"},
    {"name": "ENV", "value": f"dev"},
    {"name": "ELASTICSEARCH_URL", "value": f"http://vagrant:9200"},
    {"name": "OKAPI_URL", "value": LOCAL_OKAPI_URL},
    {"name": "JAVA_DEBUG", "value": f"true"}

]

CONFIG_YAML: dict = None

ENV_VARS = {}
ENV_VARS['DB_PASSWORD'] = 'password'
ENV_VARS['DB_USERNAME'] = 'folio_admin'
ENV_VARS['DB_DATABASE'] = 'okapi'
ENV_VARS['DB_HOST'] = 'vagrant'
ENV_VARS['DB_PORT'] = '5432'
ENV_VARS['OKAPI_URL'] = LOCAL_OKAPI_URL
ENV_VARS['KAFKA_HOST'] = 'vagrant'
ENV_VARS['KAFKA_PORT'] = '9092'

MODULES = {}

JAR_DIR = 'folio_jars'
LOG_DIR = 'logs'

OTEL_TRACES_EXPORTER = 'jaeger'
OTEL_EXPORTER_JAEGER_ENDPOINT = 'http://olamimacmini:14250'