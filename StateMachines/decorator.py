"""This module extends regular state machines (module `sm`) with decorators to facilitate the declaration of state machines.

The module `sm` requires state machines to be created programatically. 
Because actions can be attached to states and events, the programmer must create separate functions for each action
and pass them as parameters to the methods ``add_state`` and ``add_transition``.
This results in fairly hairy code and is prone to errors.

This module provides a class, `statemachine`, and two decorators, `state` and `transition`, to facilitate the declaration of state machines.

The syntax for declaring a state machine is as follows:

.. python::

    class MyStateMachine(statemachine):
        def __init__(self):
            super(MyStateMachine, self).__init__()
    
        # Declaring a state
        @state
        def SomeState(self)
            # optional function called when entering the state:
            def enter():
                ... body of enter action ...
    
            # optional function called when leaving the state:
            def leave():
                ... body of leave action ...
    
            # a simple transition
            @transition(Press, 'Button1', to=self.AnotherState)
            def action(event):
                ... body of transition action ...
    
            # a transition with a guard:
            @transition(Button1, guard=lambda event: ...expression that tests the event..., to=self.AnotherState)
            def action(event):
                ... body of transition action ...
    
            ... more transitions ...
        
        # another state
        @state
        def AnotherState(self)
            ...

Each state is a method decorated with ``@state`` that contains a set of declarations:

    - optional ``enter`` and ``leave`` functions representing the enter and leave actions of this state;
    - transitions that leave this state, declared with the ``@transition`` decorator;
    - optional declarations, e.g. of variables and functions that can be used by the enter and leave actions and/or by the transitions.

Note that because of Python's scoping rules, the bodies of the functions declared in a state have access to the
local declarations of the state as well as to the enclosing state machine (through ``self``).

Each transition is a function that must be called ``action`` that takes an event as parameter,
and that is decorated with the ``@transition`` decorator. This decorator takes one or more arguments:

    - the first argument must be the event type for this transition (see `sm.Event`);
    - subsequent positional arguments are passed to the `sm.Event.match` method to further filter the event;
    - an optinal guard is specified by the ``guard`` keyword argument. It must be a callable that takes the event as argument;
    - the destination state is specified by the ``to`` keyword argument;

Note that the body of a transition has direct access to the local declarations of its enclosing state
as well as to the enclosing state machine (using ``self``).

The advantage of this approach is that the bodies of the actions are speficied at the location where the states and transitions are declared.
Except for the scoping rules, the result of instantiating a state machine in this way is exactly the same as using 
the `sm.StateMachine.add_state` and `sm.StateMachine.add_transition` methods. 

Moreover, a state machine declared using the ``@state`` and ``@transition`` decorators can have
states and transitions added to it with the `sm.StateMachine.add_state` and `sm.StateMachine.add_transition` methods. 

:group Decorators: state, transition
:group Exceptions: TransitionDeclarationError, TransitionBadActionName
"""

__docformat__ = "restructuredtext en"

import sys, copy, inspect

from sm import State, Transition, StateMachine

__all__ = ['TransitionDeclarationError', 'TransitionBadActionName', 'state', 'transition', 'statemachine']

# -------- utilities --------

# Functions to find out the locals of a function.
# Calls the function and uses tracing tools to find out.
# NOTE : this is both dangerous (the function could have side effects)
#   and expensive: tracing is costly.
#
# Copied from http://wiki.python.org/moin/PythonDecoratorLibrary
# and modified by [mbl]:
#   - use depth of original call to test that we're getting info from the right 'return'
#   - use depth to avoid tracing nested calls (more efficient)
#   - handle exceptions

def _getsomelocals(function, keys, *args):
    """Execute a function and return its locals whose names are in keys (private).
    
    :Parameters:
        - `function`: The function from which to extract the locals.
        - `keys`: A tuple of names of locals to extract
        - `args`: Arguments to be passed to `function` so as to extract its locals.
    
    :return: The locals in `keys` with their values, as a dictionary.
    
    :note: Extracting the locals requires executing the function and is fairly inefficient.
    """
    func_locals = {'doc':function.__doc__}
    def probeFunc(frame, event, arg):
        if event == 'call' and len(inspect.stack()) > depth:
            return None
        elif event == 'return' and len(inspect.stack()) == depth:
            locals = frame.f_locals
            func_locals.update(dict((k,locals.get(k)) for k in keys))
            sys.settrace(None)
        elif event == 'exception' or event == 'c_exception':
            sys.settrace(None)
        return probeFunc
    depth = len(inspect.stack())+2
    sys.settrace(probeFunc)
    function(*args)
    return func_locals

