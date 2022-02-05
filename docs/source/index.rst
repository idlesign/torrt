torrt documentation
===================
https://github.com/idlesign/torrt



Description
-----------

*Automates torrent updates for you.*

**torrt** automatically checks your favourite torrent tracker sites, where torrents
are organized as articles (i.e forum-like tracker), to verify whether specific torrents have been updated
(e.g. torrent bundling some TV-series is updated with a new episode), and instructs your torrent client
to download new files.

**torrt** can function both as a console application and Python module.


Trackers
~~~~~~~~

Automatic updates are available for:

* AniDUB - http://tr.anidub.com/
* AniLibria - https://www.anilibria.tv/
* CasStudio - https://casstudio.tv
* Kinozal - http://kinozal.tv/
* NNM-Club - http://nnm-club.me/
* RUTOR - http://rutor.org/
* RuTracker (ex torrents.ru) - http://rutracker.org/


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


Requirements
------------

1. Python 3.7+
2. ``deluge-webapi`` plugin (to work with Deluge)
3. ``python-telegram-bot`` (to run Telegram bot)


Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    quickstart
    commands
    toolbox
    bot


Get involved into torrt
-----------------------

**Submit issues.** If you spotted something weird in application behavior or want to propose a feature you can do that
at https://github.com/idlesign/torrt/issues

**Write code.** If you are eager to participate in application development, fork it at
https://github.com/idlesign/torrt, write your code, whether it should be a bugfix or a feature implementation,
and make a pull request right from the forked project page.

**Spread the word.** If you have some tips and tricks or any other words in mind that you think might be of interest
for the others — publish it.
