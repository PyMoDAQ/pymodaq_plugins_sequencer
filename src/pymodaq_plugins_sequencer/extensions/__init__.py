# -*- coding: utf-8 -*-
"""
Created the 01/06/2023

@author: Sebastien Weber
"""
from pymodaq_plugins_sequencer.utilities.choice_models.model import get_choice_models
from pymodaq_plugins_sequencer.utilities.element_factory import register_elements


elts = register_elements()
get_choice_models()  # register choice models
pass
