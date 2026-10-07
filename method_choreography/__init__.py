"""Method Choreography is separate from Motion Identity and visual execution."""
from .compiler import compile_choreography
from .validation import inspect_choreography, validate_choreography, project_choreography, analyze_legacy
from .synthetic import compile_synthetic_peel

__all__=['compile_choreography','inspect_choreography','validate_choreography',
         'project_choreography','analyze_legacy','compile_synthetic_peel']
