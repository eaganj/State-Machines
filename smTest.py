# -*- coding: utf-8 -*-
#
# Python State Machines
#
# Copyright 2009-2011, Université Paris-Sud
# by Michel Beaudouin-Lafon (mbl at lri . fr)
# and James R. Eagan (code at my last name dot me)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# and GNU Lesser General Public License along with this program.  
# If not, see <http://www.gnu.org/licenses/>.


""" This module tests state machines."""

import unittest
import StateMachines
from StateMachines import *

# -------- utilities for the state machine examples --------

class Point(object):
    def __init__(self, x, y):
        super(Point, self).__init__()
        self.x = x
        self.y = y
        
class Key(Event):
    def __init__(self, key):
        super(Press, self).__init__("Key")
        self.key = key
    
    def __str__(self):
        return 'Key %d' % self.key

class Press(Event):
    def __init__(self, button, x, y):
        super(Press, self).__init__("Press")
        self.button = button
        self.x = x
        self.y = y
    
    def match(self, transition):
        if transition.args:
            return transition.args[0] == self.button
        return True
    
    def __str__(self):
        return 'Press %s at %d, %d' % (self.button, self.x, self.y)

class Move(Event):
    def __init__(self, x, y):
        super(Move, self).__init__("Move")
        self.x = x
        self.y = y
    
    def __str__(self):
        return 'Move to %d, %d' % (self.x, self.y)

class Release(Event):
    def __init__(self, button, x, y):
        super(Release, self).__init__("Release")
        self.button = button
        self.x = x
        self.y = y
    
    def match(self, transition):
        if transition.args:
            return transition.args[0] == self.button
        return True
    
    def __str__(self):
        return 'Release %s at %d, %d' % (self.button, self.x, self.y)

        

# -------- An example --------

print 'Declaring DragSM'

class DragSM(statemachine):
    """A state machine for drag-and-drop"""
    def __init__(self):
        super(DragSM, self).__init__()
        self.foo = 10
    
    startPoint = Point(0,0)
    
    def hysteresis(self, p1, p2, delta=5):
        if abs(p1.x - p2.x) > delta:
            return True
        if abs(p1.y - p2.y) > delta:
            return True
        return False
    
    @state
    def start(self):
        """Start state"""
        
        @state.enter
        def enter():
            print "entering Start"
        
        @state.leave
        def leave():
            print "leaving Start"
        
        @transition(Press, 'Button1', to=self.wait)
        def action(event):
            self.startPoint = Point(event.x, event.y)
        
        @transition(Key, to=self.drag)
        def action(event):
            print "transition Key"
    
    @state
    def wait(self):
        @transition(Move, guard=lambda event: self.hysteresis(self.startPoint, event), to=self.drag)
        def action(event):
            pass
    
    @state
    def drag(self):
        """Drag state"""
        
        @state.enter
        def enter():
            print "entering Drag"
        
        @state.leave
        def leave():
            print "leaving Drag"
        
        @transition(Move)
        def action(event):
            print "dragging"
        
        @transition(Release, 'Button1', to=self.start)
        def action(event):
                print "transition Release"

print 'Done declaring DragSM'
print

