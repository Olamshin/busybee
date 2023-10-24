from typing import Any

from busybee.modules import ModuleInterface
import os


class GlobalVars:
    _instance = None

    MOD_REGISTRY_URL = "http://folio-registry.aws.indexdata.com"
    LOCAL_OKAPI_URL = "http://localhost:9130"
    TENANT_ID = "diku"
    tenant_name = "Datalogisk Institut"
    tenant_desc = "Danish Library Technology Institute"
    ADMIN_USER_ID = None
    ADMIN_USER = {
        "username": "diku_admin",
        "password": "admin",
        "first_name": "",
        "last_name": "Superuser",
        "email": "admin@example.org",
        "perms_users_assign": "yes",
    }
    MINIMAL_MOD_NAMES = [
        "mod-data-import",
        "mod-source-record-manager",
        "mod-source-record-storage",
        "mod-data-import-converter-storage",
    ]

    MINIMAL_MOD_DATA = []

    OKAPI_ENV = [
        {"name": "DB_HOST", "value": f"olamiebsco"},
        {"name": "DB_PORT", "value": f"5432"},
        {"name": "DB_DATABASE", "value": f"okapi"},
        {"name": "DB_USERNAME", "value": f"folio_admin"},
        {"name": "DB_PASSWORD", "value": f"password"},
        {"name": "DB_MAXPOOLSIZE", "value": f"20"},
        {"name": "KAFKA_HOST", "value": f"olamiebsco"},
        {"name": "KAFKA_PORT", "value": f"9092"},
        {"name": "ENV", "value": f"dev"},
        {"name": "ELASTICSEARCH_URL", "value": f"http://olamiebsco:9200"},
        {"name": "OKAPI_URL", "value": LOCAL_OKAPI_URL},
        {"name": "JAVA_DEBUG", "value": f"true"},
    ]

    CONFIG_YAML: dict[str, Any] = {}

    ENV_VARS = {}
    ENV_VARS["DB_PASSWORD"] = "password"
    ENV_VARS["DB_USERNAME"] = "folio_admin"
    ENV_VARS["DB_DATABASE"] = "okapi"
    ENV_VARS["DB_HOST"] = "olamiebsco"
    ENV_VARS["DB_PORT"] = "5432"
    ENV_VARS["OKAPI_URL"] = LOCAL_OKAPI_URL
    ENV_VARS["KAFKA_HOST"] = "olamiebsco"
    ENV_VARS["KAFKA_PORT"] = "9092"
    ENV_VARS["ELASTICSEARCH_URL"] = "http://olamiebsco:9200"
    ENV_VARS["KAFKA_PRODUCER_TENANT_COLLECTION"] = "ALL"

    MODULES: dict[str, ModuleInterface] = {}

    BASE_DIR = ".busybee"
    JAR_DIR = os.path.join(BASE_DIR, "folio_jars")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    OTEL_TRACES_EXPORTER = "jaeger"
    OTEL_EXPORTER_JAEGER_ENDPOINT = "http://olamimacmini:14250"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalVars, cls).__new__(cls)
        return cls._instance
