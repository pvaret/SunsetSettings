API Reference
=============

sunset.Settings
---------------

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: derive

    .. automethod:: deriveAs

    .. automethod:: name

    .. automethod:: setName

    .. automethod:: onKeyModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

    .. automethod:: siblings

sunset.Key
----------

.. autofunction:: sunset.NewKey

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: clear

    .. automethod:: onValueChangeCall

    .. automethod:: onKeyModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.Section
--------------

.. autofunction:: sunset.NewSection

.. autoclass:: sunset.Section

    .. automethod:: derive

    .. automethod:: onKeyModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.List
-----------

.. autofunction:: sunset.NewKeyList

.. autofunction:: sunset.NewSectionList

.. autoclass:: sunset.List

    .. automethod:: iterAll

    .. automethod:: onKeyModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.protocols.Serializable
-----------------------------

.. autoclass:: sunset.protocols.Serializable

    .. automethod:: fromStr

    .. automethod:: toStr