class StaticSMTest(unittest.TestCase):

    def testOK(self):
        print 'testOK'
        print 'Instantiating DragSM'
        dnd = DragSM()
        print 'Done instantiating DragSM'
        
        self.assertEqual([str(state) for state in dnd.all_states()], ['state start', 'state drag', 'state wait'])
        self.assertEqual([str(trans) for trans in dnd.transitions_from(dnd.start)], 
            ['transition on Press with Button1 to state wait', 'transition on Key to state drag'])
        self.assertEqual([str(trans) for trans in dnd.transitions_from(dnd.wait)], 
            ['transition on Move with guard to state drag'])
        self.assertEqual([str(trans) for trans in dnd.transitions_from(dnd.drag)], 
            ['transition on Move to itself', 'transition on Release with Button1 to state start'])
        
        self.assertEqual([str(trans) for trans in dnd.transitions_to(dnd.drag)], 
            ['transition on Key to state drag', 'transition on Move to itself', 'transition on Move with guard to state drag'])
        self.assertEqual([str(trans) for trans in dnd.transitions_between(dnd.drag, dnd.start)], 
            ['transition on Release with Button1 to state start'])
        self.assertEqual([str(trans) for trans in dnd.all_transitions()], 
            ['transition on Press with Button1 to state wait', 
             'transition on Key to state drag', 
             'transition on Move to itself', 
             'transition on Release with Button1 to state start', 
             'transition on Move with guard to state drag'
            ])
        
        
        # test the equality test of states
        self.assertEqual(dnd.wait, dnd.find_state(dnd.wait))
        
        dnd.process_event(Press('Button1', 10, 10))
        self.assertEqual(dnd._sm_current_state, dnd.wait)
        
        dnd.process_event(Move(12, 10))
        self.assertEqual(dnd._sm_current_state, dnd.wait)
        
        dnd.process_event(Move(14, 14))
        self.assertEqual(dnd._sm_current_state, dnd.wait)
        
        dnd.process_event(Move(16, 14))
        self.assertEqual(dnd._sm_current_state, dnd.drag)
        
        dnd.process_event(Move(20, 16))
        self.assertEqual(dnd._sm_current_state, dnd.drag)
        
        dnd.process_event(Release('Button2', 16, 16))
        self.assertEqual(dnd._sm_current_state, dnd.drag)
        
        dnd.process_event(Release('Button1', 16, 16))
        self.assertEqual(dnd._sm_current_state, dnd.start)
        print 'Done testOK'
        print
    
    def testBadActionName(self):
        print 'testBadActionName'
        class BadActionName(statemachine):
            @state
            def start(self):
                @transition(Press)
                def myaction(event):    # should be 'action'
                    pass
        self.assertRaises(TransitionBadActionName, BadActionName)
        print 'Done testBadActionName'
        print
    
    def testDeclarationError(self):
        print 'testDeclarationError'
        class BadDeclaration(statemachine):
            #@transition(Press)
            def action(event):
                pass
            # this is equivalent to having @transition above
            self.assertRaises(TransitionDeclarationError, transition(Press), action)
        print 'Done testDeclarationError'
        print

    def testBadToState(self):
        print 'testBadToState'
        class BadToState(statemachine):
            @state
            def start(self):
                @transition(Press, to=self.other)   # the destination state must exist
                def action(event):
                    pass
            def other():
                pass
        self.assertRaises(StateUnknown, BadToState)
        print 'Done testBadToState'
        print
    
    def testFindState(self):
        print 'testFindState'
        print 'Instantiating DragSM'
        dnd = DragSM()
        print 'Done instantiating DragSM'
        self.assertNotEqual(dnd.find_state('drag'), None)
        self.assertNotEqual(dnd.find_state(dnd.drag), None)
        self.assertEqual(dnd.find_state('drag'), dnd.find_state(dnd.drag))
        self.assertEqual(dnd.find_state('drag'), dnd.drag)
        self.assertEqual(dnd.find_state('foo'), None)
        self.assertEqual(dnd.find_state(dnd.hysteresis), None)
        print 'Done testFindState'
        print
    
