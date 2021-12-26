torrt
=====
https://github.com/idlesign/torrt


.. image:: https://img.shields.io/pypi/v/torrt.svg
    :target: https://pypi.python.org/pypi/torrt

.. image:: https://img.shields.io/pypi/l/torrt.svg
    :target: https://pypi.python.org/pypi/torrt

.. image:: https://img.shields.io/coveralls/idlesign/torrt/master.svg
    :target: https://coveralls.io/r/idlesign/torrt


Description
-----------

*Automates torrent updates for you.*

**torrt** automatically checks your favourite torrent tracker sites, where torrents are organized as articles (i.e forum-like tracker),
to verify whether specific torrents have been updated (e.g. torrent bundling some TV-series is updated with a new episode),
and instructs your torrent client to download new files.

**torrt** can function both as a console application and Python module.


Trackers
~~~~~~~~

Automatic updates are available for:

* AniDUB - http://tr.anidub.com/
* AniLibria - https://www.anilibria.tv/
* CasStudio - https://casstudio.tv
* EniaHD - https://eniahd.com
* Kinozal - http://kinozal.tv/
* NNM-Club - http://nnm-club.me/
* RUTOR - http://rutor.org/
* RuTracker (ex torrents.ru) - http://rutracker.org/
* YTS.MX - https://yts.mx/


Torrent clients
~~~~~~~~~~~~~~~

**torrt** is able to cooperate with the following torrent clients:

* Transmission (using built-in JSON RPC)
* Deluge (using `deluge-webapi` plugin - https://github.com/idlesign/deluge-webapi)
* uTorrent (using built-in RPC)
* qBittorrent (using built-in RPC) v4.1+


Notifications
~~~~~~~~~~~~~

**torrt** is able to send update notifications using:

* E-Mail (SMTP)
* Telegram (via Telegram Bot API) - https://core.telegram.org/bots/api


Bots
~~~~

**torrt** can be managed using messenger's bots:

* Telegram  (via Telegram Bot API) - https://core.telegram.org/bots/api



Documentation
-------------

http://torrt.readthedocs.org/
