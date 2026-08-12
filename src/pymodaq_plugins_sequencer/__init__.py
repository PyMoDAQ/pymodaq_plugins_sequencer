
from .utils import Config
from pymodaq_utils.utils import get_version, PackageNotFoundError
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_plugins_sequencer.utilities.choice_models.model import get_choice_models
from pymodaq_plugins_sequencer.utilities.element_factory import register_elements
from pymodaq_plugins_sequencer.utilities.choice_models.factory import register_choice_models

config = Config()
try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'


elts = register_elements()
get_choice_models()  # register choice models
pass

