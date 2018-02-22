# DATABASE UTILITIES
# Why didn't I do this sooner...?

# (c) 2017-2018 ry00001

import rethinkdb as r
import discord


def edit_money(conn, user: discord.User, amount):
    r.table('profiles') \
     .get_all(str(user.id), index='user') \
     .update({'money': r.row['money'] + amount}) \
     .run(conn)
