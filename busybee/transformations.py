"""Module descriptor transformation system for BusyBee.

This module provides functionality to transform FOLIO module descriptors
before they are posted to Okapi, based on configuration in config.yml.
"""

from typing import Any, Dict, List, Optional
import copy


def apply_transformations(
    module_descriptor: dict,
    module_name: str,
    config: dict,
    all_module_names: List[str]
) -> dict:
    """
    Apply all applicable transformations to a module descriptor.

    Args:
        module_descriptor: Original module descriptor dict
        module_name: Name of the module (e.g., 'mod-users')
        config: The 'module-transformations' config section
        all_module_names: List of all module names in deployment

    Returns:
        Transformed module descriptor (deep copy, original unchanged)
    """
    result = copy.deepcopy(module_descriptor)

    if "launchDescriptor" not in result:
        return result

    applied_transforms = []

    # Apply global defaults first
    if "defaults" in config:
        result = _apply_default_transformations(result, config["defaults"])
        applied_transforms.append("defaults")

    # Apply module-specific transformations
    if "modules" in config and module_name in config["modules"]:
        module_config = config["modules"][module_name]
        result, was_applied = _apply_module_transformations(result, module_config, all_module_names)
        if was_applied:
            applied_transforms.append(f"module:{module_name}")

    if applied_transforms:
        print(f"Transformed module descriptor for {module_name}: [{', '.join(applied_transforms)}]")

    return result


def _apply_default_transformations(descriptor: dict, defaults: dict) -> dict:
    """
    Apply global default transformations to a module descriptor.

    Args:
        descriptor: Module descriptor to transform
        defaults: The 'defaults' section from config

    Returns:
        Transformed descriptor
    """
    if "docker-args" in defaults:
        _apply_docker_args(descriptor, defaults["docker-args"])

    if "env" in defaults:
        _apply_env_transformations(descriptor, defaults["env"])

    return descriptor


def _apply_module_transformations(
    descriptor: dict,
    module_config: dict,
    all_module_names: List[str]
) -> tuple:
    """
    Apply per-module transformations with condition checking.

    Args:
        descriptor: Module descriptor to transform
        module_config: Configuration for this specific module
        all_module_names: List of all module names for condition checking

    Returns:
        Tuple of (transformed descriptor, was_applied boolean)
    """
    # Check conditions if present
    if "when" in module_config:
        if not _check_conditions(module_config["when"], all_module_names):
            return descriptor, False

    if "docker-args" in module_config:
        _apply_docker_args(descriptor, module_config["docker-args"])

    if "env" in module_config:
        _apply_env_transformations(descriptor, module_config["env"])

    return descriptor, True


def _check_conditions(conditions: dict, all_module_names: List[str]) -> bool:
    """
    Check if transformation conditions are met.

    Args:
        conditions: Dict with 'modules-present' and/or 'modules-absent' lists
        all_module_names: List of all module names in deployment

    Returns:
        True if all conditions are met, False otherwise
    """
    module_set = set(all_module_names)

    # Check modules-present: all listed modules must be present
    if "modules-present" in conditions:
        required = set(conditions["modules-present"])
        if not required.issubset(module_set):
            return False

    # Check modules-absent: all listed modules must be absent
    if "modules-absent" in conditions:
        forbidden = set(conditions["modules-absent"])
        if forbidden.intersection(module_set):
            return False

    return True


def _apply_docker_args(descriptor: dict, docker_args_config: dict) -> None:
    """
    Apply docker-args transformations to a module descriptor.

    Handles both scalar values (replace) and array values with action wrapper.

    Args:
        descriptor: Module descriptor to modify in place
        docker_args_config: The docker-args configuration dict
    """
    if "launchDescriptor" not in descriptor:
        return

    launch_desc = descriptor["launchDescriptor"]
    if "dockerArgs" not in launch_desc:
        launch_desc["dockerArgs"] = {}

    docker_args = launch_desc["dockerArgs"]

    _apply_docker_args_recursive(docker_args, docker_args_config, [])


def _apply_docker_args_recursive(target: dict, config: dict, path: List[str]) -> None:
    """
    Recursively apply docker-args configuration to target dict.

    Args:
        target: Target dict to modify
        config: Config dict with values to apply
        path: Current path for logging/debugging
    """
    for key, value in config.items():
        current_path = path + [key]

        if isinstance(value, dict):
            # Check if this is an action wrapper for arrays
            if "action" in value and "values" in value:
                _apply_docker_args_array(target, key, value)
            else:
                # Nested dict - recurse
                if key not in target:
                    target[key] = {}
                if isinstance(target[key], dict):
                    _apply_docker_args_recursive(target[key], value, current_path)
                else:
                    # Target is not a dict but config expects nesting - replace
                    target[key] = {}
                    _apply_docker_args_recursive(target[key], value, current_path)
        else:
            # Scalar value - replace
            target[key] = value


def _apply_docker_args_array(target: dict, key: str, config: dict) -> None:
    """
    Apply an array transformation to docker-args.

    Args:
        target: Target dict containing the array
        key: Key of the array in target
        config: Dict with 'action' and 'values' keys
    """
    action = config.get("action", "set")
    values = config.get("values", [])

    if action == "append":
        # Append to existing array or create new
        if key not in target:
            target[key] = []
        if isinstance(target[key], list):
            target[key].extend(values)
        else:
            # Not a list - replace with new list containing values
            print(f"Warning: Cannot append to non-list value at {key}, replacing instead")
            target[key] = values
    else:
        # Default to set - replace entirely
        target[key] = values


def _apply_env_transformations(descriptor: dict, env_config: List[dict]) -> None:
    """
    Apply environment variable transformations to a module descriptor.

    Args:
        descriptor: Module descriptor to modify in place
        env_config: List of env var transformation configs
    """
    if "launchDescriptor" not in descriptor:
        return

    launch_desc = descriptor["launchDescriptor"]
    if "env" not in launch_desc:
        launch_desc["env"] = []

    env_list = launch_desc["env"]

    for transform in env_config:
        _apply_single_env_transformation(env_list, transform)


def _apply_single_env_transformation(env_list: List[dict], transform: dict) -> None:
    """
    Apply a single environment variable transformation.

    Args:
        env_list: List of env var dicts to modify in place
        transform: Dict with 'name', 'value', and optional 'action' keys
    """
    name = transform.get("name")
    value = transform.get("value", "")
    action = transform.get("action", "set")

    if not name:
        print("Warning: env transformation missing 'name', skipping")
        return

    # Find existing env var by name
    existing_idx = None
    for idx, env_var in enumerate(env_list):
        if env_var.get("name") == name:
            existing_idx = idx
            break

    if action == "add":
        # Add new env var - warn if exists
        if existing_idx is not None:
            print(f"Warning: env var '{name}' already exists, skipping add")
            return
        env_list.append({"name": name, "value": value})

    elif action == "append":
        # Append to existing value - warn if not found
        if existing_idx is None:
            print(f"Warning: env var '{name}' not found for append, skipping")
            return
        env_list[existing_idx]["value"] += value

    elif action == "remove":
        # Remove env var if it exists
        if existing_idx is not None:
            del env_list[existing_idx]
        else:
            print(f"Warning: env var '{name}' not found for remove, skipping")

    else:
        # Default to 'set' - replace if exists, add if not
        if existing_idx is not None:
            env_list[existing_idx]["value"] = value
        else:
            env_list.append({"name": name, "value": value})
