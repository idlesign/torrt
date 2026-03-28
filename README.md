# torrt

https://github.com/idlesign/torrt

[![PyPI version](https://img.shields.io/pypi/v/torrt.svg)](https://pypi.python.org/pypi/torrt)
[![License](https://img.shields.io/pypi/l/torrt.svg)](https://pypi.python.org/pypi/torrt)
[![Coverage](https://img.shields.io/coveralls/idlesign/torrt/master.svg)](https://coveralls.io/r/idlesign/torrt)

## Description

*Automates torrent updates for you.*

**torrt** automatically checks your favourite torrent tracker sites, where torrents are organized as articles (i.e. forum-like tracker),
to verify whether specific torrents have been updated (e.g. torrent bundling some TV-series is updated with a new episode),
and instructs your torrent client to download new files.

**torrt** can function both as a console application and Python module.

### Trackers

Automatic updates are available for:

* [AniDUB](https://tr.anidub.com/)
* [AniLibria](https://www.anilibria.tv/)
* [CasStudio](https://casstudio.tv)
* [Kinozal](https://kinozal.tv/)
* [NNM-Club](https://nnm-club.me/)
* [RUTOR](https://rutor.org/)
* [RuTracker (ex torrents.ru)](https://rutracker.org/)

### Torrent clients

**torrt** is able to cooperate with the following torrent clients:

* Transmission (using built-in JSON RPC)
* Deluge (using [deluge-webapi](https://github.com/idlesign/deluge-webapi) plugin)
* uTorrent (using built-in RPC)
* qBittorrent (using built-in RPC) v4.1+

### Notifications

**torrt** is able to send update notifications using:

* E-Mail (SMTP)
* Telegram (via [Telegram Bot API](https://core.telegram.org/bots/api)) 

### Bots

**torrt** can be managed using messenger's bots:

* Telegram (via [Telegram Bot API](https://core.telegram.org/bots/api))

## Documentation

<https://torrt.readthedocs.io/>