def _getlocals(function, *args):
    """Execute a function and return its locals (private).
    
    :Parameters:
        - `function`: The function from which to extract the locals.
        - `args`: Arguments to be passed to `function` so as to extract its locals.
    
    :return: All the locals of `function` together with their values, as a dictionary.
    
    :note: Extracting the locals requires executing the function and is fairly inefficient.
    """
    func_locals = {'doc':function.__doc__}
    def probeFunc(frame, event, arg):
        if event == 'return' and len(inspect.stack()) == depth:
            func_locals.update(frame.f_locals)
            sys.settrace(None)
        return probeFunc
    depth = len(inspect.stack())+2
    sys.settrace(probeFunc)
    function(*args)
    return func_locals

# -------- Error classes --------

class TransitionDeclarationError(Exception):
    """Signals that the ``@transition`` decorator must be used within a state declaration."""

class TransitionBadActionName(Exception):
    """Signals that the name of the function defining a transition must be ``action``."""

# -------- decorators to declare states and transitions --------
    
class state(State):
    """This decorator class is used to declare the states of a state machine.
    
    For the technically inclined, here is how it works:
    
    When ``@state`` decorates a function ``s`` in the body of a `statemachine`, the class `state` is instantiated and 
    the new state object is stored in the variable ``s``.
    When the state machine is initialized (`statemachine.__init__`), it looks up its class attributes that derive from `state`.
    It calls each such attribute, i.e. it invokes the `__call__` function of the state object created by the decorator.
    This `__call__` function, in turn, calls the function that was decorated, i.e. the function following the ``@state`` line.
    This function is supposed to define the enter/leave functions for the state and the transitions, declared using the ``@transition`` decorator.
    The ``@transition`` decorator creates transition objects and stores them in the ``transitions`` variable of the state.
    Finally, the `__call__` function retreives and stores these enter and leave actions, if any.
    """

    @classmethod
    def uid(cls):
        """Return a unique, monotonically increasing id. 
        
        Used to find the first state declared in a state machine.
        """
        try:
            cls.nextuid += 1
        except Exception:
            cls.nextuid = 1
        return cls.nextuid

    # This is called when @state is encountered, i.e. when a state machine class is declared
    def __init__(self, func):
        """Initialize a state created by the ``@state`` decorator.
        
        :param func: The function defining the state.
        """
        if __debug__:
            print "Declaring state", func.__name__
        super(state, self).__init__(func.__name__)
        #self.__dict__ = func.__dict__  # this is a bit extreme I think...
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.func = func
        self.uid = self.uid()

    # This is called when the state is called, when initializing a state machine, i.e. when a state machine is instantiated.
    def __call__(self, state_machine):
        """The wrapper function of the state decorator.
        
        Calls the original state function and extracts its enter/leave actions, if any.
        """
        if __debug__:
            print "Initializing", self

        # call the state function that was decorated and extract the enter/leave functions that it declares, if any.
        func_locals = _getsomelocals(self.func, ('enter', 'leave'), state_machine)

        self.enter = func_locals.get('enter')
        if self.enter and not callable(self.enter):
            self.enter = None

        self.leave = func_locals.get('leave')
        if self.leave and not callable(self.leave):
            self.leave = None

