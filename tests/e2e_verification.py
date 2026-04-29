#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""E2E verification: Process a realistic repo through the full pipeline.

The processor's source_root = base_dir/raw_subdir/category.
Each subdirectory of source_root is treated as a repo_dir.
Governance files and test files must be inside the repo_dir.

Correct structure:
    owner/
        <category>/         <- source_root
            <repo_name>/    <- repo_dir
                .gitlab-ci.yml   <- governance here (inside repo_dir!)
                tests/
                    test_*.py
                custom_components/
                    smart_thermostat/
                        manifest.json
                        __init__.py
                        climate.py
                        config.py
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from src.discovery.metadata_enricher import ProcessingConfig, RepoProcessor


@pytest.fixture
def e2e_config():
    """Create a realistic HA-style repo and processor config."""
    work_dir = Path(tempfile.mkdtemp(prefix="e2e_test_"))

    try:
        # Structure: owner/category/repo_name/...
        # Processor iterates: source_root -> owner_dir (subdirs) -> repo_dir (subdirs of owner_dir)
        # We need: repo_dir with governance files + tests + modules
        repo_dir = work_dir / "owner" / "myrepo" / "thermostat"
        repo_dir.mkdir(parents=True)

        # Component directory (the actual module)
        component = repo_dir / "custom_components" / "smart_thermostat"
        component.mkdir(parents=True)

        # Governance file MUST be inside the processor's repo_dir (custom_components/).
        # The processor iterates: source_root/thermostat/custom_components/ as repo_path.
        # So governance goes at custom_components/.gitlab-ci.yml.
        (repo_dir / "custom_components" / ".gitlab-ci.yml").write_text("""
stages:
  - test
  - lint
  - deploy

test:
  stage: test
  script:
    - pytest tests/
    - pytest --cov=custom_components/

lint:
  stage: lint
  script:
    - ruff check .
    - pylint custom_components/

deploy:
  stage: deploy
  script:
    - echo "Deploying thermostat component"
  only:
    - main
""")

        # manifest.json (module anchor)
        (component / "manifest.json").write_text(
            json.dumps(
                {
                    "name": "Smart Thermostat",
                    "version": "2.1.0",
                    "domain": "smart_thermostat",
                    "dependencies": [],
                    "requirements": [],
                },
                indent=2,
            )
        )

        # __init__.py (module anchor)
        (component / "__init__.py").write_text("""
# Smart Thermostat integration
from homeassistant.core import HomeAssistant

DOMAIN = "smart_thermostat"
PLATFORMS = ["climate"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass, entry):
    return True

async def async_unload_entry(hass, entry):
    return True
""")

        # climate.py (logic file with test)
        (component / "climate.py").write_text("""
from homeassistant.components.climate import ClimateEntity
from homeassistant.core import HomeAssistant

class SmartThermostat(ClimateEntity):
    '''Smart Thermostat entity with comprehensive climate control.'''

    _attr_min_temp = 7.0
    _attr_max_temp = 35.0
    _attr_target_temp_step = 0.5

    def __init__(self, hass):
        self._hass = hass
        self._target_temp = 21.0
        self._current_temp = 20.0
        self._is_heating = False
        self._is_cooling = False
        self._mode = "auto"
        self._fan_mode = "auto"

    @property
    def target_temp(self) -> float:
        return self._target_temp

    @property
    def current_temp(self) -> float:
        return self._current_temp

    @property
    def is_heating(self) -> bool:
        return self._is_heating

    @property
    def is_cooling(self) -> bool:
        return self._is_cooling

    @property
    def hvac_mode(self) -> str:
        return self._mode

    async def async_set_temperature(self, temperature):
        self._target_temp = temperature

    async def async_turn_on(self):
        self._is_heating = True

    async def async_turn_off(self):
        self._is_heating = False
        self._is_cooling = False

    async def async_set_hvac_mode(self, mode):
        self._mode = mode

    async def async_set_fan_mode(self, fan_mode):
        self._fan_mode = fan_mode

    @property
    def fan_mode(self) -> str:
        return self._fan_mode

    @property
    def supported_features(self):
        return 1  # TARGET_TEMPERATURE
""")

        # config.py (logic file with test)
        (component / "config.py").write_text("""
# Configuration management for Smart Thermostat
# Handles validation, defaults, and schema definitions
import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_TEMP = 35.0
DEFAULT_MIN_TEMP = 7.0
DEFAULT_HYSTERESIS = 0.5
DEFAULT_TARGET_OFFSET = 0.0
DEFAULT_PREHEAT_TIME = 30
DEFAULT_SENSOR_TIMEOUT = 60

CONFIG_SCHEMA = {
    'max_temp': 35.0,
    'min_temp': 7.0,
    'hysteresis': 0.5,
    'target_offset': 0.0,
    'preheat_time': 30,
    'sensor_timeout': 60,
    'auto_mode': True,
    'eco_mode': False,
}

def validate_config(config):
    '''Validate thermostat configuration with comprehensive checks.

    Checks temperature bounds, hysteresis range, sensor connectivity,
    and mode compatibility. Returns list of error strings (empty if valid).
    '''
    errors = []
    warnings = []

    # Temperature validation
    max_temp = config.get('max_temp', 35)
    min_temp = config.get('min_temp', 7)
    if max_temp < min_temp:
        errors.append('max_temp must be greater than min_temp')
    if max_temp > 50:
        warnings.append('max_temp exceeds 50C - may indicate misconfiguration')
    if min_temp < 0:
        errors.append('min_temp cannot be below 0C')

    # Hysteresis validation
    hysteresis = config.get('hysteresis', 0.5)
    if not (0 <= hysteresis <= 2.0):
        errors.append('hysteresis must be between 0 and 2.0 degrees')

    # Preheat time validation
    preheat = config.get('preheat_time', 30)
    if preheat < 0:
        errors.append('preheat_time cannot be negative')
    if preheat > 300:
        warnings.append('preheat_time exceeds 5 minutes')

    # Sensor timeout validation
    timeout = config.get('sensor_timeout', 60)
    if timeout < 10:
        warnings.append('sensor_timeout below 10s - may cause false disconnects')
    if timeout > 300:
        errors.append('sensor_timeout must not exceed 300 seconds')

    # Log any warnings
    for w in warnings:
        _LOGGER.warning('Config warning: %s', w)

    return errors

def get_default_config():
    '''Return the default configuration dictionary.'''
    return dict(CONFIG_SCHEMA)

def merge_config(base, override):
    '''Merge override config into base config.'''
    result = dict(base)
    for key, value in override.items():
        if key in base:
            result[key] = value
        else:
            _LOGGER.warning('Unknown config key: %s', key)
    return result
""")

        # sensors.py (logic file WITHOUT a test - produces TYPE 3 LOGIC_ONLY)
        # Must be >= 800 chars for LOGIC_ONLY_MIN_CHARS threshold
        # Also includes a gold pattern to pass the gold filter for .py files
        (component / "sensors.py").write_text("""
# Temperature sensor helper functions for Smart Thermostat
# Provides utilities for humidity calculation and comfort classification
# All functions operate on raw sensor data from Home Assistant climate entities
# Related to ClimateEntity domain sensor readings and thermostat integration
import logging
import math
from typing import Optional, Tuple

_LOGGER = logging.getLogger(__name__)

# Constants for sensor calibration
CALIBRATION_OFFSET = 0.5
MAX_READING_INTERVAL = 30  # seconds
TEMPERATURE_UNITS = {
    'celsius': 'C',
    'fahrenheit': 'F',
    'kelvin': 'K',
}

def calculate_humidity_index(temp: float, humidity: float) -> float:
    '''Calculate heat index based on temperature and humidity readings.

    Uses the National Weather Service formula for heat index calculation.
    Returns the heat index value rounded to one decimal place.
    Accounts for sensor calibration offset applied to raw readings.
    '''
    calibrated_temp = temp + CALIBRATION_OFFSET
    if calibrated_temp < 27:
        return calibrated_temp
    hi = -8.784695 + 1.61139411 * calibrated_temp
    hi += 2.338549 * humidity
    hi += -0.14611605 * calibrated_temp * humidity
    hi += -1.2308094e-2 * calibrated_temp * calibrated_temp
    hi += -1.6424828e-2 * humidity * humidity
    return round(hi, 1)

def classify_comfort(temp: float, humidity: float) -> str:
    '''Classify the comfort level based on temperature and humidity.

    Returns one of: cold, hot, dry, humid, or comfortable.
    Uses standard comfort zone boundaries defined by ASHRAE 55.
    The classification considers both thermal and moisture comfort.
    '''
    if temp < 18:
        return "cold"
    if temp > 28:
        return "hot"
    if humidity < 30:
        return "dry"
    if humidity > 70:
        return "humid"
    return "comfortable"

def compute_thermostat_setpoint(target: float, offset: float, outdoor_temp: float) -> float:
    '''Compute adjusted thermostat setpoint based on outdoor temperature.

    Adjusts the target temperature based on the difference between
    outdoor temperature and a baseline of 20C. Accounts for heat loss
    or gain through walls and windows during extreme weather conditions.
    '''
    delta = outdoor_temp - 20.0
    if abs(delta) > 10:
        _LOGGER.warning('Extreme outdoor temp: %s', outdoor_temp)
    return target + delta * 0.01 + (offset * 0.1)

def validate_sensor_reading(value: float, sensor_type: str) -> Tuple[bool, Optional[str]]:
    '''Validate a sensor reading for type-specific constraints.

    Checks temperature ranges, humidity bounds, and other type-specific
    constraints. Returns (is_valid, error_message) tuple.
    '''
    valid = True
    error = None
    if sensor_type == 'temperature':
        if value < -40 or value > 60:
            valid = False
            error = 'Temperature out of sensor range'
    elif sensor_type == 'humidity':
        if value < 0 or value > 100:
            valid = False
            error = 'Humidity out of valid range'
    return valid, error

def calculate_rate_of_change(current: float, previous: float, dt: float) -> float:
    '''Calculate the rate of change between two sensor readings.

    Returns the rate in units per second. Handles edge cases where
    dt is zero or negative by returning zero rate of change.
    '''
    if dt <= 0:
        _LOGGER.debug('Invalid time delta for rate calculation: %s', dt)
        return 0.0
    return (current - previous) / dt
""")

        # strings.json (module anchor)
        (component / "strings.json").write_text(
            json.dumps(
                {
                    "climate": {
                        "mode_heat": "Heat",
                        "mode_cool": "Cool",
                        "mode_auto": "Auto",
                        "mode_off": "Off",
                    },
                    "services": {
                        "set_schedule": {
                            "name": "Set Schedule",
                            "description": "Set thermostat schedule",
                        }
                    },
                },
                indent=2,
            )
        )

        # Test files - find_test uses: repo_root/tests/<relative_parent>/test_<name>
        # The repo_root for this fixture is custom_components/ (processor iterates subdirs).
        # For climate.py at smart_thermostat/climate.py (relative to repo_root):
        #   looks for: repo_root/tests/smart_thermostat/test_climate.py
        tests_dir = repo_dir / "tests" / "smart_thermostat"
        tests_dir.mkdir(parents=True)

        (tests_dir / "test_climate.py").write_text("""
import sys
sys.path.insert(0, '../../../custom_components/smart_thermostat')
import climate

def test_smart_thermostat_defaults():
    st = climate.SmartThermostat(None)
    assert st.target_temp == 21.0
    assert st.current_temp == 20.0
    assert st.is_heating is False

def test_set_temperature():
    st = climate.SmartThermostat(None)
    st.async_set_temperature(22.0)
    assert st.target_temp == 22.0

def test_turn_on_off():
    st = climate.SmartThermostat(None)
    st.async_turn_on()
    assert st.is_heating is True
    st.async_turn_off()
    assert st.is_heating is False
""")

        (tests_dir / "test_config.py").write_text("""
import sys
sys.path.insert(0, '../../../custom_components/smart_thermostat')
import config

def test_validate_config_normal():
    errors = config.validate_config({'max_temp': 30, 'min_temp': 10, 'hysteresis': 0.5})
    assert errors == [], f'Expected no errors, got {errors}'

def test_validate_config_invalid_temps():
    errors = config.validate_config({'max_temp': 5, 'min_temp': 30, 'hysteresis': 0.5})
    assert any('max_temp must be greater than min_temp' in e for e in errors)

def test_validate_config_bad_hysteresis():
    errors = config.validate_config({'hysteresis': 5.0})
    assert any('hysteresis must be between 0 and 2.0' in e for e in errors)

def test_validate_config_negative_preheat():
    errors = config.validate_config({'preheat_time': -10})
    assert any('preheat_time cannot be negative' in e for e in errors)

def test_get_default_config():
    defaults = config.get_default_config()
    assert defaults['max_temp'] == 35.0
    assert defaults['min_temp'] == 7.0

def test_merge_config():
    base = config.get_default_config()
    merged = config.merge_config(base, {'max_temp': 40, 'unknown_key': 'x'})
    assert merged['max_temp'] == 40
    assert 'unknown_key' not in merged
""")

        # Also add a README at repo root for blueprint
        (repo_dir / "README.md").write_text("""
# Smart Thermostat Component

A smart thermostat integration for Home Assistant.

## Features
- Temperature control
- Schedule support
- Eco mode

## Installation
Copy the custom_components directory to your Home Assistant config.
""")

        # Write YAML config
        config_file = work_dir / "e2e_config.yaml"
        config_file.write_text(f"""
base_dir: {work_dir}
raw_subdir: owner
output_subdir: data/output
category: myrepo
profile: homeassistant
module_discovery_strategy: manifest
on_parse_error: skip
""")

        yield {
            "work_dir": work_dir,
            "config_file": config_file,
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def test_e2e_fragment_types(e2e_config):
    """Process a realistic HA-style repo through the full pipeline.

    Verifies all four fragment types are generated:
    - TYPE 1: FUNCTIONAL_UNIT (code + test context)
    - TYPE 3: LOGIC_ONLY (standalone logic files)
    - TYPE 4: MODULE_BLUEPRINT (anchor + README aggregation)
    - TYPE 5: GOVERNANCE_RULES (repo governance files)
    """
    work_dir = e2e_config["work_dir"]
    config_file = e2e_config["config_file"]

    # Load config and run processor
    config = ProcessingConfig(**yaml.safe_load(config_file.read_text()))
    processor = RepoProcessor(config)
    processor.run()

    # Check output
    output_dir = work_dir / "data" / "output" / "myrepo"

    results = {
        "type1_functional_unit": 0,
        "type3_logic_only": 0,
        "type4_module_blueprint": 0,
        "type5_governance": 0,
        "bundle_files": [],
        "modules_found": processor._stats.get("modules_found", 0),
    }

    if output_dir.exists():
        for txt_file in sorted(output_dir.rglob("*.txt")):
            rel = txt_file.relative_to(output_dir)
            content = txt_file.read_text()
            if "Type: FUNCTIONAL_UNIT" in content:
                results["type1_functional_unit"] += 1
            elif "Type: LOGIC_ONLY" in content:
                results["type3_logic_only"] += 1
            elif "Type: MODULE_BLUEPRINT" in content:
                results["type4_module_blueprint"] += 1
            results["bundle_files"].append(str(rel))

    # Check governance bundles
    gov_dir = output_dir / "_governance"
    if gov_dir.exists():
        for gov_file in sorted(gov_dir.glob("*.txt")):
            content = gov_file.read_text()
            if "Type: GOVERNANCE_RULES" in content:
                results["type5_governance"] += 1
            results["bundle_files"].append(f"_governance/{gov_file.name}")

    # Print summary
    print(f"\n  Modules found: {results['modules_found']}")
    print(f"  TYPE 1 (FUNCTIONAL_UNIT): {results['type1_functional_unit']}")
    print(f"  TYPE 3 (LOGIC_ONLY): {results['type3_logic_only']}")
    print(f"  TYPE 4 (MODULE_BLUEPRINT): {results['type4_module_blueprint']}")
    print(f"  TYPE 5 (GOVERNANCE_RULES): {results['type5_governance']}")
    print(f"  Bundle files: {results['bundle_files']}")

    # Verify
    assert results["modules_found"] > 0, f"No modules found. Stats: {processor._stats}"
    assert results["type4_module_blueprint"] > 0, (
        f"No MODULE_BLUEPRINT bundles. Files: {results['bundle_files']}"
    )
    assert results["type5_governance"] > 0, (
        f"No GOVERNANCE_RULES bundles. Files: {results['bundle_files']}"
    )
    assert results["type1_functional_unit"] > 0, (
        f"No FUNCTIONAL_UNIT bundles. Files: {results['bundle_files']}"
    )
    assert results["type3_logic_only"] > 0, (
        f"No LOGIC_ONLY bundles. Files: {results['bundle_files']}"
    )

    total = (
        results["type1_functional_unit"]
        + results["type3_logic_only"]
        + results["type4_module_blueprint"]
        + results["type5_governance"]
    )
    assert total > 0, "No bundle types emitted"


def test_e2e_bundle_content(e2e_config):
    """Verify the content structure of generated bundles."""
    work_dir = e2e_config["work_dir"]
    config_file = e2e_config["config_file"]

    config = ProcessingConfig(**yaml.safe_load(config_file.read_text()))
    processor = RepoProcessor(config)
    processor.run()

    output_dir = work_dir / "data" / "output" / "myrepo"
    assert output_dir.exists(), "Output directory not created"

    bundle_files = list(output_dir.rglob("*.txt"))
    gov_dir = output_dir / "_governance"
    if gov_dir.exists():
        bundle_files.extend(gov_dir.glob("*.txt"))

    assert len(bundle_files) > 0, "No bundle files generated"

    # Check that bundles have expected structure
    for bf in bundle_files[:5]:
        content = bf.read_text()
        assert "=== LOGICAL ENTITY:" in content, (
            f"Missing LOGICAL ENTITY header in {bf}"
        )
        assert "Context:" in content, f"Missing Context line in {bf}"
        assert "Type:" in content, f"Missing Type line in {bf}"
