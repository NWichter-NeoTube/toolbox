#!/usr/bin/env python3
"""Validate coolify-config.json schema.

Usage:
    python scripts/validate-config.py [path/to/coolify-config.json]

Exit codes:
    0 = valid
    1 = invalid or missing
"""
import json
import sys
from pathlib import Path


VALID_TYPES = {"website", "webapp", "shop", "app"}
VALID_SERVICE_NAMES = {"web", "frontend", "api", "storefront", "dashboard"}


def validate(config_path: str) -> list[str]:
    """Validate config and return list of errors (empty = valid)."""
    errors = []
    path = Path(config_path)

    if not path.exists():
        return [f"File not found: {config_path}"]

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # type
    proj_type = data.get("type")
    if not proj_type:
        errors.append("Missing required field: type")
    elif proj_type not in VALID_TYPES:
        errors.append(f"Invalid type '{proj_type}', must be one of: {VALID_TYPES}")

    # services
    services = data.get("services")
    if not services:
        errors.append("Missing required field: services")
    elif not isinstance(services, dict):
        errors.append("services must be an object")
    else:
        for svc_name, svc_config in services.items():
            if not isinstance(svc_config, dict):
                errors.append(f"services.{svc_name} must be an object")
                continue
            if "port" not in svc_config:
                errors.append(f"services.{svc_name} missing required field: port")
            elif not isinstance(svc_config["port"], int):
                errors.append(f"services.{svc_name}.port must be an integer")
            if "context" not in svc_config:
                errors.append(f"services.{svc_name} missing required field: context")
            if svc_name not in VALID_SERVICE_NAMES:
                errors.append(
                    f"Warning: services.{svc_name} is not a standard name "
                    f"({VALID_SERVICE_NAMES}), domain mapping may be unexpected"
                )

    # databases
    databases = data.get("databases", {})
    if not isinstance(databases, dict):
        errors.append("databases must be an object")
    else:
        for key in databases:
            if key not in ("postgres", "redis"):
                errors.append(f"Unknown database type: {key}")

    # type-specific validation
    if proj_type == "website":
        if databases and any(databases.values()):
            errors.append("Website type should not have databases")
    elif proj_type in ("webapp", "app"):
        if services and "api" not in services:
            errors.append(f"{proj_type} type should have an 'api' service")

    # storage
    storage = data.get("storage")
    if storage and not isinstance(storage, dict):
        errors.append("storage must be an object")

    # Dockerfile check
    if services:
        for svc_name, svc_config in services.items():
            ctx = svc_config.get("context", ".")
            dockerfile = Path(config_path).parent / ctx / "Dockerfile"
            if not dockerfile.exists():
                errors.append(
                    f"Dockerfile not found for service '{svc_name}' "
                    f"at {dockerfile}"
                )

    return errors


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "coolify-config.json"
    errors = validate(config_path)

    if not errors:
        print(f"OK: {config_path} is valid")
        sys.exit(0)
    else:
        print(f"ERRORS in {config_path}:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