class transition(Transition):
    """This decorator class is used to declare the transitions of a state machine.
    
    For the technically inclined, here is how it works:
    
    This decorator takes as parameters the event type, additional event matching information, an optional guard and an optional destination state.
    When ``@transition`` is evaluated, i.e. when the enclosing state machine is being initialized, the class `transition` is instantiated
    and the decorator's arguments passed to its `__init__` method. Then, the new object is called, i.e. its `__call__` function is called.
    (Note that this differs from the `state` decorator, because ``@transition`` takes arguments while ``@state`` does not).
    The `__call__` function adds the transition to the list of transitions of its enclosing state.

    We require that any function decorated by ``@transition`` be called ``action``. 
    This is meant to facilitate programming (inventing transition names is often difficult) and to avoid polluting the namespace. 
    We also check that the ``@transition`` decorator is used only inside the declaration of a state.
    """

    # This is called when @transition is encountered, i.e. when a state machine is initialized
    # (The state machine calls each state in turn, and each state function contains its transitions)
    def __init__(self, event_type, *args, **kwargs):
        """Initialize a transition created by the ``@transition`` decorator.

        :Parameters:
            - `event_type`: The type of the events to be matched.
            - `args`: Additional positional arguments for matching events.
            - `kwargs`: Keyword arguments for matching events and for specifying the transition (see below).
        
        :Keywords:
            - `guard`: Optional keyword argument to specify a callable to be called to filter events.
            - `to`: Optional keyword argument to specify the name of the destination state (if not specified, the transition loops on its state).
        
        :Exceptions:
            - `StateUnknown`: The destination state does not exist or is not a state.
            - `TransitionBadAction`: The transition's action is not callable.
            - `TransitionBadGuard`: The transition's guard is not callable.
        """
        super(transition, self).__init__(event_type, *args, **kwargs)

    # This is called right after the initialization above and must return the wrapped function.
    # Since all transition functions are called 'action', we us a single wrapper for all transitions.
    # The wrapper stores the transitions as a list in its 'transitions' attribute.
    def __call__(self, func):
        """Finish creating a transition declared by the ``@transition decorator``.
        
        Check that the function being wrapped is called ``action``, and that it is declared inside the declaration of a state.
        Add the transition objects to the state's list of transitions.
        
        :param func: the function being decorated, i.e. the transition action.
        """
        if __debug__:
            print "  Declaring", self

        # func must be called 'action': 
        if func.__name__ != 'action':
            raise TransitionBadActionName, "The function '%s' declared with the @transition decorator must be called 'action'." % func.__name__

        self.action = func

        # we're supposed to be called by the state decorator function, which calls '_getsomelocals'
        # This is why we go up 3 levels in the call stack to find the state we belong to.
        locals = sys._getframe(3).f_locals
        my_state = None
        if locals:
            my_state = locals.get('self')
        if not locals or not my_state or not isinstance(my_state, state):
            raise TransitionDeclarationError, "A transition must be declared within a state"
        my_state.transitions.append(self)

        return func

class statemachine(StateMachine):
    """A state machine that can use the ``@state`` and ``@transition`` decorators to declare the structure of the machine.
    
    Like regular state machines, additional states and transitions can be added with the `sm.StateMachine.add_state` and `sm.StateMachine.add_transition` methods.
    """
    
    def __init__(self, active = True, call_actions = False):
        """Initialize a new state machine.
        
        :Parameters:
            - `active`: specifies whether the state machine is immediately processing events.
            - `call_actions`: specifies whether to call enter/leave actions when starting/suspending/resuming/resetting the state machine.
        """
        super(statemachine, self).__init__(active, call_actions)
        
        # go through the declared states and call them.
        # this will call state.__call__ which will initialize the state.
        # also initialize start_state (and current_state) with the lowest numbered state
        start_id = 0
        for my_name, my_state in self.__class__.__dict__.items():
            if isinstance(my_state, state) and callable(my_state):
                # we make a copy of the state otherwise it would be shared among instances of the state machine class.
                # we keep a link from the copy to the original so that find_state can return the copy when given the id of the original.
                original = my_state
                my_state = copy.deepcopy(original)
                my_state.original = original
                my_state.state_machine = self
                
                # call the state, which will declare the enter/leave actions and the transitions
                my_state(self)
                
                # add it to the list of states
                self.states.append(my_state)
                
                # make it the start state if needed
                if not self.start_state or my_state.uid < start_id:
                    start_id = my_state.uid
                    self.start_state = my_state
        
        # now fix the destination states of the transitions so they point to the copies instead of the originals:
        for my_state in self.states:
            for transition in my_state.transitions:
                if transition.to_state:
                    transition.to_state = self.find_state(transition.to_state)
        
        # set initial state
        self.current_state = self.start_state
        
        if self.active and self.call_actions_from_reset:
            # temporarily setting active to False allows the enter action to distinguish from normal calls
            self.active = False
            self.current_state.enter()
            self.active = True
