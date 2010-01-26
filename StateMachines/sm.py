
"""This module implements state machines for event-driven programming.

This module provides the class `StateMachine` and the class `Event`.
It also provides the classes `State` and `Transition`, although these are not normally used directly by applications.
A companion module, `decorator`, provides two decorators, ``@state`` and ``@transition`` that simplify the
definition of state machines.

State machines are a control structure particularly suited for *event-driven programming*,
i.e. when the program's behavior depends on events arriving asynchronously as is the case
with, e.g., user interfaces.

A state machine contains a set of *states*. 
At any one time, only one state is *current*. If the current state is ``A``, the machine is said to be in state ``A``.
One state is the *initial state*, i.e. the current state when the machine is started.

Each state may have one or more *transitions* that describe how the machine reacts to events when it is in this state.
Each transition specifies the events it recognizes and a *destination state*.
When an event is processed by the state machine, it checks each transition of its current state.
The first transition that matches the event is *fired*, and its destination state becomes the current state.
If no transition matches the event, the event is ignored.

In this implementation of state machines, events that match a transition are specified by:

    - an *event type*, which is usually a class object, e.g., ``ButtonPress`` for an event representing the user pressing the button of the mouse;
    - optional extra arguments relative to the state of the event, e.g., ``'Button1'`` to specify which button of the mouse should be pressed;
    - an optional *guard*, which is a predicate evaluated on the event.

States and transitions can have *actions* attached to them.
States can have an *enter action*, called when the state becomes current,
and a *leave action*, called when the state ceases to be current.
Transitions have a *transition action* that is called when the transition is fired.
In summary, if the current state is ``A`` and the transition being fired has destination state ``B``,
the following actions are called in that order:

    - the leave action of the current state ``A``;
    - the transition action;
    - the enter action of the destination state ``B``, which is now the new current state.

State machines are traditionally represented by a graphical notation:
states are represented by circles and transitions by directed arrows going from their starting state to their destination state.
The initial state is usually marked with an L-shaped arrow or a thicker border.
Transitions are typically labelled by an expression of the form 

    ``Event(args) [& guard] [/ action]``

that specifies the event type, additional arguments, optinal guard, and optional action.

    [Should include a simple example here with a drawing]

:group Exceptions: StateUnknown, StateAlreadyExists, TransitionBadAction, TransitionBadGuard

"""
__docformat__ = "restructuredtext en"

__all__ = ['StateUnknown', 'StateAlreadyExists', 'TransitionBadAction', 'TransitionBadGuard',
    'Event', 'State', 'Transition', 'StateMachine']


# -------- Error classes --------

class StateUnknown(Exception):
    """Signals that a state specified by name or by id is unknown."""
    
class StateAlreadyExists(Exception):
    """Signals that a state by this name already exists."""

class TransitionBadAction(Exception):
    """Signals that the action specified for a transition is not callable."""

class TransitionBadGuard(Exception):
    """Signals that the guard specified for a transition is not callable."""

# -------- Event class --------

class Event(object):
    """Base class for events processed by state machines (see `StateMachine.process_event`).
    
    Applications should define subclasses of `Event` to implement application-specific types of events.
    
    In fact, state machines only require events to have a `type` field and a `match` method so in fact
    events do not absolutely need to be instances of `Event`.
    
    :ivar type: The type of the event. This field is compared with the type of event expected by each transition.
    """
    def __init__(self, type):
        """Initialize an event. 
        
        :param type: The type of the event. Can be any object but normally subclasses use the event class object itself, e.g. ``ButtonPress``.  NOTE:  This type is not currently used -JRE 2010-01-22
        """
        super(Event, self).__init__()
        self.type = type
    
    def match(self, transition):
        """Return True if this event matches the transition.
        
        :param transition: The transition being tested.
        :return: True if the event matches the transition's ``args`` and ``kwargs`` fields.
        
        This method is called by `StateMachine.process_event` once the event type matches that of the transition.
        Subclasses should redefine this method to properly interpret the transition's ``args`` and ``kwargs`` fields
        and refine the match, e.g. to distinguish among several buttons for a ``ButtonPress`` event.
        By default, i.e. unless it is redefined, match always returns True.
        """
        return True

