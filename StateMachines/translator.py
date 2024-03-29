# -*- coding: utf-8 -*-
#
# Python State Machines
#
# Copyright 2007-2011, Université Paris-Sud
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

from __future__ import with_statement

import os
from os import stat
import py_compile
import re
import sys

_indent_exp_str = ur'^(\s*)'
_indent_exp = re.compile(_indent_exp_str)
_state_exp_str = ur'^\s*State\s+(?P<name>[-A-Za-z0-9_]+)\s*(?:\(\s*(?P<parent>[-A-Za-z0-9_]+)\s*\))?\s*:'
_state_exp = re.compile(_state_exp_str)
_transition_exp_str = ur'^\s*Transition\s+(?P<name>[-A-Za-z0-9_]+)\s*' \
                       ur'\(\s*self\s*,\s*(?P<args>.*)\)\s*(?:>>\s*(?P<target>.*?)\s*)?:'
_transition_exp = re.compile(_transition_exp_str)
_def_exp_str = ur'^\s*def\s+(?P<name>[-A-Za-z0-9_]+)\s*\(\s*self\s*(?P<args>.*)\)\s*:'
_def_exp = re.compile(_def_exp_str)
class PySMTranslator(object):
    def translate(self, smFileName, pyFileName, cleanUp=True, force=False):
        pycFileName = pyFileName + 'c'
        pyoFileName = pyFileName + 'o'
        if os.path.exists(smFileName) and (force or not (
            (os.path.exists(pyFileName) and stat(pyFileName).st_mtime >= stat(smFileName).st_mtime)
            or (os.path.exists(pycFileName) and stat(pycFileName).st_mtime >= stat(smFileName).st_mtime)
            or (os.path.exists(pyoFileName) and stat(pyoFileName).st_mtime >= stat(smFileName).st_mtime))):
            # print "Translating", inFilename, "to", outFilename
            self._doTranslate(smFileName, pyFileName)
            self.postProcess(smFileName, pyFileName, cleanUp=cleanUp)
    
    def postProcess(self, fileName, pyFileName, cleanUp=True):
        py_compile.compile(pyFileName, dfile=fileName)
        if (os.path.exists(pyFileName + 'c') or os.path.exists(pyFileName + 'o')) and \
           os.path.exists(pyFileName) and os.path.exists(fileName):
           if cleanUp:
               os.unlink(pyFileName)
               print "Unlinking", pyFileName
           
    def _doTranslate(self, inFilename, outFilename):
        indent = 0
        in_state = False
        state_indent = 0
        in_transition = False
        transition_indent = 0
        with open(inFilename, 'r') as f:
            with open(outFilename, 'w') as out:
                out.write(self._initialize())
                
                for line_no, line in enumerate(f):
                    line_indent = _indent_exp.search(line).end() # Assume match
                    code = line.strip()
                    if not code or code.startswith('#'):
                        # Empty line or comment
                        out.write(line)
                        continue
                        
                    if line_indent < indent:
                        # de-dent
                        if in_transition and line_indent <= transition_indent:
                            in_transition = False
                            out.write(self._finishTranslatingTransitionStatement(u' '*transition_indent))
                            transition_indent = 0
                        if in_state and line_indent <= state_indent:
                            in_state = False
                            out.write(self._finishTranslatingStateStatement(u' '*state_indent))
                            state_indent = 0
                            
                    indent = line_indent
                        
                    if not in_state:
                        m = _state_exp.search(line)
                        if m:
                            in_state = True
                            state_indent = indent
                            out.write(self._translateStateStatement(m, u' '*indent))
                        else:
                            out.write(line)
                    else: 
                        # Parsing in_state
                        m = _def_exp.search(line)
                        if m:
                            out.write(self._translateDefStatement(m, u' '*indent))
                        elif not in_transition: 
                            m = _transition_exp.search(line)
                            if m:
                                in_transition = True
                                transition_indent = indent
                                out.write(self._translateTransitionStatement(m, u' '*indent))
                            else:
                                out.write(line)
                        else:
                            # Not a def statement or a transition statement, write it as-is
                            out.write(line)
                
                # Clean up
                out.write("\n")
                
                if in_transition:
                    out.write(self._finishTranslatingTransitionStatement(u' '*transition_indent))
                
                if in_state:
                    out.write(self._finishTranslatingStateStatement(u' '*state_indent))
                            
                            
    def _initialize(self):
        return ''
#         return '''\
# from __future__ import with_statement
# 
# from StateMachines import *
# 
# '''
        
    def _translateStateStatement(self, m, indent):
        name = m.group("name")
        parent = m.group("parent")
        
        if not parent:
            parent = 'State'
        
        self._stateName = name
        
        # return indent + "class %sState(%s):\n" % (name, parent)
        return indent + "@state\n" + \
               indent + "def %s(self):\n" % (name)
    
    def _finishTranslatingStateStatement(self, my_indent):
        # return "%s%s = %sState()\n\n\n" % (my_indent, self._stateName, self._stateName)
        return ""
    
    def _translateTransitionStatement(self, m, indent):
        name = m.group("name")
        args = m.group("args")
        targetState = m.group("target")
        
        if targetState:
            target = ", to=%s" % (targetState)
        else:
            target = ""
        
        self._transitionName = name
        
        # return indent + "@transition(%s%s)\n" % (args, target) + \
        #        indent + "def %s(state, self):\n" % (name)
        return indent + "@transition(%s%s)\n" % (args, target) + \
               indent + "def action(event):\n"
    
    def _finishTranslatingTransitionStatement(self, my_indent):
        return ''
    
    def _translateDefStatement(self, m, indent):
        name = m.group("name")
        args = m.group("args")
        
        # return indent + "def %s(state, %s):\n" % (name, args)
        # return indent + "def %s(%s):\n" % (name, args)
        decorator = ''
        if name in ('enter', 'leave'):
            decorator = "%s@state.%s\n" % (indent, name)
        return "%s%sdef %s(%s):\n" % (decorator, indent, name, args)

class PySMMetaImporter(object):
    def find_module(self, fullname, path=None):
        # print 'find_module(%s, %s)' % (fullname, path)
        moduleName = fullname.rsplit('.', 1)[-1]
        for d in (path or sys.path):
            fileName = os.path.join(d, moduleName + '.pysm')
            pyFileName = os.path.join(d, moduleName + '.py')
            if os.path.exists(fileName):
                print 'translating', fileName, 'to', pyFileName
                PySMTranslator().translate(fileName,
                                           os.path.join(d, moduleName + '.py'))
                
        
        return None

sys.meta_path.append(PySMMetaImporter())

__all__ = ['PySMTranslator']

        
if __name__ == '__main__':
    import os
    translator = PySMTranslator()
    
    options = {}
    
    args = []
    for arg in sys.argv:
        if arg == '--force':
            options['force'] = True
        elif arg == '--noCleanUp':
            options['cleanUp'] = False
        elif arg.startswith('--'):
            print "Unrecognized option:", arg
        else:
            args.append(arg)
    
    if len(args) < 3:
        outFile = os.path.splitext(args[1])[0] + '.py'
    else:
        outFile = args[2]
        
    print 'translate from %s to %s' % (args[1], outFile)
    translator.translate(args[1], outFile, **options)
    
