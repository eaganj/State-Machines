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
    def translate(self, smFileName, pyFileName):
        pycFileName = pyFileName + 'c'
        pyoFileName = pyFileName + 'o'
        if os.path.exists(smFileName) and not (
            (os.path.exists(pyFileName) and stat(pyFileName).st_mtime >= stat(smFileName).st_mtime)
            or (os.path.exists(pycFileName) and stat(pycFileName).st_mtime >= stat(smFileName).st_mtime)
            or (os.path.exists(pyoFileName) and stat(pyoFileName).st_mtime >= stat(smFileName).st_mtime)):
            # print "Translating", inFilename, "to", outFilename
            self._doTranslate(smFileName, pyFileName)
            self.postProcess(smFileName, pyFileName)
    
    def postProcess(self, fileName, pyFileName):
        py_compile.compile(pyFileName, dfile=fileName)
        if (os.path.exists(pyFileName + 'c') or os.path.exists(pyFileName + 'o')) and \
           os.path.exists(pyFileName) and os.path.exists(fileName):
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
        return '''\
from __future__ import with_statement

from StateMachines import *

'''
        
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
        return indent + "def %s(%s):\n" % (name, args)

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
    
    if len(sys.argv) < 3:
        outFile = os.path.splitext(sys.argv[1])[0] + '.py'
    else:
        outFile = sys.argv[2]
        
    print 'translate from %s to %s' % (sys.argv[1], outFile)
    translator.translate(sys.argv[1], outFile)
    
