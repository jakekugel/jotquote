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
1. (Optional, but recommended) Install `uv <https://docs.astral.sh/uv/>`_.

2. Install jotquote and all development dependencies::

    $ uv sync --group dev

Running unit tests
------------------
Once the development environment has been configured as described above,
the unit tests can be run with this command::

    $ uv run pytest

Or to run and measure code coverage::

    $ uv run coverage run -m pytest
    $ uv run coverage report

Running lint
------------
::

    $ uv run python -m flake8 jotquote/

On Windows, using ``python -m flake8`` avoids Application Control policy
restrictions that may block the ``flake8`` wrapper executable directly.

Multi-version CI
----------------
Multi-version testing (Python 3.8–3.14 on Linux, Mac, and Windows) is
handled automatically by GitHub Actions on push and pull request.
