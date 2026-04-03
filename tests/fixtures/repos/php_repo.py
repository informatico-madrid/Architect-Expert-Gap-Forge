# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""PHP repository fixture for testing PHP processing."""

PHP_CODE = """<?php

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
"""

PHP_CONTROLLER = """<?php

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
            default:
                return null;
        }
    }
}
"""

PHP_MODEL = """<?php

namespace App\\Models;

class User {
    public string $name;
    public string $email;

    public function __construct(string $name, string $email) {
        $this->name = $name;
        $this->email = $email;
    }
}
"""

PHP_MODEL_ORDER = """<?php

namespace App\\Models;

class Order {
    public string $id;
    public array $items;

    public function __construct(string $id, array $items) {
        $this->id = $id;
        $this->items = $items;
    }
}
"""

COMPOSER_JSON = """{
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
"""
