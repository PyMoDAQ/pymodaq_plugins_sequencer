from typing import TYPE_CHECKING, Any
from qtpy import QtCore

from qtpy.QtStateMachine import (QState, QStateMachine, QFinalState, QHistoryState,
                                 QAbstractTransition, QSignalTransition)  # noqa


from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq_plugins_sequencer.utilities.element_factory import SeqEltBase


logger = set_logger(get_module_name(__file__))



class MyQFinalState(QFinalState):
    def onEntry(self, event, /):
        logger.debug(f'Entering  {self.objectName()}')

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')


class CompositeState(QState):
    def __init__(self, elt: 'SeqEltBase', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.execute_state: QState | None = None
        self.done_state: MyQFinalState | None = None
        self.children_state: QState | None = None
        self._external_transitions = []

        self._elt = elt

        self.setup_states()

        self.execute_state.entered.connect(elt.execute)
        self.execute_state.addTransition(elt.children_signal, self.children_state)

        self.addTransition(elt.done_signal, self.done_state)  # apply to all substates

    def onEntry(self, event, /):
        logger.debug(f'Entering {self.objectName()}')

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')

    def setup_states(self):
        self.setObjectName(f'State of the elt: {self._elt}')

        self.execute_state = QState(self)
        self.execute_state.setObjectName(f'ExecuteState of the elt: {self._elt}')
        self.done_state = MyQFinalState(self)
        self.done_state.setObjectName(f'FinalState of the elt: {self._elt}')
        self.children_state = QState(self)
        self.children_state.setObjectName(f'ChildrenState of the elt: {self._elt}')

        self.setInitialState(self.execute_state)

    def add_external_transition(self, signal: QtCore.Signal, target: QState):
        self._external_transitions.append(self.addTransition(signal, target))

    @property
    def external_transitions(self) -> list[QAbstractTransition]:
        return self._external_transitions

    def clear_state_and_transitions(self):
        for trans in list(self.external_transitions):
            self.removeTransition(trans)
        self.setParent(None)


class ValueTransition(QSignalTransition):
    def __init__(self, signal: QtCore.Signal, value: Any, target_state: QState):
        super().__init__(signal)
        self.value = value
        self.setTargetState(target_state)

    def eventTest(self, event: QStateMachine.SignalEvent) -> bool:
        if not super().eventTest(event):
            return False

        arguments = event.arguments()
        if arguments:
            value = arguments[0]
            return value == self.value
        return False
