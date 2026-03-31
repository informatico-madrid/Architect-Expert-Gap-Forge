# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration Test for PHP Repo Processing
=========================================

Verifies PHP repo (.php files) generates TYPE 3 LOGIC_ONLY + TYPE 4 MODULE_BLUEPRINT.

Requirements: FR-5, AC-7.1 to AC-7.4
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestPhpRepoProcessing:
    """Integration tests for PHP repo processing."""

    def test_php_namespace_extraction(self, tmp_path: Path) -> None:
        """Test that PHP namespaces are extracted into MODULE_BLUEPRINT.

        AC-7.1: Namespace declarations should be captured in MODULE_BLUEPRINT.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create PHP directory structure
        services = owner_dir / "src" / "Services"
        services.mkdir(parents=True)

        # Create PHP file with namespace
        (services / "UserService.php").write_text("""
<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }

    public function findUser(string $email): ?User {
        foreach ($this->users as $user) {
            if ($user->email === $email) {
                return $user;
            }
        }
        return null;
    }

    public function deleteUser(string $email): bool {
        $index = array_search($email, array_column($this->users, 'email'));
        if ($index !== false) {
            unset($this->users[$index]);
            return true;
        }
        return false;
    }
}
""".strip())

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
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )

        # Verify namespace is captured
        blueprint = blueprint_files[0].read_text()
        assert 'App' in blueprint, (
            "MODULE_BLUEPRINT should capture 'App' namespace"
        )
        assert 'Services' in blueprint, (
            "MODULE_BLUEPRINT should capture 'Services' namespace path"
        )

    def test_php_class_methods_extraction(self, tmp_path: Path) -> None:
        """Test that PHP class methods are extracted into MODULE_BLUEPRINT.

        AC-7.2: Method signatures should be captured in MODULE_BLUEPRINT.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create PHP directory structure
        controllers = owner_dir / "src" / "Controllers"
        controllers.mkdir(parents=True)

        # Create PHP file with multiple methods
        (controllers / "UserController.php").write_text("""
<?php

namespace App\\Controllers;

use App\\Services\\UserService;

class UserController {
    private UserService $userService;

    public function __construct(UserService $userService) {
        $this->userService = $userService;
    }

    public function handleRequest(string $action, array $data): ?array {
        switch ($action) {
            case 'create':
                return $this->userService->createUser(
                    $data['name'],
                    $data['email']
                );
            case 'find':
                return $this->userService->findUser($data['email']);
            case 'delete':
                return $this->userService->deleteUser($data['email']);
            default:
                return null;
        }
    }

    public function listUsers(): array {
        return $this->userService->getAllUsers();
    }

    public function updateUser(string $email, array $data): bool {
        return $this->userService->updateUser($email, $data);
    }
}
""".strip())

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
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )

        # Verify methods are captured
        blueprint = blueprint_files[0].read_text()
        assert 'handleRequest' in blueprint, (
            "MODULE_BLUEPRINT should capture handleRequest method"
        )
        assert 'listUsers' in blueprint, (
            "MODULE_BLUEPRINT should capture listUsers method"
        )
        assert 'updateUser' in blueprint, (
            "MODULE_BLUEPRINT should capture updateUser method"
        )

    def test_php_type_hints_extraction(self, tmp_path: Path) -> None:
        """Test that PHP type hints are extracted into MODULE_BLUEPRINT.

        AC-7.3: Type hints (string, array, User, etc.) should be captured.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create PHP directory structure
        services = owner_dir / "src" / "Services"
        services.mkdir(parents=True)

        # Create PHP file with type hints
        (services / "OrderService.php").write_text("""
<?php

namespace App\\Services;

use App\\Models\\Order;
use App\\Models\\Customer;

class OrderService {
    private array $orders = [];
    private array $customers = [];

    public function createOrder(
        string $customerId,
        array $items,
        string $shippingAddress
    ): Order {
        $order = new Order($customerId, $items, $shippingAddress);
        $this->orders[] = $order;
        return $order;
    }

    public function getOrder(string $orderId): ?Order {
        foreach ($this->orders as $order) {
            if ($order->getId() === $orderId) {
                return $order;
            }
        }
        return null;
    }

    public function calculateTotal(Order $order): float {
        $total = 0.0;
        foreach ($order->getItems() as $item) {
            $total += $item->getPrice() * $item->getQuantity();
        }
        return $total;
    }
}
""".strip())

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
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )

        # Verify type hints are captured
        blueprint = blueprint_files[0].read_text()
        assert 'string' in blueprint, (
            "MODULE_BLUEPRINT should capture string type hint"
        )
        assert 'array' in blueprint, (
            "MODULE_BLUEPRINT should capture array type hint"
        )
        assert 'Order' in blueprint, (
            "MODULE_BLUEPRINT should capture Order class reference"
        )
        assert 'float' in blueprint, (
            "MODULE_BLUEPRINT should capture float type hint"
        )

    def test_php_filesystem_anchor_detection(self, tmp_path: Path) -> None:
        """Test that PHP uses filesystem anchor detection.

        AC-7.4: PHP repos should detect filesystem structure (composer.json, src/).
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create composer.json (typical PHP project anchor)
        (owner_dir / "composer.json").write_text("""{
    "name": "app/services",
    "type": "library",
    "autoload": {
        "psr-4": {
            "App\\\\": "src/"
        }
    },
    "require": {
        "php": "^8.0"
    }
}
""".strip())

        # Create PHP files in src/ directory
        services = owner_dir / "src" / "Services"
        services.mkdir(parents=True)

        (services / "UserService.php").write_text("""
<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }

    public function findUser(string $email): ?User {
        foreach ($this->users as $user) {
            if ($user->email === $email) {
                return $user;
            }
        }
        return null;
    }
}
""".strip())

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
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )

        # Verify filesystem anchor detection
        blueprint = blueprint_files[0].read_text()
        assert 'filesystem' in blueprint, (
            "MODULE_BLUEPRINT should reference filesystem anchor"
        )
