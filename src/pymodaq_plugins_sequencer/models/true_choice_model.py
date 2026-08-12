from pymodaq_data import DataToExport
from pymodaq_plugins_sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq_plugins_sequencer.utilities.choice_models.model import ChoiceModelBase


@ChoiceModelFactory.register_choice()
class TrueChoiceModel(ChoiceModelBase):
    model_name = 'true'

    params = []

    def process_dte(self, dte: DataToExport) -> bool:
        return True
