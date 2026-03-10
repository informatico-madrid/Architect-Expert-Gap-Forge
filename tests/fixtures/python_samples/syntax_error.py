# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

# ruff: noqa: E999
# File with syntax error for testing parse error handling

import os

def broken_function(
    x: int,
    y: int
    # Missing closing parenthesis
    return x + y

# This should trigger a parse error
