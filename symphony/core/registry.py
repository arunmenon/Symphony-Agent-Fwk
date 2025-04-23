"""Service registry for Symphony components.

This module has been refactored and moved to symphony.core.registry.
This module is kept for backward compatibility and will be removed in a future release.
"""

from symphony.core.registry.base import ServiceRegistry

# Re-export for backward compatibility
__all__ = ['ServiceRegistry']