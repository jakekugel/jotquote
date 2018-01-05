Contributing to jotquote
========================

As an open source project, contributions are welcome.  Examples of
contributions include:

* Code patches
* Documentation improvements
* Bug reports and patch reviews

If you have an idea for jotquote, run it by me before you begin
writing code.  This way, I can get you going in the right direction.

Development environment setup
-----------------------------
1. (Optional, but recommended) Create a virtualenv to work in, and activate it.

2. Install development requirements::

    $ pip install -r dev-requirements.txt

3.  Install jotquote in editable mode::

    $ pip install --editable .

Running unit tests
------------------
Once the development environment has been configured as described above,
the unit tests can be run with this command::

    $ nosetests

Or to run and measure code coverage::

    $ nosetests  --with-coverage

Running tox tests
-----------------
Tox can be used to run the tests on multiple Python versions.  As a
prerequisite, the Python interpreters for the different versions must
be installed.  After installing development requirements as described above,
the tox tests can be run using this command::

    $ tox

