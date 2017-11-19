popquote
========

.. image:: https://travis-ci.org/jakekugel/popquote.svg?branch=master
    :target: https://travis-ci.org/jakekugel/popquote

.. image:: https://travis-ci.org/jakekugel/popquote/coverage.svg?branch=master
    :target: https://travis-ci.org/jakekugel/popquote?branch=master

popquote is a command-line tool for building a collection of quotes,
and it includes a simple web server to display a quote of the day.
The quotes are stored in a single text file in a human-friendly syntax,
one per line.  100 famous quotes are included with the package, and
it is easy to get started::

    $ pip install popquote
    $ popquote
    The best way out is always through.  - Robert Frost

Although there are 100 quotes included with the package, the purpose of
popquote is to help you build a collection of your own favorites.  Adding
new quotes is easy::

    $ popquote add "The larger the island of knowledge, the longer the shoreline of wonder. - James Madison"
    1 quote added for total of 639 quotes.

Starting the web server
~~~~~~~~~~~~~~~~~~~~~~~
In some cases, the command-line might be good enough for viewing the quotes in your
collection, but you can start a web server that will show a quote of the day.
The ``popquote webserver`` command can be used to start the webserver::

    $ popquote webserver
    * Running on http://127.0.0.1:5544/ (Press CTRL+C to quit)

By default, the web server is only accessible on the system on which
it is running.  But by editing the settings.conf file, the web server can be
made accessible to computers on the network also.  See the section below about
the settings.conf file for details.

The quote file
~~~~~~~~~~~~~~
popquote stores the quotes in a text file that uses a human-friendly syntax
and can be modified with a plain text editor if necessary.  Quotes are stored
in the text file one per line using the syntax:

<quote> | <author> | <publication> | <tag1, tag2, etc...>

For example:

The best way out is always through. | Robert Frost | A Servant to Servants | motivational, poetry

You can find the location of the quote file using the ``popquote info`` command,
and you can change the location by modifying the ``quote_file`` property in
settings.conf (see the settings.conf section below).

The text file is encoded in UTF-8 to allow the full Unicode character set.

Extended functions
~~~~~~~~~~~~~~~~~~
To help you build your collection, the command-line interface has an extended set
of functions including tagging and keyword searching.  Here are a couple of examples.
To display a random quote that has the 'motivational' tag, use the command::

    $ popquote random -t motivational

Or to display all quotes that have the word 'Einstein' in the quote, author name,
or publication name, use this command::

    $ popquote list -k Einstein

The help for these extended functions can be accessed with the '-h' argument;
for example, to see the help for the popquote add function, use
the command::

    $ popquote add -h

The settings.conf file
~~~~~~~~~~~~~~~~~~~~~~
The behavior of the popquote command is controlled with the settings.conf
file.  This file is always found at ~/.popquote/settings.conf on Windows, Mac,
and Linux.

Supported environments
~~~~~~~~~~~~~~~~~~~~~~
popquote is tested on Python 2.7, 3.4, 3.5, and 3.6 on Windows, Mac, and Linux.

Cloud storage
~~~~~~~~~~~~~
If you'd like to make your quotes accessible from multiple computers, you can
put your quote file in a cloud storage service such as Dropbox or Google Drive
and then configure popquote on each computer to use the file on your cloud
storage directory.  To do this, edit the settings.conf file and change the
``quote_file`` property to the path to the file on your cloud storage drive.

Credit
~~~~~~
This package was inspired by other similar utilities including Ken Arnold's original
UNIX utility ``fortune``.  This package also relies on the Flask and Click packages
by Armin Ronacher.  The Click package was especially useful and resolved some headaches
related to the earlier argparse-based implementation.

Contributing
~~~~~~~~~~~~
Contributions are welcome!  See CONTRIBUTING.rst for contribution instructions.