# -------- State and Transition classes --------


class State(object):
    """A state of a state machine.
    
    This class should not be directly instantiated nor its methods called directly by the application.
    States are created either with the `StateMachine.add_state` method or the ``@state`` decorator in module `decorator`.
    """
    
    def __init__(self, name, enter=None, leave=None):
        """Initialize a state.
        
        :param name: The name of the state, which can be used in the ``to`` keyword of transitions.
        :kwarg enter: The enter action (must be callable if not None).
        :kwarg leave: The leave action (must be callable if not None).
        """
        super(State, self).__init__()
        self.name = name
        self.enter = enter
        self.leave = leave
        self.transitions = []
        self.original = self        # used by the @state decorator pattern
        self.state_machine = None   # the state machine this state is in
    
    def _add_transition(self, event_type, *args, **kwargs):
        """Add a transition from this state (private).
        
        :param event_type: The type of the event being matched.
        :param args: Additional positional arguments for matching the event.
        :param kwargs: Keyword arguments for matching the event.
        
        :return: The newly created transition
        
        Applications should either use `StateMachine.add_transition` or the ``@transition`` decorator to create transitions.
        """
        transition = Transition(event_type, *args, **kwargs)
        transition.state = self
        self.transitions.append(transition)
        return transition
    
    def enter(self):
        """Call the state's enter action, if any."""
        if self.enter:
            self.enter()
    
    def leave(self):
        """Call the state's leave action, if any."""
        if self.leave:
            self.leave()
    
    def get_transition(self, event):
        """Return the first transition that matches `event` and whose guard (if any) evaluates to True, None otherwise.
        
        :param event: The event to be matched.
        
        For each transition, first the event type is tested, if it matches then the `Event.match` method is called,
        if it returns True and the transition has a guard, then the guard is evaluated.
        """
        for transition in self.transitions:
            if __debug__:
                print 'trying ', transition
            if isinstance(event, transition.event_type) and event.match(transition):
                if callable(transition.guard):
                    if transition.guard(event):
                        return transition
                    continue
                return transition
        return None
    
    def __str__(self):
        return "state "+self.name
    
    def __eq__(self, other):
        """Equality test for states.
        
        States are considered equal if they have the same 'original' state.
        By default, a state is its own 'original' state, but states created by the ``@state`` decorator 
        have a different 'original' state (see module `decorator`).
        """
        if not other:
            return False
        return id(self.original) == id(other.original)


