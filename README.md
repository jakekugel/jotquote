# jotquote

[![PyPI version](https://img.shields.io/pypi/v/jotquote)](https://pypi.org/project/jotquote/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)
[![Python versions](https://img.shields.io/pypi/pyversions/jotquote)](https://pypi.org/project/jotquote/)
[![CI](https://github.com/jakekugel/jotquote/actions/workflows/ci.yml/badge.svg)](https://github.com/jakekugel/jotquote/actions/workflows/ci.yml)

jotquote is a command-line tool for building a collection of quotes,
and it includes a simple web server to display a quote of the day.
The quotes are stored in a single text file in a human-friendly syntax,
one per line.  100 famous quotes are included with the package, and
it is easy to get started:

```bash
$ pip install jotquote
$ jotquote
The best way out is always through.  - Robert Frost
```

Although there are 100 quotes included with the package, the purpose of
jotquote is to help you build a collection of your own favorite quotes.  Adding
new quotes is easy:

```bash
$ jotquote add "The larger the island of knowledge, the longer the shoreline of wonder. - James Madison"
1 quote added for total of 639 quotes.
```

## Starting the web server

In some cases, the command-line might be good enough for viewing the quotes in your
collection, but you can start a web server that will show a quote of the day.  The simplest way to start the web server is with the built-in command:

```bash
$ jotquote webserver
```

By default, the web server is only accessible on the system on which
it is running.  But by editing the settings.conf file, the web server can be
made accessible to computers on the network also.  See [DOCUMENTATION.md](DOCUMENTATION.md) for details.

## The quote file

jotquote stores the quotes in a text file that uses a human-friendly syntax
and can be modified with a plain text editor if necessary.  Quotes are stored
in the text file one per line using the syntax:

```
<quote> | <author> | <publication> | <tag1, tag2, etc...>
```

For example:

```
The best way out is always through. | Robert Frost | A Servant to Servants | motivational, poetry
```

You can find the location of the quote file using the `jotquote info` command,
and you can change the location by modifying the `quote_file` property in
settings.conf.

The text file is encoded in UTF-8 to allow the full Unicode character set.

## Extended functions

To help you build your collection, the command-line interface has an extended set
of functions including tagging and keyword searching.  Here are a couple of examples.
To display a random quote that has the 'motivational' tag, use the command:

```bash
$ jotquote random -t motivational
```

Or to display all quotes that have the word 'Einstein' in the quote, author name,
or publication name, use this command:

```bash
$ jotquote list -k Einstein
```

The help for these extended functions can be accessed with the `-h` argument;
for example, to see the help for the jotquote add function, use
the command:

```bash
$ jotquote add -h
```

## The settings.conf file

The behavior of the jotquote command is controlled with the settings.conf
file.  This file is always found at `~/.jotquote/settings.conf` on Windows, Mac,
and Linux.  See [DOCUMENTATION.md](DOCUMENTATION.md) for the full table of available properties.

## Supported environments

jotquote is tested on Python 3.9 through 3.14 on Windows, Mac, and Linux.

## Additional documentation

[DOCUMENTATION.md](DOCUMENTATION.md) contains full reference documentation for the package, including:

- Complete CLI command reference with all options and examples
- The quotemap feature for scheduling specific quotes on specific dates
- The review app for managing quote tags from a browser
- Full settings.conf property reference

## Credit

This package was inspired by other similar utilities including Ken Arnold's original
UNIX utility `fortune`.  This package also relies on the Flask and Click packages
by Armin Ronacher.

## Contributing

Contributions are welcome, see [DEVELOPMENT.md](DEVELOPMENT.md) for details.

## License

MIT — see [LICENSE.txt](LICENSE.txt) for details.
