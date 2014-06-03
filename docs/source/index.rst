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

**torrt** can function both as a console application and Python module.


Requirements
------------

1. Python 2.7+
2. `libtorrent` Python bindings (`python-libtorrent` package on Debian-based)
3. Requests module
4. Beautiful Soup 4+ module
5. Deluge `deluge-webapi` plugin (to work with Deluge)


Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    quickstart
    commands
    toolbox

