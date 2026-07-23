# -*- coding: utf-8 -*-
"""
Created the 01/06/2023

@author: Sebastien Weber
"""
import importlib
from pathlib import Path

from .element_factory import SeqEltFactory


here = Path(__file__).parent

def register_path(base_path: Path):
    # loading modules to register Sequencer Elements
    base_module = importlib.import_module('pymodaq_plugins_sequencer.utilities')
    for subpath in here.joinpath('elements').iterdir():
        importlib.import_module(f'elements.{subpath.stem}', base_module.__name__)