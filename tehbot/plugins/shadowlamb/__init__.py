# -*- coding: utf-8 -*-
from tehbot.plugins import *
from tehbot.plugins import say, me
import tehbot.plugins as plugins
import irc.client
from tehbot.plugins.shadowlamb.core import *
import tehbot.plugins.shadowlamb.model as model
import threading
import time
from random import randint, random
import gettext
import os.path

t = gettext.translation("Shadowlamb", os.path.dirname(__file__))
_ = t.gettext

class ShadowlambPlugin(StandardPlugin, PrivilegedPlugin):
    """What, you don't know what shadowlamb is??"""

    def __init__(self):
        StandardPlugin.__init__(self)

    def command(self, connection, event, extra, dbconn):
        return "Shadowlamb is teh greatest!"

register_plugin("sl", ShadowlambPlugin())


class ShadowlambHandler(PrefixHandler, AuthedPlugin):
    def command_prefix(self):
        return u'\U0001f44d'
        #return "+"

    def __init__(self):
        PrefixHandler.__init__(self)
        AuthedPlugin.__init__(self)
        self.cmd2action = {
                "start" : self.start,
                "reset" : self.reset,
                "s" : self.status,
                "status" : self.status,
                }
        model.init()

    def postinit(self, dbconn):
        self.quit = False
        self.thread = threading.Thread(target=self.timerfunc)
        self.thread.start()

    def deinit(self, dbconn):
        self.quit = True
        self.thread.join()

    def cmd(self, args):
        return u"\x02%s%s\x02" % (self.command_prefix(), args)

    def sltime(self):
        with model.db_session:
            return model.Shadowlamb[1].time

    def timerfunc(self):
        return
        while not self.quit:
            print "SL Timer"

            nxt = time.time() + 1
            while time.time() < nxt:
                time.sleep(0.1)

    def start(self, connection, event, extra, dbconn):
        with model.db_session:
            genders = [g.name for g in model.Gender.select()]
            races = [r.name for r in model.Race.select(lambda x: not x.is_npc)]

        parser = plugins.ThrowingArgumentParser(prog="start", description=self.__doc__)
        parser.add_argument("gender", metavar="gender", choices=genders, help="gender: %s" % ", ".join(genders))
        parser.add_argument("race", metavar="race", choices=races, help="race: %s" % ", ".join(races))

        try:
            pargs = parser.parse_args(extra["args"])
            if parser.help_requested:
                return parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % exc2str(e)

        def random_birthday(s):
            tm = time.gmtime(s)
            return time.mktime((tm.tm_year, randint(1, 12), randint(1, 31), randint(0, 23), randint(0, 59), randint(0, 61), 0, 1, -1))

        def random_value(val, p):
            rand = 1.0 + p * (2 * random() - 1)
            return val * rand

        with model.db_session:
            if model.Player.get(name=event.source.nick, network_id=self.tehbot.settings.network_id(connection)):
                return "Player exists!"

            network_id = self.tehbot.settings.network_id(connection)
            r = model.Race.get(name=pargs.race)
            p = model.Player(
                    network_id=network_id,
                    name=event.source.nick,
                    gender=model.Gender.get(name=pargs.gender),
                    race=r,
                    birthday = random_birthday(self.sltime() - random_value(r.age, 0.2) * 365 * 24 * 60 * 60),
                    height = random_value(r.height, 0.2),
                    weight = random_value(r.weight, 0.2),
                    options = {},
                    hp = 0,
                    mp = 0,
                    distance = 0,
                    xp = 0,
                    xp_level = 0,
                    karma = 0,
                    bad_karma = 0,
                    level = 0,
                    bounty = 0,
                    bounty_done = 0,
                    quests_done = 0,
                    nuyen = 0,
                    known_words = [],
                    known_spells = [],
                    known_places = "",
                    bank_nuyen = 0,
                    bank_items = "",
                    effects = "",
                    const_vars = "",
                    combat_ai = "",
                    game_ai = "",
                    feelings = model.Feelings(),
                    attributes = model.Attributes(),
                    skills = model.Skills(),
                    properties = model.Properties(),
                    knowledge = model.Knowledge(),
                    lock = 0,
                    transport = 0,
                    stats = model.PlayerStats()
                    )
            p.init_player()

        return _("Player created!")

    def reset(self, connection, event, extra, dbconn):
        parser = plugins.ThrowingArgumentParser(prog="reset")
        parser.add_argument("confirmation", nargs="?")

        try:
            pargs = parser.parse_args(extra["args"])
            if parser.help_requested:
                return parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % exc2str(e)

        with db_session:
            p = model.Player.get(name=event.source.nick, network_id=self.tehbot.settings.network_id(connection))
            if p is None:
                return "You haven't started the game yet. Type \x02%sstart\x02 to begin playing." % self.command_prefix()

            if not pargs.confirmation or "".join(pargs.confirmation) != "i_am_sure":
                return "This will completely delete your character. Type \x02%sreset i_am_sure\x02 to confirm." % self.command_prefix()

            p.delete()
            return "Your character has been deleted. You may issue %s again." % self.cmd("start")

    def status(self, connection, event, extra, dbconn):
        with model.db_session:
            p = model.Player.get(name=event.source.nick)

            if p is None:
                return u"Player not created yet. Try %sstart" % self.command_prefix()

            # male troll L0(0). HP:35/35, Atk:22.8, Def:0.1, Dmg:1.8-7.5, Arm(M/F):0/0, XP:0, Karma:0, ¥:50, Weight:0g/18.5kg.
            # female fairy L0(0). HP:10/10, MP:36/36, Atk:2.8, Def:1.5, Dmg:-0.2-2.5, Arm(M/F):0/0, XP:0, Karma:0, ¥:0, Weight:0g/3.5kg.
            return u"%s %s L%d(%d): \x02HP\x02:%.1f/%.1f" % (p.gender.name, p.race.name, p.level, p.effective_level(), p.hp, p.max_hp())

    def execute(self, connection, event, extra, dbconn):
        cmd = extra["cmd"].lower()
        msg_type = "say" if irc.client.is_channel(event.target) else "notice"

        with db_session:
            p = model.Player.get(name=event.source.nick, network_id=self.tehbot.settings.network_id(connection))

        if p is not None and not irc.client.is_channel(event.target):
            msg_type = p.option("msg_type", msg_type)

        if not self.cmd2action.has_key(cmd):
            return [(msg_type, "The command is not available for your current action or location. Try %s to see all currently available commands." % self.cmd("commands [--long]"))]

        if p is None and cmd != "start":
            return [(msg_type, "You haven't started the game yet. Type %s to begin playing." % self.cmd("start"))]

        try:
            return [(msg_type, self.cmd2action[cmd](connection, event, extra, dbconn))]
        except Exception as e:
            import traceback
            traceback.print_exc()
            return [(msg_type, u"Error: %s" % exc2str(e))]

register_prefix_handler(ShadowlambHandler())