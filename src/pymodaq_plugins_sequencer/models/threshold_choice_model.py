from pymodaq_data import DataToExport
from pymodaq_plugins_sequencer.utilities.choice_models.factory import ChoiceModelFactory
from pymodaq_plugins_sequencer.utilities.choice_models.model import ChoiceModelBase


@ChoiceModelFactory.register_choice()
class ThresholdChoiceModel(ChoiceModelBase):
    model_name = 'threshold'

    params = [{'title': 'Threshold', 'name': 'threshold', 'type': 'float', 'value': 0},
              {'title': 'Direction', 'name': 'direction', 'type': 'list', 'value': 'Above',
               'limits': ['Above', 'Below']},
              {'title': 'DataName', 'name': 'data_name', 'type': 'itemselect',},]

    def process_dte(self, dte: DataToExport) -> bool:
        dwa = dte.get_data_from_name(self.settings['data_name'])
        if self.settings['direction'] == 'Above':
            return dwa.value() > self.settings['threshold']
        else:
            return dwa.value() < self.settings['threshold']
