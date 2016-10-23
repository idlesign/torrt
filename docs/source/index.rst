torrt documentation
===================
https://github.com/idlesign/torrt



Description
-----------

*Automates torrent updates for you.*

**torrt** automatically checks your favourite torrent tracker sites, where torrents are organized as articles (i.e forum-like tracker),
to verify whether specific torrents have been updated (e.g. torrent bundling some TV-series is updated with a new episode),
and instructs your torrent client to download new files.

Automatic updates are available for:

* RuTracker (ex torrents.ru) - http://rutracker.org/
* RUTOR - http://rutor.org/
* AniDUB - http://tr.anidub.com/
* NNM-Club - http://nnm-club.me/

**torrt** is able to cooperate with the following torrent clients:

* Transmission (using built-in JSON RPC)
* Deluge (using `deluge-webapi` plugin - https://github.com/idlesign/deluge-webapi)
* uTorrent (using built-in RPC)

**torrt** is able to send notifications about downloaded files with:

* Mail (using SMTP server)
* Telegram (using telegram bot API) - https://core.telegram.org/bots/api


**torrt** can function both as a console application and Python module.


Requirements
------------

1. Python 2.7+
2. `libtorrent` Python bindings (`python-libtorrent` package on Debian-based)
3. `Requests` module
4. `Beautiful Soup` 4+ module
5. `lxml` module.
6. Deluge `deluge-webapi` plugin (to work with Deluge)


Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    quickstart
    commands
    toolbox


Get involved into torrt
-----------------------

**Submit issues.** If you spotted something weird in application behavior or want to propose a feature you can do that at https://github.com/idlesign/torrt/issues

**Write code.** If you are eager to participate in application development, fork it at https://github.com/idlesign/torrt, write your code, whether it should be a bugfix or a feature implementation, and make a pull request right from the forked project page.

**Spread the word.** If you have some tips and tricks or any other words in mind that you think might be of interest for the others — publish it.
