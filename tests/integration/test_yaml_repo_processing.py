# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration Test for YAML/Jinja Repo Processing
================================================

Verifies YAML/Jinja repo (.yaml/.jinja files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT.

Requirements: FR-5, AC-6.1 to AC-6.4
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestYamlRepoProcessing:
    """Integration tests for YAML/Jinja repo processing."""

    def test_yaml_automation_patterns(self, tmp_path: Path) -> None:
        """Test that YAML automation patterns are extracted into MODULE_BLUEPRINT.

        AC-6.1: Automation patterns (trigger, action, condition) should be captured.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create __init__.py to make it a valid Python package
        (owner_dir / "__init__.py").write_text("")

        # Create YAML automation file directly in repo root
        (owner_dir / "automation.yaml").write_text(
            """
# Home Assistant automation configurations
automation:
  - alias: "Turn off lights"
    trigger:
      platform: time
      at: "23:00:00"
    action:
      service: light.turn_off
      target:
        area_id: living_room

  - alias: "Climate control"
    trigger:
      platform: state
      entity_id: sensor.temperature
      for:
        minutes: 5
    condition:
      condition: numeric_state
      entity_id: sensor.temperature
      above: 22
    action:
      service: climate.set_hvac_mode
      target:
        entity_id: climate.living_room
      data:
        hvac_mode: "cool"

  - alias: "Morning routine"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
      - service: light.turn_on
        target:
          entity_id: light.living_room
      - service: notification.notify
        data:
          message: "Good morning!"
""".strip()
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files if "MODULE_BLUEPRINT" in f.read_text()
        ]

        assert len(blueprint_files) > 0, "YAML files should emit MODULE_BLUEPRINT"

        # Verify automation patterns are captured
        blueprint = blueprint_files[0].read_text()
        assert "automation" in blueprint, (
            "MODULE_BLUEPRINT should capture 'automation' pattern"
        )
        assert "trigger" in blueprint, (
            "MODULE_BLUEPRINT should capture 'trigger' pattern"
        )
        assert "action" in blueprint, "MODULE_BLUEPRINT should capture 'action' pattern"
        assert "condition" in blueprint, (
            "MODULE_BLUEPRINT should capture 'condition' pattern"
        )

    def test_yaml_script_extraction(self, tmp_path: Path) -> None:
        """Test that YAML script patterns are extracted into MODULE_BLUEPRINT.

        AC-6.2: Script patterns (sequence, service calls) should be captured.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create __init__.py to make it a valid Python package
        (owner_dir / "__init__.py").write_text("")

        # Create YAML script file directly in repo root
        (owner_dir / "scripts.yaml").write_text(
            """
# Home Assistant script configurations
script:
  hello_world:
    alias: "Hello World"
    description: "Say hello world"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.living_room
      - service: persistent_notification.create
        data:
          message: "Hello, World!"

  morning_routine:
    alias: "Morning Routine"
    description: "Start morning routine"
    sequence:
      - service: light.turn_on
        target:
          area_id: bedroom
      - service: light.turn_on
        target:
          area_id: bathroom
      - service: media_player.play_media
        target:
          entity_id: media_player.bedroom_speaker
        data:
          media_content_id: "radio://simple"
          media_content_type: "music"
      - service: notification.notify
        data:
          message: "Good morning! Time to start your day."

  bedtime:
    alias: "Bedtime"
    description: "Start bedtime routine"
    sequence:
      - service: light.turn_off
        target:
          area_id: living_room
      - service: light.turn_off
        target:
          area_id: kitchen
      - service: homeassistant.turn_off
""".strip()
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files if "MODULE_BLUEPRINT" in f.read_text()
        ]

        assert len(blueprint_files) > 0, "YAML files should emit MODULE_BLUEPRINT"

        # Verify script patterns are captured
        blueprint = blueprint_files[0].read_text()
        assert "script" in blueprint, "MODULE_BLUEPRINT should capture 'script' pattern"
        assert "sequence" in blueprint, (
            "MODULE_BLUEPRINT should capture 'sequence' pattern"
        )
        assert "service" in blueprint, (
            "MODULE_BLUEPRINT should capture 'service' pattern"
        )

    def test_yaml_sensor_extraction(self, tmp_path: Path) -> None:
        """Test that YAML sensor patterns are extracted into MODULE_BLUEPRINT.

        AC-6.3: Sensor patterns (template, command, platform) should be captured.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create __init__.py to make it a valid Python package
        (owner_dir / "__init__.py").write_text("")

        # Create YAML sensor file directly in repo root
        (owner_dir / "sensors.yaml").write_text(
            """
# Home Assistant sensor configurations
sensor:
  - platform: template
    sensors:
      room_temperature:
        value_template: "{{ state('sensor.bedroom_temperature') }}"
        unit_of_measurement: "°C"
        icon: "mdi:thermometer"

      room_humidity:
        value_template: "{{ state('sensor.bedroom_humidity') }}"
        unit_of_measurement: "%"
        icon: "mdi:water-percent"

  - platform: command
    name: "System Load"
    command: "uptime -p"
    unit_of_measurement: "up"
    value_template: >
      {{ value | regex_replace('up (\\d+)', '1') | int }}
    scan_interval: 60

  - platform: rest
    name: "API Status"
    resource: "http://example.com/api/status"
    value_template: "{{ value_json.status }}"
    headers:
      Authorization: "Bearer token"
    sensor:
      - name: "Response Time"
        value_template: "{{ value_json.response_time }}"
        unit_of_measurement: "ms"
""".strip()
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files if "MODULE_BLUEPRINT" in f.read_text()
        ]

        assert len(blueprint_files) > 0, "YAML files should emit MODULE_BLUEPRINT"

        # Verify sensor patterns are captured
        blueprint = blueprint_files[0].read_text()
        assert "sensor" in blueprint, "MODULE_BLUEPRINT should capture 'sensor' pattern"
        assert "template" in blueprint, (
            "MODULE_BLUEPRINT should capture 'template' pattern"
        )
        assert "command" in blueprint, (
            "MODULE_BLUEPRINT should capture 'command' pattern"
        )
        assert "value_template" in blueprint, (
            "MODULE_BLUEPRINT should capture 'value_template' pattern"
        )

    def test_yaml_jinja_template_detection(self, tmp_path: Path) -> None:
        """Test that YAML files with Jinja templates are detected and processed.

        AC-6.4: Jinja templates ({{ }}, {% %}) should be captured in MODULE_BLUEPRINT.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create __init__.py to make it a valid Python package
        (owner_dir / "__init__.py").write_text("")

        # Create YAML file with Jinja templates directly in repo root
        (owner_dir / "templates.yaml").write_text(
            """
# Home Assistant templates with Jinja
automation:
  - alias: "Dynamic notification"
    trigger:
      platform: state
      entity_id: sensor.system_load
    condition:
      condition: template
      value_template: "{{ state_attr('sensor.system_load', 'load_1m') | float > 0.8 }}"
    action:
      - service: persistent_notification.create
        data:
          title: "High Load Alert"
          message: >
            System load is {{ state_attr('sensor.system_load', 'load_1m') | round(2) }}.
            This is above the threshold of 0.8.
            {{ now() | strftime('%Y-%m-%d %H:%M:%S') }}

script:
  notify_when_offline:
    alias: "Notify when device offline"
    sequence:
      - service: persistent_notification.create
        data:
          message: >
            Device {{ device_name }} is offline.
            Last seen: {{ device_last_seen | default('Unknown') }}.

sensor:
  - platform: template
    sensors:
      device_status:
        value_template: >
          {% if is_state('device_tracker.phone', 'home') %}
            Online
          {% else %}
            Offline
          {% endif %}
        icon_template: >
          {% if is_state('device_tracker.phone', 'home') %}
            mdi:check-circle
          {% else %}
            mdi:close-circle
          {% endif %}
""".strip()
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files if "MODULE_BLUEPRINT" in f.read_text()
        ]

        assert len(blueprint_files) > 0, "YAML files should emit MODULE_BLUEPRINT"

        # Verify Jinja templates are captured
        blueprint = blueprint_files[0].read_text()
        assert "jinja" in blueprint or "template" in blueprint, (
            "MODULE_BLUEPRINT should capture Jinja template patterns"
        )
        assert "{{" in blueprint or "{%" in blueprint, (
            "MODULE_BLUEPRINT should capture Jinja syntax"
        )
