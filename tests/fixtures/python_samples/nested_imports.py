# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

# File with nested imports and various import patterns

from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
import ast
import json

# Nested relative imports
from .subpackage import module_a
from .subpackage.module_b import ClassB
from .. import parent_helper

# External imports
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Star import (should be handled)
from collections import *  # noqa

__version__ = "1.0.0"
