"""Frozen teaching projections. No solver, Registry or Review creation."""

from .compiler import PedagogyCompiler, compile_plan
from .validation import validate_plan, inspect_historical
from .handoff import copy_projection, motion_projection, validate_handoff

__all__ = ['PedagogyCompiler', 'compile_plan', 'validate_plan',
           'inspect_historical', 'copy_projection', 'motion_projection',
           'validate_handoff']
