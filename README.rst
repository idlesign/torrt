torrt
=====
https://github.com/idlesign/torrt

.. image:: https://img.shields.io/pypi/v/torrt.svg
    :target: https://pypi.python.org/pypi/torrt

.. image:: https://img.shields.io/pypi/l/torrt.svg
    :target: https://pypi.python.org/pypi/torrt

.. image:: https://img.shields.io/coveralls/idlesign/torrt/master.svg
    :target: https://coveralls.io/r/idlesign/torrt

.. image:: https://img.shields.io/travis/idlesign/torrt/master.svg
    :target: https://travis-ci.org/idlesign/torrt

.. image:: https://landscape.io/github/idlesign/torrt/master/landscape.svg?style=plastic
   :target: https://landscape.io/github/idlesign/torrt/master


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
* AniLibria - https://www.anilibria.tv/
* NNM-Club - http://nnm-club.me/
* Kinozal - http://kinozal.tv/

**torrt** is able to cooperate with the following torrent clients:

* Transmission (using built-in JSON RPC)
* Deluge (using `deluge-webapi` plugin - https://github.com/idlesign/deluge-webapi)
* uTorrent (using built-in RPC)
* qBittorrent (using built-in RPC)

**torrt** is able to send update notifications using:

* E-Mail (SMTP)
* Telegram (via Telegram Bot API) - https://core.telegram.org/bots/api

**torrt** can function both as a console application and Python module.


Documentation
-------------

http://torrt.readthedocs.org/
