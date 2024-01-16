import os
import shutil

DIRECTORY_NAME = '.busybee'
USER_HOME_DIR = os.path.join(os.path.expanduser("~"), DIRECTORY_NAME)

CONFIG_LOCATIONS = [
    os.path.join(USER_HOME_DIR, "config.yml"),
    os.path.normpath(os.path.join(".", DIRECTORY_NAME)),
]

class MissingConfigurationException(Exception):
    def __init__(self, message="Configuration parameter is missing"):
        self.message = message
        super().__init__(self.message)



def find_config_file(possible_locations):
    for location in possible_locations:
        if os.path.isfile(location):
            return location
    return None

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def gen_config():
    yaml_file_path = resource_path("config.yml")
    if not os.path.exists(USER_HOME_DIR):
        os.makedirs(USER_HOME_DIR)
    config_path = os.path.join(USER_HOME_DIR, "config.yml")
    shutil.copyfile(yaml_file_path, config_path)
    return config_path