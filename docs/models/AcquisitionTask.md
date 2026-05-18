# AcquisitionTask Model

Base class used for declarative class definitions.

The :class:`_orm.DeclarativeBase` allows for the creation of new
declarative bases in such a way that is compatible with type checkers::


    from sqlalchemy.orm import DeclarativeBase


    class Base(DeclarativeBase):
        pass

The above ``Base`` class is now usable as the base for new declarative
mappings.  The superclass makes use of the ``__init_subclass__()``
method to set up new classes and metaclasses aren't used.

When first used, the :class:`_orm.DeclarativeBase` class instantiates a new
:class:`_orm.registry` to be used with the base, assuming one was not
provided explicitly. The :class:`_orm.DeclarativeBase` class supports
class-level attributes which act as parameters for the construction of this
registry; such as to indicate a specific :class:`_schema.MetaData`
collection as well as a specific value for
:paramref:`_orm.registry.type_annotation_map`::

    from typing_extensions import Annotated

    from sqlalchemy import BigInteger
    from sqlalchemy import MetaData
    from sqlalchemy import String
    from sqlalchemy.orm import DeclarativeBase

    bigint = Annotated[int, "bigint"]
    my_metadata = MetaData()


    class Base(DeclarativeBase):
        metadata = my_metadata
        type_annotation_map = {
            str: String().with_variant(String(255), "mysql", "mariadb"),
            bigint: BigInteger(),
        }

Class-level attributes which may be specified include:

:param metadata: optional :class:`_schema.MetaData` collection.
 If a :class:`_orm.registry` is constructed automatically, this
 :class:`_schema.MetaData` collection will be used to construct it.
 Otherwise, the local :class:`_schema.MetaData` collection will supersede
 that used by an existing :class:`_orm.registry` passed using the
 :paramref:`_orm.DeclarativeBase.registry` parameter.
:param type_annotation_map: optional type annotation map that will be
 passed to the :class:`_orm.registry` as
 :paramref:`_orm.registry.type_annotation_map`.
:param registry: supply a pre-existing :class:`_orm.registry` directly.

.. versionadded:: 2.0  Added :class:`.DeclarativeBase`, so that declarative
   base classes may be constructed in such a way that is also recognized
   by :pep:`484` type checkers.   As a result, :class:`.DeclarativeBase`
   and other subclassing-oriented APIs should be seen as
   superseding previous "class returned by a function" APIs, namely
   :func:`_orm.declarative_base` and :meth:`_orm.registry.generate_base`,
   where the base class returned cannot be recognized by type checkers
   without using plugins.

**__init__ behavior**

In a plain Python class, the base-most ``__init__()`` method in the class
hierarchy is ``object.__init__()``, which accepts no arguments. However,
when the :class:`_orm.DeclarativeBase` subclass is first declared, the
class is given an ``__init__()`` method that links to the
:paramref:`_orm.registry.constructor` constructor function, if no
``__init__()`` method is already present; this is the usual declarative
constructor that will assign keyword arguments as attributes on the
instance, assuming those attributes are established at the class level
(i.e. are mapped, or are linked to a descriptor). This constructor is
**never accessed by a mapped class without being called explicitly via
super()**, as mapped classes are themselves given an ``__init__()`` method
directly which calls :paramref:`_orm.registry.constructor`, so in the
default case works independently of what the base-most ``__init__()``
method does.

.. versionchanged:: 2.0.1  :class:`_orm.DeclarativeBase` has a default
   constructor that links to :paramref:`_orm.registry.constructor` by
   default, so that calls to ``super().__init__()`` can access this
   constructor. Previously, due to an implementation mistake, this default
   constructor was missing, and calling ``super().__init__()`` would invoke
   ``object.__init__()``.

The :class:`_orm.DeclarativeBase` subclass may also declare an explicit
``__init__()`` method which will replace the use of the
:paramref:`_orm.registry.constructor` function at this level::

    class Base(DeclarativeBase):
        def __init__(self, id=None):
            self.id = id

Mapped classes still will not invoke this constructor implicitly; it
remains only accessible by calling ``super().__init__()``::

    class MyClass(Base):
        def __init__(self, id=None, name=None):
            self.name = name
            super().__init__(id=id)

Note that this is a different behavior from what functions like the legacy
:func:`_orm.declarative_base` would do; the base created by those functions
would always install :paramref:`_orm.registry.constructor` for
``__init__()``.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `task_id` | string |  |
| `specimen_id` | string |  |
| `block_id` | string |  |
| `roi_id` | string |  |
| `task_type` | string |  |
| `version` | int |  |
| `status` | string |  |
| `error_message` | string |  |
| `started_at` | datetime |  |
| `completed_at` | datetime |  |
| `tags` | object |  |
| `metadata` | object |  |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
