import random

import pytest
from qt_themes import set_theme

from serializall import SerializableFactory

from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq_plugins_sequencer.utilities.mocks import DAQ_Move, DAQ_Viewer, DashBoard


seq_factory = SeqEltFactory()
ser_factory = SerializableFactory()

ROOT_INDEX = -1


@pytest.fixture
def qtbot(qtbot):
    set_theme("monokai")
    return qtbot


def create_tree() -> tuple[SeqEltBase, list[int], list[str]]:
    """create a tree of SeqEltBase with two levels depth

    First layer has 5 children with index from 0 to 5
    Each child as one child
    """
    elt = SeqEltFactory.get_seq_elt('wait')(ROOT_INDEX)
    elt.children_allowed = True
    ind = 0
    ids = []
    elts_repr = []
    for _ in range(0, 5):
        ind += 1
        child = SeqEltFactory.get_seq_elt('wait')(ind)
        ids.append(child.id)
        elts_repr.append(str(child))
        child.children_allowed = True
        elt.append_child(child)

        for _ in range(0, 5):
            ind += 1
            grandchild = SeqEltFactory.get_seq_elt('wait')(ind)
            ids.append(grandchild.id)
            elts_repr.append(str(grandchild))
            grandchild.children_allowed = True
            child.append_child(grandchild)

    return elt, ids, elts_repr


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


def test_get_elt_by_id_and_get_root():

    root, _, _ = create_tree()

    elt_7_id = 7
    elt_7 = root.get_elt_from_id(elt_7_id)

    elt_4_id = 4
    assert elt_7.id == elt_7_id
    assert elt_7.get_root_elt() == root

    elt_4 = elt_7.get_elt_from_id(elt_4_id)
    assert elt_4.id == elt_4_id
    assert elt_4.get_root_elt() == root

    assert elt_4.get_elt_from_id(-2) is None


def test_get_ids():

    root, all_ids, all_reprs = create_tree()
    ids = root.get_ids()

    for id in ids:
        assert id in all_ids
    for id in all_ids:
        assert id in ids

    elts_repr = root.get_elts_as_str()

    for _repr in elts_repr:
        assert _repr in all_reprs
    for _repr in all_reprs:
        assert _repr in elts_repr