Telegram Bot
============

You can add new torrents with Telegram bot. Here described how to configure and run it.

Register bot
------------
1. Register your bot with BotFather as described at https://core.telegram.org/bots#6-botfather

.. note::

    If you have already configured notifications with Telegram you don't need create new bot. You can use existing.

2. Add bot to your torrt configuration with command::

    > torrt configure_bot token=YOUR_TOKEN

   You can limit users who can talk to bot with option *allowed_users*. Possible to set several usernames joined by comma. For example::

    > torrt configure_bot token=YOUR_TOKEN allowed_users=user1,user2

3. Create new Telegram group and add bot.

Start bot
---------
To start bot in current tty you can use command::

    > torrt run_bots

Now your bot is ready to accept messages and fully functional. But It is recommended to start process with any process
management system. Example of configuration with supervisord available at the end of this page.


Usage
-----
Bot have several commands.

1. To quickly add torrent just send message to Telegram group with your bot::

    /add https://rutracker.org/forum/viewtopic.php?t=1234567

Torrent would be downloaded from provided link to default directory.

2. If you want to download torrent to another directory please start new conversation with command::

    /start

and follow further instructions.

Supervisor configuration
------------------------
Here described how to configure and start torrt's Telegram bot with supervisor

1. Install supervisor on your host as described at http://supervisord.org/installing.html
2. Create configuration file torrt.conf at */etc/supervisor/conf.d/* with following content::

    [program:torrt]
    directory=/tmp
    command=PATH_TO_TORRT_SCRIPT run_bots
    user=USER_ON_HOST
    autostart=true
    autorestart=true

Replace *PATH_TO_TORRT_SCRIPT* with location of torrt executable file and *USER_ON_HOST* with user who start process

3. Start process with following commands::

    # supervisorctl reread
    # supervisorctl reload
    # supervisorctl start torrt

