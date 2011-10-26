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

import StateMachines
import pysmTest

import subprocess
import sys

#subprocess.call(("%s pysmTest.py" % (sys.executable)).split())
subprocess.Popen("python pysmTest.pyc", shell=True)