class DynamicSMTest(unittest.TestCase):
    def testDynSM(self):
        print 'testDynSM'
        class MySM(StateMachine):
            """a state machine where states are built dynamically"""
            startPoint = Point(0,0)

            def hysteresis(self, p1, p2, delta=5):
                if abs(p1.x - p2.x) > delta:
                    return True
                if abs(p1.y - p2.y) > delta:
                    return True
                return False

            def enter_start(self):
                print "Entering start state"

            def leave_start(self):
                print "Leaving start state"

            def press_action(self, event):
                self.startPoint = Point(event.x, event.y)
                print "Pressed button in start state"
        
            def __init__(self):
                super(MySM, self).__init__()
                self.add_state('start', enter=self.enter_start, leave=self.leave_start)
                self.add_state('wait')
                self.add_state('drag')
                
                self.add_transition('start', Press, 'Button1', to='wait', action=self.press_action)
                self.add_transition('start', Key, to='drag')
                self.add_transition('wait', Move, guard=lambda event: self.hysteresis(self.startPoint, event), to='drag')
                self.add_transition('drag', Move)
                self.add_transition('drag', Release, 'Button1', to='start')

        print "Instantiating MySM"
        sm = MySM()
        print "Done instantiating MySM"
        
        self.assertEqual([str(state) for state in sm.all_states()], ['state start', 'state wait', 'state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('start')], 
            ['transition on Press with Button1 to state wait', 'transition on Key to state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('wait')], 
            ['transition on Move with guard to state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('drag')], 
            ['transition on Move to itself', 'transition on Release with Button1 to state start'])
        
        self.assertEqual([str(trans) for trans in sm.transitions_to('drag')], 
            ['transition on Key to state drag', 'transition on Move with guard to state drag', 'transition on Move to itself'])
        self.assertEqual([str(trans) for trans in sm.transitions_between('drag', 'start')], 
            ['transition on Release with Button1 to state start'])
        self.assertEqual([str(trans) for trans in sm.all_transitions()], 
            ['transition on Press with Button1 to state wait', 
             'transition on Key to state drag', 
             'transition on Move with guard to state drag',
             'transition on Move to itself',
             'transition on Release with Button1 to state start'
            ])
        
        sm.process_event(Press('Button1', 10, 10))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(12, 10))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(14, 14))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(16, 14))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Move(20, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Release('Button2', 16, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Release('Button1', 16, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('start'))
        
        print 'Done testDynSM'
        print


class HybridSMTest(unittest.TestCase):
    
    print "Declaring MyHybridSM"
    class MyHybridSM(statemachine):
        startPoint = Point(0,0)

        def hysteresis(self, p1, p2, delta=5):
            if abs(p1.x - p2.x) > delta:
                return True
            if abs(p1.y - p2.y) > delta:
                return True
            return False

        @state
        def start(self):
            @transition(Press, 'Button1', to=self.wait)
            def action(event):
                self.startPoint = Point(event.x, event.y)
                print "Pressed"

        @state
        def wait(self):
            pass
    print "Done declaring MyHybridSM"
    print
    
    def testHybridSM(self):
        print 'testHybridSM'
            
        def indrag():
            print "in drag"
        
        print "Instantiating MyHybridSM"
        sm = HybridSMTest.MyHybridSM()
        print "Done instantiating MyHybridSM"
        
        sm.add_state('drag', enter=indrag)
        sm.add_transition('start', Key, to='drag')
        sm.add_transition('wait', Move, guard=lambda event: sm.hysteresis(sm.startPoint, event), to='drag')
        sm.add_transition('drag', Move)
        sm.add_transition('drag', Release, 'Button1', to='start')
        
        self.assertEqual([str(state) for state in sm.all_states()], ['state start', 'state wait', 'state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('start')], 
            ['transition on Press with Button1 to state wait', 'transition on Key to state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('wait')], 
            ['transition on Move with guard to state drag'])
        self.assertEqual([str(trans) for trans in sm.transitions_from('drag')], 
            ['transition on Move to itself', 'transition on Release with Button1 to state start'])
        
        self.assertEqual([str(trans) for trans in sm.transitions_to('drag')], 
            ['transition on Key to state drag', 'transition on Move with guard to state drag', 'transition on Move to itself'])
        self.assertEqual([str(trans) for trans in sm.transitions_between('drag', 'start')], 
            ['transition on Release with Button1 to state start'])
        self.assertEqual([str(trans) for trans in sm.all_transitions()], 
            ['transition on Press with Button1 to state wait', 
             'transition on Key to state drag', 
             'transition on Move with guard to state drag',
             'transition on Move to itself',
             'transition on Release with Button1 to state start'
            ])
        
        sm.process_event(Press('Button1', 10, 10))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(12, 10))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(14, 14))
        self.assertEqual(sm._sm_current_state, sm.find_state('wait'))
        
        sm.process_event(Move(16, 14))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Move(20, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Release('Button2', 16, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('drag'))
        
        sm.process_event(Release('Button1', 16, 16))
        self.assertEqual(sm._sm_current_state, sm.find_state('start'))
        
        print 'Done testHybridSM'
        print

if __name__ == "__main__":
    unittest.main()
