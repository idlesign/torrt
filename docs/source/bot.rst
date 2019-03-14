Telegram Bot
============

You can add new torrents via Telegram bot.


Register bot
------------

1. Register your bot with BotFather as described in https://core.telegram.org/bots#6-botfather

.. note::

    If you have already configured notifications with Telegram you don't need create a new bot. Use an existing one.

2. Install ``python-telegram-bot`` library to your python environment with

    .. code-block:: shell

        $ pip install python-telegram-bot

    You may install **torrt** with required dependencies with:

    .. code-block:: shell

        $ pip install torrt[telegram]

3. Configure **torrt** to use the bot:

    .. code-block:: shell

        $ torrt configure_bot telegram token=YOUR_TOKEN

    Restricts users (comma-separated) talking to the bot with option ``allowed_users``:

    .. code-block:: shell

        $ torrt configure_bot telegram token=YOUR_TOKEN allowed_users=user1,user2

4. Create a new Telegram group and add the bot.


Listen to commands
------------------

Start listening to user commands:

.. code-block:: shell

    $ torrt run_bots


Now your bot is ready to accept messages and fully functional.

.. note::

    It is recommended to start ``run_bots`` process using a process management system (see ``supervisord`` configuration example below).


Talking to the bot
------------------

Bot supports a number of commands.

1. To start new conversation with bot use command::

    /start

  and follow further instructions. You can add new, list or remove already registered torrents.

  .. note::
    If you want to cancel current operation use `/cancel` command.

2. Add a torrent using ``/add`` command (torrent is downloaded to a default directory.)::

    /add https://rutracker.org/forum/viewtopic.php?t=1234567


3. All registered torrents can be viewed with::

   /list

4. To remove torrent use command::

    /remove

5. To show all available commands use::

    /help


Supervisor configuration
------------------------

Here described how to configure and start torrt's Telegram bot with ``supervisord``.

1. Install ``supervisord`` on your host as described at http://supervisord.org/installing.html
2. Create configuration file ``torrt.conf`` at ``/etc/supervisor/conf.d/``:

    .. code-block:: ini

        [program:torrt]
        directory=/tmp
        command=PATH_TO_TORRT_SCRIPT run_bots
        user=USER_ON_HOST
        autostart=true
        autorestart=true


  Replace ``PATH_TO_TORRT_SCRIPT`` with a location of **torrt** executable file and ``USER_ON_HOST`` with a user starting a process.

3. Start process with following commands:

    .. code-block:: shell

        # supervisorctl reread
        # supervisorctl reload
        # supervisorctl start torrt

