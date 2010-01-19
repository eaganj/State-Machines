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
