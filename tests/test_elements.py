import random

import pytest
from qt_themes import set_theme

from serializall import SerializableFactory

from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory
from pymodaq_plugins_sequencer.utilities.mocks import DAQ_Move, DAQ_Viewer, DashBoard


seq_factory = SeqEltFactory()
ser_factory = SerializableFactory()


@pytest.fixture
def qtbot(qtbot):
    set_theme("monokai")
    return qtbot


@pytest.fixture
def mock_dashboard():
    return DashBoard(title='my_dashboard', detectors=[DAQ_Viewer('det0'),
                                                      DAQ_Viewer('det1')],
                     actuators=[DAQ_Move('act0'), DAQ_Move('act1'), DAQ_Move('act2')])


def test_get_elements():
    assert len(seq_factory.elements) > 0
    for elt in seq_factory.elements:
        assert isinstance(elt, str)


def test_all_element_serialized_registered(qtbot):
    for elt_name in seq_factory.elements:
        assert seq_factory.get_seq_elt(elt_name) in ser_factory.get_serializables()


@pytest.mark.parametrize('elt_name', seq_factory.elements)
def test_widget_creation(qtbot, elt_name, mock_dashboard):
    id = random.randint(0, 100)
    element = seq_factory.get_seq_elt(elt_name)(id, dashboard=mock_dashboard)
    widget = element.create_widget()
    qtbot.addWidget(widget)
    widget.show()


class TestElements:

    @pytest.mark.parametrize('elt_name', seq_factory.elements)
    def test_serialization_deserialization(self, qtbot, elt_name, mock_dashboard):

        id = random.randint(0, 100)
        go_to = random.randint(0, 100)
        element = seq_factory.get_seq_elt(elt_name)(id, dashboard=mock_dashboard,)
        element.go_to = go_to

        assert ser_factory.get_apply_deserializer(
            ser_factory.get_apply_serializer(element), only_object=True) == element

        serialized = ser_factory.get_apply_serializer(element)
        obj, remaining_bytes = ser_factory.get_apply_deserializer(serialized, False)
        assert obj == element
        assert remaining_bytes == b''


