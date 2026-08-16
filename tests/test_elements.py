import random
from typing import TYPE_CHECKING

import pytest
from qt_themes import set_theme

from serializall import SerializableFactory

from pymodaq_plugins_sequencer import get_choice_models
from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq_plugins_sequencer.utilities.mocks import DAQ_Move, DAQ_Viewer, DashBoard
from pymodaq_plugins_sequencer.utilities.choice_models.factory import ChoiceModelFactory

if TYPE_CHECKING:
    from pymodaq_plugins_sequencer.utilities.elements.choice import ChoiceElt


get_choice_models()
seq_factory = SeqEltFactory()
ser_factory = SerializableFactory()
choice_factory = ChoiceModelFactory()

ROOT_INDEX = -1


@pytest.fixture
def qtbot(qtbot):
    set_theme("monokai")
    return qtbot


def create_tree(n_element=5) -> tuple[SeqEltBase, list[int], list[SeqEltBase]]:
    """create a tree of SeqEltBase with two levels depth

    First layer has 5 children with index from 0 to 5
    Each child as one child
    """
    elt = SeqEltFactory.get_seq_elt('wait')(ROOT_INDEX)
    elt.children_allowed = True
    ind = 0
    ids = []
    elts = []
    for _ in range(0, n_element):
        ind += 1
        child = SeqEltFactory.get_seq_elt('wait')(ind)
        ids.append(child.id)
        elts.append(child)
        child.children_allowed = True
        elt.append_child(child)

        for _ in range(0, n_element):
            ind += 1
            grandchild = SeqEltFactory.get_seq_elt('wait')(ind)
            ids.append(grandchild.id)
            elts.append(grandchild)
            grandchild.children_allowed = True
            child.append_child(grandchild)

    return elt, ids, elts


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


class TestElements:

    @pytest.mark.parametrize('elt_name', seq_factory.elements)
    def test_widget_creation(self, qtbot, elt_name):
        id = random.randint(0, 100)
        element = seq_factory.get_seq_elt(elt_name)(id)
        widget = element.create_widget()
        qtbot.addWidget(widget)
        widget.show()

    @pytest.mark.parametrize('elt_name', seq_factory.elements)
    def test_serialization_deserialization(self, qtbot, elt_name):

        id = random.randint(0, 100)
        element = seq_factory.get_seq_elt(elt_name)(id, )

        assert ser_factory.get_apply_deserializer(
            ser_factory.get_apply_serializer(element), only_object=True) == element

        serialized = ser_factory.get_apply_serializer(element)
        obj, remaining_bytes = ser_factory.get_apply_deserializer(serialized, False)
        assert obj == element
        assert remaining_bytes == b''

    def test_tree_serialization_deserialization(self, qtbot):

        tree_elt, ids, elts = create_tree(5)

        assert ser_factory.get_apply_deserializer(
            ser_factory.get_apply_serializer(tree_elt), only_object=True) == tree_elt

        serialized = ser_factory.get_apply_serializer(tree_elt)
        obj, remaining_bytes = ser_factory.get_apply_deserializer(serialized, False)
        assert obj == tree_elt
        assert remaining_bytes == b''

    @pytest.mark.parametrize('elt_name', seq_factory.elements)
    def test_todict_fromdict(self, qtbot, elt_name, mock_dashboard):

        id = random.randint(0, 100)
        element = seq_factory.get_seq_elt(elt_name)(id,)

        dict_config = element.to_dict()
        element_back = element.from_dict(dict_config)
        assert element_back == element

    def test_tree_todict_fromdict(self, qtbot):

        tree_elt, ids, elts = create_tree(5)

        assert tree_elt.from_dict(tree_elt.to_dict()) == tree_elt


    def test_get_elt_by_id_and_get_root(self):

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


    def test_get_ids(self):

        root, all_ids, _ = create_tree()
        ids = root.get_ids()

        for id in ids:
            assert id in all_ids
        for id in all_ids:
            assert id in ids


    def test_get_elts(self):

        root, all_ids, all_elts = create_tree()
        elts = root.get_elts()

        for _elt in elts:
            assert _elt in all_elts
        for _elt in all_elts:
            assert _elt in elts


    def compare_get_ids_get_elts(self):
        root, all_ids, all_elts = create_tree()
        for (id, elt) in zip(all_ids, all_elts):
            assert id == elt.id


class TestChoiceElementModels():

    @pytest.mark.parametrize('choice_model', choice_factory.models)
    def test_models(self, qtbot, choice_model):

        elt: ChoiceElt = seq_factory.get_seq_elt('choice')(0)
        elt.choice_model = choice_model

    @pytest.mark.parametrize('choice_model', choice_factory.models)
    def test_from_to_dict(self, qtbot, choice_model):

        elt: ChoiceElt = seq_factory.get_seq_elt('choice')(0)
        elt.choice_model = choice_model


        assert ser_factory.get_apply_deserializer(
            ser_factory.get_apply_serializer(elt), only_object=True) == elt


        assert elt.from_dict(elt.to_dict()) == elt
