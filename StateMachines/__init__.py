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

"""
This package implements State Machines.

Submodule `sm` supports state machines that are defined programatically,
while submodule `decorator` supports state machines that are defined declaratively.
It is safe to ``import *`` from either this package or from either submodule.

:author: Michel Beaudouin-Lafon
:contact: mbl@lri.fr
:version: 0.1
:date: 4 December 2007

"""
__docformat__ = "restructuredtext en"

from sm import *
from decorator import *
from translator import *
