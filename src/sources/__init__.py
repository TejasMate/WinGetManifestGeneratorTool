"""
Sources Package - Consolidated source implementations.

Each source (github, gitlab, sourceforge) is implemented as a single file
containing all necessary functionality for that source type.
"""

# Import source modules
try:
    from . import github
except ImportError:
    github = None

try:
    from . import gitlab  
except ImportError:
    gitlab = None

try:
    from . import sourceforge
except ImportError:
    sourceforge = None


def get_source_module(source_type: str):
    """Get a source module by type."""
    sources = {
        'github': github,
        'gitlab': gitlab,
        'sourceforge': sourceforge,
    }
    
    module = sources.get(source_type)
    if module is None:
        raise ValueError(f"Unknown source type: {source_type}")
    return module


def list_available_sources():
    """List all available source types."""
    return ['github', 'gitlab', 'sourceforge']


def run_source_workflow(source_type: str, input_file: str = None):
    """Run the complete workflow for a specific source."""
    module = get_source_module(source_type)
    
    if hasattr(module, 'main'):
        return module.main()
    else:
        # Try to get orchestrator class
        orchestrator_name = f"{source_type.title()}Orchestrator"
        if hasattr(module, orchestrator_name):
            orchestrator_class = getattr(module, orchestrator_name)
            orchestrator = orchestrator_class()
            return orchestrator.run_complete_workflow(input_file)
        else:
            raise NotImplementedError(f"No workflow implementation found for {source_type}")


__all__ = [
    'github',
    'gitlab', 
    'sourceforge',
    'get_source_module',
    'list_available_sources',
    'run_source_workflow',
]
