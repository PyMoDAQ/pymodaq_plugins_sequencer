import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_data import DataToExport
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils.logger import set_logger, get_module_name



if TYPE_CHECKING:
    from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase
    from pymodaq_plugins_sequencer.utilities.elements.choice import ChoiceElt

logger = set_logger(get_module_name(__file__))


class ChoiceModelBase(ParameterManager):
    params = []
    model_name: str = abstract_attribute()

    def __init__(self, parent_elt: 'ChoiceElt',):
        super().__init__(settings_name='choice_model_settings',
                         action_list=("search", "save", "update", "load"),
                         )
        self.parent_elt = parent_elt
        self.modules_manager: ModulesManager = parent_elt.modules_manager

    def updated_module_manager(self):
        """ called whenever the parent modules manager is updated

        to be reimplemented
        """
        pass

    @property
    def selected(self) -> list[str]:
        return self.modules_manager.selected_detectors_name

    def execute(self, dte: DataToExport):
        pass


def get_choice_models():
    """
    Register ChoiceModels in pymodaq models entrypoints

    Returns
    -------
    list: list of dict containing the name and python module of the found models

    Example
    -------
    model = [{'name': 'MyModel', 'class': DataModel}]
    """
    models_import = []
    discovered_models = list(get_entrypoints(group='pymodaq.models'))

    if len(discovered_models) > 0:
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        # by just importing the module, the models that may have a register decorator will be
                        # added to the factory

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')