class Transition(object):
    """A transition of a state machine.
    
    This class should not be instantiated nor its methods called directly by the application.
    Transitions are created either with the `StateMachine.add_transition` or method using the ``@transition`` decorator from module `decorator`.
    
    The instance variables listed below can all be freely read by the application.
    Except for `state`, they can also be freely written by the application.
    
    :IVariables:
        - `event_type`: the type of event matched by this transition.
        - `args`: a tuple of extra arguments specifying the events matched by this transition.
        - `kwargs`: a dictionary of extra keyword arguments specifying the events matched by this transition.
        - `guard`: the guard for this transition (``None`` if there is no guard).
        - `state`: the source state of this transition (must not be changed).
        - `to_state`: the destination state of this transition (if ``None``, the destination state is the same as the source state, and the enter/leave actions are *not* called).
        - `action`: the action for this transition (``None`` if there is no action).

    """
    def __init__(self, event_type, *args, **kwargs):
        """Initialize a transition.
        
        :Parameters:
            - `event_type`: The type of the events to be matched.
            - `args`: Additional positional arguments for matching events.
            - `kwargs`: Keyword arguments for matching events and for specifying the transition (see below).
        
        :Keywords:
            - `guard`: Optional keyword argument to specify a callable to be called to filter events.
            - `to`: Optional keyword argument to specify the name of the destination state (if not specified, the transition loops on its state).
            - `action`: Optional keyword argument to specify a callable invoked when the transition is fired.
        
        :Exceptions:
            - `StateUnknown`: The destination state does not exist or is not a state.
            - `TransitionBadAction`: The transition's action is not callable.
            - `TransitionBadGuard`: The transition's guard is not callable.
        """
        super(Transition, self).__init__()
        self.event_type = event_type
        self.args = args
        self.kwargs = kwargs
        self.state = None
        
        # extract action, guard and destination state and remove them from kwargs
        self.action = kwargs.get('action')
        self.guard = kwargs.get('guard')
        self.to_state = kwargs.get('to')
        for attr in ('action', 'guard', 'to'):
            try:
                del kwargs[attr]
            except Exception:
                pass
        
        # sanity checks
        if self.to_state:
            if not isinstance(self.to_state, State):
                raise StateUnknown, "The destination state does not exist or is not a state."
        if self.action:
            if not callable(self.action):
                raise TransitionBadAction, "The transition's action is not callable."
        if self.guard:
            if not callable(self.guard):
                raise TransitionBadGuard, "The transition's guard is not callable."
    
    def __str__(self):
        res = 'transition on ' + self.event_type.__name__
        if len(self.args) > 0:
            res += ' with ' + ', '.join(self.args)
        if self.guard:
            res += ' with guard'
        if self.to_state:
            res += ' to ' + str(self.to_state)
        else:
            res += ' to itself'
        return res

# -------- the StateMachine class --------

