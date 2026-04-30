# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

# Simple Python file with various import types

import os
import sys
from pathlib import Path

from requests import get, post

from mypackage import utils

# This is a relative import
from . import helpers
from .helpers import process_data

__all__ = ["process", "run"]
