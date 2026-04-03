# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""Repository fixture helpers for creating test repositories.

These helpers create properly structured repositories that the RepoProcessor
can successfully process.

Repository structure expected by RepoProcessor:
    owner/
        <category>/              # e.g., "myrepo"
            __init__.py (optional)
            manifest.json (optional)
            <component_dir>/
                component.py
                tests/
                    test_component.py
"""

from pathlib import Path
from typing import Optional


def create_python_repo(
    base_dir: Path,
    category: str = "myrepo",
    component_name: str = "test_component",
    include_test: bool = True,
) -> Path:
    """Create a Python repository with proper structure for RepoProcessor.

    Args:
        base_dir: Base directory where owner/ will be created
        category: Category name (repo directory name under owner/)
        component_name: Name of the component directory
        include_test: Whether to include test files

    Returns:
        Path to the created repository root
    """
    # Create owner directory structure
    owner_dir = base_dir / "owner"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository directory
    repo_dir = owner_dir / category
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory
    component_dir = repo_dir / component_name
    component_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest.json (required for manifest strategy)
    manifest = component_dir / "manifest.json"
    manifest.write_text(
        '{\n'
        f'    "name": "{component_name}",\n'
        '    "version": "1.0.0",\n'
        f'    "domain": "{component_name}"\n'
        '}'
    )

    return repo_dir


def create_python_component(
    component_dir: Path,
    code: str,
    test_code: Optional[str] = None,
) -> None:
    """Create Python component files.

    Args:
        component_dir: Directory for the component
        code: Python component code
        test_code: Optional test code
    """
    # Create component file
    component_file = component_dir / "component.py"
    component_file.write_text(code)

    # Create tests directory and test file if requested
    if test_code:
        tests_dir = component_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_file = tests_dir / "test_component.py"
        test_file.write_text(test_code)


def create_typescript_repo(
    base_dir: Path,
    category: str = "myrepo",
    component_name: str = "test_component",
    include_test: bool = True,
) -> Path:
    """Create a TypeScript repository with proper structure.

    Args:
        base_dir: Base directory where owner/ will be created
        category: Category name (repo directory name under owner/)
        component_name: Name of the component directory
        include_test: Whether to include test files

    Returns:
        Path to the created repository root
    """
    # Create owner directory structure
    owner_dir = base_dir / "owner"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository directory
    repo_dir = owner_dir / category
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory
    component_dir = repo_dir / component_name
    component_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest.json
    manifest = component_dir / "manifest.json"
    manifest.write_text(
        '{\n'
        f'    "name": "{component_name}",\n'
        '    "version": "1.0.0",\n'
        f'    "domain": "{component_name}"\n'
        '}'
    )

    return repo_dir


def create_typescript_component(
    component_dir: Path,
    code: str,
    test_code: Optional[str] = None,
) -> None:
    """Create TypeScript component files.

    Args:
        component_dir: Directory for the component
        code: TypeScript component code
        test_code: Optional test code
    """
    # Create component file
    component_file = component_dir / "component.ts"
    component_file.write_text(code)

    # Create test file if requested
    if test_code:
        test_file = component_dir / "test_component.ts"
        test_file.write_text(test_code)


def create_php_repo(
    base_dir: Path,
    category: str = "myrepo",
    include_test: bool = True,
) -> Path:
    """Create a PHP repository with proper structure.

    Args:
        base_dir: Base directory where owner/ will be created
        category: Category name (repo directory name under owner/)
        include_test: Whether to include test files

    Returns:
        Path to the created repository root
    """
    # Create owner directory structure
    owner_dir = base_dir / "owner"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository directory
    repo_dir = owner_dir / category
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create src directory structure (typical for PHP)
    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Create composer.json
    composer = repo_dir / "composer.json"
    composer.write_text(
        '{\n'
        '    "name": "app/services",\n'
        '    "type": "library",\n'
        '    "autoload": {\n'
        '        "psr-4": {\n'
        '            "App\\\\\\\\": "src/"\n'
        '        }\n'
        '    }\n'
        '}'
    )

    return repo_dir


def create_yaml_repo(
    base_dir: Path,
    category: str = "myrepo",
    include_test: bool = True,
) -> Path:
    """Create a YAML repository with proper structure.

    Args:
        base_dir: Base directory where owner/ will be created
        category: Category name (repo directory name under owner/)
        include_test: Whether to include test files

    Returns:
        Path to the created repository root
    """
    # Create owner directory structure
    owner_dir = base_dir / "owner"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository directory
    repo_dir = owner_dir / category
    repo_dir.mkdir(parents=True, exist_ok=True)

    return repo_dir


def create_yaml_files(
    repo_dir: Path,
    automation_code: str,
    script_code: Optional[str] = None,
    sensor_code: Optional[str] = None,
    jinja_code: Optional[str] = None,
) -> None:
    """Create YAML files in repository.

    Args:
        repo_dir: Repository directory
        automation_code: YAML automation code
        script_code: Optional YAML script code
        sensor_code: Optional YAML sensor code
        jinja_code: Optional YAML Jinja template code
    """
    # Create automation.yaml
    (repo_dir / "automation.yaml").write_text(automation_code)

    # Create script.yaml if provided
    if script_code:
        (repo_dir / "script.yaml").write_text(script_code)

    # Create sensors.yaml if provided
    if sensor_code:
        (repo_dir / "sensors.yaml").write_text(sensor_code)

    # Create templates.yaml if provided
    if jinja_code:
        (repo_dir / "templates.yaml").write_text(jinja_code)
