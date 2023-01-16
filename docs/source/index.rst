Welcome to SunsetSettings's documentation!
==========================================

SunsetSettings is a library that provides facilities to declare and use settings
for an interactive application in a *type-safe* manner, and load and save them
in a simple INI-like format.

The settings can safely store arbitrary types, and can be structured in an
arbitrarily deep hierarchy of subsections, which allows you to implement
overrides per project, per folder, per user, etc.

It is mainly intended for software where the user can change settings on the
fly, for instance with a settings dialog, and those settings need to be
preserved between sessions.

.. toctree::
   :maxdepth: 2

   installation
   usage
   api
   changelog


Indices and tables
==================

* :ref:`genindex`
