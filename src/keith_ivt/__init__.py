"""Legacy HappyMeasure implementation namespace.

The public product/package name is now ``happymeasure``.  This historical
``keith_ivt`` namespace is retained so existing imports and local tools keep
working while the codebase is migrated incrementally.
"""

from keith_ivt.version import __version__

__all__ = ["__version__"]
