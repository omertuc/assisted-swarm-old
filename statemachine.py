from collections import OrderedDict
import time
from itertools import takewhile


class RetryingStateMachine:
    """
    A statemachine that's designed to be mostly used for running a bunch of linear states in a row.
    Retries a state forever when the step raises an exception (this is helpful for trying
    to deal with intermittent service issues / downtime).

    This statemachine is used to model the behavior of the entire swarm and for single
    swarm agents as well.

    The states in the state machine are given as a dictionary with state names as keys
    and state functions as values. The state functions receive the "next state" as a parameter.
    This parameter is just a recommendation (and it's always just equal to the next entry in the
    states ordered dict), but the true next state is determined by the state itself
    via its return value. This allows states to mostly not care which states come after them (by just
    returning the recommended value), but still allows them to break the linearity if they choose to do
    so, by returning a state of their choice.
    """
    def __init__(self, initial_state: str, terminal_state: str, states: OrderedDict, name: str, logging):
        self.state = initial_state
        self.terminal_state = terminal_state
        self.states = states
        self.logging = logging
        self.name = name
        self.exponential_backoff = 0

    def start(self):
        while self.state != self.terminal_state:
            state_successful = self.statemachine()

            if not state_successful:
                # Retry again soon
                self.exponential_backoff += 1
                # time.sleep(min(120, 2 ** self.exponential_backoff))
                time.sleep(5)
            else:
                self.exponential_backoff = 0

        self.logging.info(f'Statemachine "{self.name}" complete')

    def get_next_state(self):
        keys_iter = iter(self.states.keys())
        for _ in takewhile(lambda k: k != self.state, keys_iter):
            pass
        try:
            return next(keys_iter)
        except StopIteration:
            return None

    def statemachine(self):
        # States typically don't care what's the next state, so we can just recommend the next one in the list
        next_state = self.get_next_state()
        self.logging.info(f'State machine "{self.name}" running state: "{self.state}"')

        try:
            true_next_state = self.states[self.state](next_state)
        except Exception as e:
            self.logging.exception(e)
            true_next_state = self.state

        if true_next_state != self.state:
            self.state = true_next_state
            return True

        return False


