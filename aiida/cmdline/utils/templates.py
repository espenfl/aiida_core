"""Templates for input/output of verdi commands."""
from __future__ import absolute_import
from jinja2 import Environment, PackageLoader

#pylint: disable=invalid-name
env = Environment(loader=PackageLoader('aiida', 'cmdline/templates'))
