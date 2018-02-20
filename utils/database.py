# DATABASE UTILITIES
# Why didn't I do this sooner...?

# (c) 2017-2018 ry00001

import rethinkdb as r
import discord
import addict


def check_setting(conn, g, setting):
    exists = (lambda: list(r.table('settings').filter(
        lambda a: a['guild'] == str(g.id)).run(conn)) != [])()
    if not exists:
        return None
    settings = list(r.table('settings').filter(
        lambda a: a['guild'] == str(g.id)).run(conn))[0]
    if setting in settings.keys():
        return settings[setting]
    else:
        return None


def get_settings(conn, g):
    exists = (lambda: list(r.table('settings').filter(
        lambda a: a['guild'] == str(g.id)).run(conn)) != [])()
    if not exists:
        return None
    settings = list(r.table('settings').filter(
        lambda a: a['guild'] == str(g.id)).run(conn))[0]
    return settings


def add_money(conn, user: discord.User, amount: int=10) -> int:
    cursor = r.table('profiles') \
              .filter({'user': user.id}) \
              .update({'money': r.row['money'] + amount}) \
              .run(conn)
    return cursor.next()['money']