class StateMachine(object):
    """A basic state machine (see `decorator.statemachine` for the class that supports the ``@state`` and ``@transition`` decorators).
    
    The instance variables listed below can all be read and written by the application.
    
    :IVariables:
        - `start_state`: The initial state.
        - `current_state`: The current state.
        - `active`: ``True`` if the machine processes events (use `suspend` and `resume` to change the active state).
        - `call_actions_on_reset`: if ``True``, resetting the state machine calls the current state's leave action and the starting state's enter action.
        - `call_actions_on_suspend`: if ``True``, suspending the state machine calls the current state's leave action.
        - `call_actions_on_resume`: if ``True``, resuming the state machine calls the current state's enter action.
    
    :group Editing: add_state, add_transition
    :group Event processing: process_event, resume, suspend, reset
    :group Iterators: all_states, all_transitions, transitions_from, transitions_to, transitions_between, transitions
    """
    
    def __init__(self, active = True, call_actions = False):
        """Initialize a new state machine.
        
        :Parameters:
            - `active`: specifies whether the state machine is immediately processing events.
            - `call_actions`: specifies whether to call enter/leave actions when starting/suspending/resuming/resetting the state machine.
        
        After the initialization, the application can set three booleans to control how actions are called:
        In all cases, the field 'active' of the state machine is set to False while the actions are being called,
        giving them a way to distinguish these calls from "normal" calls.
        Initially, all three booleans have the same value as the 'call_actions' parameter.
        """
        super(StateMachine, self).__init__()
        
        self._sm_states = []
        self._sm_current_state = None
        self._sm_start_state = None
        
        self._sm_active = active;
        self._sm_call_actions_from_reset = call_actions
        self._sm_call_actions_from_suspend = call_actions
        self._sm_call_actions_from_resume = call_actions
    
    # ---- iterators to list the states of this state machine and the transitions of a state
    
    def all_states(self):
        """Return an iterator over the states of this state machine."""
        return iter(self._sm_states)
    
    def all_transitions(self):
        """Return an iterator over all the transitions of this state machine."""
        for state in self.all_states():
            for transition in state.transitions:
                yield transition
    
    def transitions_from(self, src_state):
        """Return an iterator over the transitions from ``src_state``.
        
        :param src_state: The source state (a string or a state object).
        :except StateNotFound: The source state was not found in this state machine.
        """
        src_state = self.find_state(src_state)
        if not src_state:
            raise StateNotFound
        return iter(src_state.transitions)
    
    def transitions_to(self, dest_state):
        """Return an iterator over the transitions to ``dest_state``.
        
        :param dest_state: The destination state (a string or a state object).
        :except StateNotFound: The destination state was not found in this state machine.
        """ 
        dest_state = self.find_state(dest_state)
        if not dest_state:
            raise StateNotFound
        for src_state in self.all_states():
            for transition in src_state.transitions:
                if transition.to_state == dest_state or (not transition.to_state and src_state == dest_state):
                    yield transition

    def transitions_between(self, src_state, dest_state):
        """Return an iterator over the transitions from ``src_state`` to ``dest_state``.
        
        :param src_state: The source state (a string or a state object).
        :param dest_state: The destination state (a string or a state object).
        :except StateNotFound: The source or destination state was not found in this state machine.
        """
        src_state = self.find_state(src_state)
        if not src_state:
            raise StateNotFound
        
        dest_state = self.find_state(dest_state)
        if not dest_state:
            raise StateNotFound
        
        for transition in src_state.transitions:
            if transition.to_state == dest_state or (not transition.to_state and src_state == dest_state):
                yield transition
    
    def transitions(self, src=None, dest=None):
        """Return an iterator over the transitions of the state machine.
        
        This iterator triggers one of the other transition iterators according to the values of `src` and `dest`:
        
            - If `src` and `dest` are ``None`` or not specified, list all transitions;
            - If `dest` is ``None`` or not specified, list transitions that leave `src`;
            - If `src` is ``None`` or not specified, list transitions that arrive at `dest`;
            - If both `src` and `dest` are not ``None``, list transitions that go from `src` to `dest`.
        
        :param src: The source state (a string or a state object).
        :param dest: The destination state (a string or a state object).
        :except StateNotFound: The source or destination state was not found in this state machine.
        """
        if src and dest:
            return self.transitions_between(src, dest)
        if src:
            return self.transitions_from(dest)
        if dest:
            return self.transitions_to(src)
        return self._sm_all_transitions
    
    
    # ---- find a state by name
    
    def find_state(self, name_or_string):
        """Return the state object specified by its identifier or its string name.
        
        :param name_or_string: Either a state object or the string name of a state.
        :return: The state if it was found, ``None`` otherwise.
        """
        if isinstance(name_or_string, State):
            for s in self.all_states():
                if s == name_or_string:
                    return s
        else:
            for s in self.all_states():
                if s.name == name_or_string:
                    return s
        return None
    
    # ---- functions to dynamically add states and transitions.
    #      (Most state machines will use the @state and @transition decorators instead)
    
    def add_state(self, name, enter=None, leave=None):
        """Create a new state and add it to this state machine.
        
        :param name: The name of the state (a string).
        :keyword enter: The enter action, if any (must be callable).
        :keyword leave: The leave action, if any (must be callable).
        :except StateAlreadyExists: A state with the same name already exists.
        :return: The newly created state.
        """
        # check that no state has this name already
        if self.find_state(name):
            raise StateAlreadyExists, "This state is already defined"
        
        # create a State object
        state = State(name, enter=enter, leave=leave)
        state.state_machine = self
        
        # assign it to self.start_state if it's the first state
        if not self._sm_start_state:
            self._sm_start_state = state
            self._sm_current_state = state
        
        # add to self.states
        self._sm_states.append(state)
        
        # return the new state
        return state
    
    def add_transition(self, state, event_type, *args, **kwargs):
        """Create a new transition and add it to this state machine.
        
        :Parameters:
            - `state`: The source state of the transition.
            - `event_type`: The type of the events to be matched.
            - `args`: Additional positional arguments for matching events.
            - `kwargs`: Keyword arguments for matching events and for specifying the transition (see below).
        
        :Keywords:
            - `guard`: Optional keyword argument to specify a callable to be called to filter events.
            - `to`: Optional keyword argument to specify the name of the destination state (if not specified, the transition loops on its state).
            - `action`: Optional keyword argument to specify a callable invoked when the transition is fired.
        
        :Exceptions:
            - `StateUnknown`: The destination state does not exist or is not a state.
            - `TransitionBadAction`: The transition's action is not callable.
            - `TransitionBadGuard`: The transition's guard is not callable.
        
        :return: The newly created transition.
        """
        # check that the from state exists
        from_state = self.find_state(state)
        if not from_state:
            raise StateUnknown, "Source state unknown:"+str(from_state)
        
        # check that the to state exists if it is specified
        to_state = kwargs.get('to')
        if to_state:
            to_state = self.find_state(to_state)
            if not to_state:
                raise StateUnknown, "Destination state unknown"+str(to_state)
            kwargs['to'] = to_state
        
        # add the transition to the from state
        return from_state._add_transition(event_type, *args, **kwargs)
    
    # ---- event processing
    
    def reset(self):
        """Reset the machine to the initial state.
        
        If the state machine is active, the `call_actions_on_reset` variable is ``True`` and the current state is not the initial state,
        then the current state's leave action and the initial state's enter action, if any, are called.
        During these calls, the `active` variable is set to ``False`` so that the actions can distinguish these calls from a 'normal' call.
        """
        if self._sm_call_actions_on_reset and self._sm_active \
           and self._sm_current_state != self._sm_start_state:
            # setting active to False during the reset allows the enter/leave functions to know they are being called from reset (or suspend/resume)
            self._sm_active = False
            self._sm_current_state.leave()
            self._sm_current_state = self._sm_start_state
            self._sm_current_state.enter()
            self._sm_active = True
        else:
            self._sm_current_state = self._sm_start_state
    
    def suspend(self):
        """Stop processing events.
        
        If the state machine is active and the `call_actions_on_suspend` variable is ``True``,
        then the current state's leave action, if any, is called.
        During that call, the `active` variable is set to ``False`` so that the action can distinguish this call from a 'normal' call.
        """
        if self._sm_call_actions_on_suspend and not self._sm_active:
            self._sm_active = False
            # setting active to false allows the leave function to distinguish between a regular call and a call from suspend or reset
            self._sm_current_state.leave()
        self._sm_active = False
    
    def resume(self):
        """Start processing events.
        
        If the state machine is not active and the `call_actions_on_resume` variable is ``True``,
        then the current state's enter action, if any, is called.
        During that call, the `active` variable is set to ``False`` so that the action can distinguish this call from a 'normal' call.
        """
        if self._sm_call_actions_on_resume and not self._sm_active:
            self._sm_current_state.enter()
            # setting active to true after the call allows the enter function to distinguish between a regular call and a call from resume or reset
        self._sm_active = True
    
    def process_event(self, event):
        """Process an event. 
        
        :param event: The event to process.
        :return: ``True`` if the event triggered a transition, ``False`` otherwise.
        """
        
        if not self._sm_active:
            return None
        
        if __debug__:
            print
            print 'Processing ', event
        
        # call the current state's 'action' function to retrieve the transition associated with this event
        # This 'action' function is actually the 'wrapper' function of the transition class.
        transition = self._sm_current_state.get_transition(event)
        
        # no transition: ignore event
        if not transition:
            if __debug__:
                print 'No transition for this event: ignored'
            return False
        
        # fire the transition: call the current state's leave action, the transition's action, and the destination state's enter action
        if transition.to_state:
            if self._sm_current_state.leave:
                self._sm_current_state.leave()
            if callable(transition.action):
                transition.action(event)
            self._sm_current_state = transition.to_state
            if self._sm_current_state.enter:
                self._sm_current_state.enter()
        else:
            # if the destination state is not specified, simply call the transition's action
            if callable(transition.action):
                transition.action(event)
        
        if __debug__:
            print '-> ', self._sm_current_state
        return True
