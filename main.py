# Celestia Bot
# Version 1.2.0

import os
import time
import traceback
from collections import defaultdict, Counter

import discord
from discord.ext import tasks, commands
import json
import logging
import datetime
import random
import numpy as np

import aiohttp
import io

from dotenv import load_dotenv

from message_model import MessageModel
from message_cache import MessageCache


class ExpectedException(Exception):
    pass


version = '1.2.0'

# read config
load_dotenv()
config_file = open('.conf/prod_config.json')
config = json.load(config_file)
token: str = config['token']
celestia_id: int = int(config['celestia_id'])
server: int = int(config['server'])
admin_role = int(config['admin'])
max_messages: int = int(config['max_messages'])
backlog_length: int = int(config['backlog_length'])
log_channel: int = int(config['log_channel'])
dev_channel: int = int(config['dev_channel'])
log_history: int = int(config['log_history'])
ignored_categories: list[int] = config['ignored_categories']
dm_probability: float = config['dm_probability']
read_cache_file: bool = config['read_cache_file']

# cache
message_cache: MessageCache = MessageCache(max_cache_size=max_messages)
i: int = 0

# birthday
birthday_date: datetime.date = datetime.date(year=2022, month=11, day=22)
birthday_channel_id: int = int(config['birthday_channel_id'])
ping_cooldown: datetime.timedelta = datetime.timedelta(minutes=15)
recent_ping_dict: dict[int, datetime.datetime] = defaultdict(lambda: datetime.datetime.min)
recent_ping_list: list = []
recent_ping_list_len: int = 4
tickets: dict = Counter()

# other variables
celestia_caught: int = 1018593299440869487
pdt = datetime.timezone(-datetime.timedelta(hours=7))
pst = datetime.timezone(-datetime.timedelta(hours=8))
is_setting_up = True
start_time: datetime.datetime | None = None
logging.basicConfig(filename='celestia-logs.txt', encoding='utf-8', level=logging.INFO, filemode='w')

# bot setup
bot_token: str = os.getenv(token)
bot: commands.Bot = commands.Bot(command_prefix='+', intents=discord.Intents.all(), status=discord.Status.online,
                                 activity=discord.Activity(type=discord.ActivityType.watching,
                                                           name='over the server'))


async def create_delete_log_embed(message: MessageModel) -> tuple[discord.Embed, list[discord.File]]:
    author = bot.get_user(message.user_id)
    channel = bot.get_channel(message.channel_id)

    message_iterator = channel.history(limit=log_history, before=discord.Object(message.message_id), oldest_first=False)
    embed_color = discord.Color.red()
    embed = discord.Embed(
        title='Message deleted',
        description=f'**{author.name}\'s message was deleted in <#{channel.id}>**',
        color=embed_color)
    embed.set_author(name=f'{author.name}#{author.discriminator} ({author.display_name})',
                     icon_url=author.display_avatar.url)
    first_message_url = None
    files = []

    while True:
        try:
            previous_message: discord.Message = await anext(message_iterator)
            if previous_message.type != discord.MessageType.default:
                continue
            num_fields = insert_embed_text(embed=embed, name=f'**{previous_message.author.name}**',
                                           value=get_message_content(previous_message),
                                           index=0)
            if len(previous_message.attachments) > 0:
                embed.insert_field_at(index=num_fields, name='Attachments',
                                      value='\n'.join([attachment.url for attachment in previous_message.attachments]),
                                      inline=False)

            first_message_url = previous_message.jump_url
        except StopAsyncIteration:
            break
    if first_message_url is not None:
        embed.url = first_message_url
    insert_embed_text(embed=embed, name=f'**Deleted message - {author.name}**',
                      value=await get_message_model_content(message),
                      index=len(embed.fields))
    if len(message.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join([attachment[0] for attachment in message.attachments]), inline=False)
        for index in range(len(message.attachments)):
            ext = MessageModel.is_image(message.attachments[index][0])
            if ext is not None:
                files.append(discord.File(await get_image_bytes(message.attachments[index][0]),
                                          f'Attachment {index + 1}{ext}', spoiler=message.attachments[index][1]))
    embed.set_footer(text=f'Deleted at {datetime.datetime.now(get_timezone()).isoformat(sep=" ", timespec="seconds")}')
    return embed, files


async def create_edit_log_embed(before: MessageModel, after: MessageModel) -> tuple[discord.Embed, list[discord.File]]:
    author = bot.get_user(after.user_id)
    channel = bot.get_channel(after.channel_id)
    files = []

    embed_color = discord.Color.dark_gold()
    embed = discord.Embed(
        title='Message edited',
        description=f'**{author.name} edited a message in <#{channel.id}>**',
        color=embed_color)
    embed.set_author(name=f'{author.name}#{author.discriminator} ({author.display_name})',
                     icon_url=author.display_avatar.url)
    embed.url = (await channel.get_partial_message(after.message_id).fetch()).jump_url
    insert_embed_text(embed=embed, name=f'**Before**',
                      value=await get_message_model_content(before), index=len(embed.fields))
    if len(before.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join([attachment[0] for attachment in before.attachments]), inline=False)
        for index in range(len(before.attachments)):
            ext = MessageModel.is_image(before.attachments[index][0])
            if ext is not None:
                files.append(discord.File(await get_image_bytes(before.attachments[index][0]),
                                          f'Attachment {index + 1}{ext}', spoiler=before.attachments[index][1]))
    insert_embed_text(embed=embed, name=f'**After**',
                      value=await get_message_model_content(after), index=len(embed.fields))
    if len(after.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join([attachment[0] for attachment in after.attachments]), inline=False)
    embed.set_footer(text=f'Edited at {datetime.datetime.now(get_timezone()).isoformat(sep=" ", timespec="seconds")}')
    return embed, files


def insert_embed_text(embed: discord.Embed, name: str, value: str, index: int) -> int:
    max_length = 1024
    string_breakup = []
    while len(value) > max_length:
        rindex = -1
        try:
            rindex = value.rindex(' ', 1, max_length)
        except ValueError:
            pass
        if rindex >= 0:
            string_breakup.append(value[0:rindex])
            value = value[rindex+1:]
        else:
            string_breakup.append(value[0:max_length])
            value = value[max_length:]
    string_breakup.append(value)
    for j in range(len(string_breakup)):
        if j == 0:
            embed.insert_field_at(index=index + j, name=name, value=string_breakup[j], inline=False)
        else:
            embed.insert_field_at(index=index + j, name='\u200b', value=string_breakup[j], inline=False)
    return len(string_breakup)


async def get_message_model_content(message: MessageModel) -> str:
    return message.content + ('' if message.sticker == 0 else f'\n:{await bot.fetch_sticker(message.sticker)}:')


def get_message_content(message: discord.Message) -> str:
    return ((message.content if message.content != '' else "*[Empty message body]*") +
            ('' if len(message.stickers) == 0 else f'\n:{message.stickers[0].name}:'))


async def populate_cache():
    global is_setting_up, message_cache
    if read_cache_file:
        try:
            read_cache_time: float = get_unix_time(datetime.datetime.now())
            cache_file = open(".cache/cache.txt")
            cache_object = json.load(cache_file)
            message_cache = MessageCache(max_cache_size=max_messages, cache=cache_object)
            print_to_bot_logs(f'Loaded cache file in '
                              f'{round(get_unix_time(datetime.datetime.now()) - read_cache_time, 3)}s')
        except json.decoder.JSONDecodeError:
            print_to_bot_logs("Failed to read cache file")
    guild: discord.Guild = bot.get_guild(server)
    if guild is not None:
        channels = guild.channels
        for channel in channels:
            if channel.type == discord.ChannelType.text and channel.category_id not in ignored_categories:
                time_start = max([datetime.datetime.now(get_timezone()) - datetime.timedelta(days=backlog_length),
                                  message_cache.get_max_time(channel_id=channel.id, tzinfo=get_timezone())])
                print_to_bot_logs(f'Caching channel {channel.name}')
                message_iterator = channel.history(limit=None, after=time_start)
                while True:
                    try:
                        next_message: discord.Message = await anext(message_iterator)
                        if not next_message.author.bot and next_message.type == discord.MessageType.default:
                            message_cache.add_message_model(MessageModel(next_message), append=False)
                    except StopAsyncIteration:
                        break
                    except discord.errors.Forbidden:
                        break
    is_setting_up = False


async def notify_error(error: str, message_model: MessageModel = None):
    print(error)
    message_str = f'{f"From message id {message_model.message_id}"}' if message_model is not None else ''
    channel_str = (f'{f"From channel {bot.get_channel(message_model.channel_id).name}"}'
                   if message_model is not None else '')
    user_str = f'{f"From user {bot.get_user(message_model.user_id).name}"}' if message_model is not None else ''
    log = await bot.get_channel(log_channel).send(content=(f'Celestia ran into an error! Please contact the bot dev '
                                                           f'with the following stacktrace: ```{error}'
                                                           f'{message_str}' + '\n'
                                                           f'{channel_str}' + '\n'
                                                           f'{user_str}'
                                                           f'```'))
    await log.add_reaction('✉')


async def send_dm_message(user_id: int):
    if random.random() < dm_probability:
        user: discord.User = bot.get_user(user_id)
        await user.send(content='https://media.discordapp.net/stickers/1018593299440869487.webp?size=160')


async def get_image_bytes(proxy_url: str) -> io.BytesIO | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(proxy_url) as resp:
            if resp.status != 200:
                return None
            data = io.BytesIO(await resp.read())
            return data


def print_to_bot_logs(log: str):
    print(log)
    logging.info(log)


def get_metrics() -> str:
    length = message_cache.len()
    size = message_cache.__sizeof__()
    ret_str = (f'Cache length: {length} entries' + '\n' + f'Cache size: {size} bytes' + '\n'
               f'Average entry size: {round(size / length, 2)} bytes')
    return ret_str


def get_unix_time(date_time: datetime.datetime) -> float:
    return datetime.datetime.timestamp(date_time)


def is_daylight_savings() -> bool:
    return bool(time.localtime().tm_isdst)


def get_timezone() -> datetime.tzinfo:
    return pdt if is_daylight_savings() else pst


def to_json(obj):
    return json.dumps(obj, default=lambda o: o.__dict__, indent=4)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    after = None
    try:
        if not is_setting_up:
            after_message = await bot.get_channel(payload.channel_id).get_partial_message(payload.message_id).fetch()
            if after_message.author.bot or after_message.guild.id != server:
                return
            after = MessageModel(after_message)
            before = message_cache.get_message_model(message=after, update=True)
            if before is not None and not before.total_eq(after):
                embed, attachments = await create_edit_log_embed(before=before, after=after)
                log = await bot.get_channel(log_channel).send(embed=embed)
                await log.add_reaction('✉')
                if len(attachments) > 0:
                    await bot.get_channel(log_channel).send(files=attachments)
                await send_dm_message(after.user_id)
    except:
        await notify_error(traceback.format_exc(limit=None), message_model=after)


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    message = None
    try:
        if not is_setting_up:
            if payload.cached_message is not None:
                if payload.cached_message.author.bot or payload.cached_message.guild.id != server:
                    return
            message = message_cache.get_message_model(MessageModel(message=payload.cached_message, payload=payload),
                                                      delete=True)
            if message is not None:
                embed, attachments = await create_delete_log_embed(message=message)
                log = await bot.get_channel(log_channel).send(embed=embed)
                await log.add_reaction('✉')
                if len(attachments) > 0:
                    await bot.get_channel(log_channel).send(files=attachments)
                await send_dm_message(message.user_id)
    except:
        await notify_error(traceback.format_exc(limit=None), message_model=message)


@bot.event
async def on_message(message: discord.Message):
    global i
    try:
        if ((not message.author.bot) and message.guild.id == server
                and message.channel.category_id not in ignored_categories
                and message.type == discord.MessageType.default):
            message_cache.add_message_model(MessageModel(message=message))
            i = i + 1
            if i % 100 == 0:
                print_to_bot_logs(get_metrics())
        await ping_giveaway(message)
    except:
        await notify_error(traceback.format_exc(limit=None), message_model=MessageModel(message))
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if (reaction.message.channel.id == log_channel and reaction.message.author.id == celestia_id
            and user.id != celestia_id
            and bot.get_guild(server).get_member(user.id).get_role(admin_role) is not None
            and reaction.emoji.__str__() == '✉'):
        async for user in reaction.users():
            if user.id == bot.user.id:
                await reaction.message.remove_reaction('✉', bot.user)
                await reaction.message.add_reaction('📮')
                content = reaction.message.content
                embeds = reaction.message.embeds
                await bot.get_channel(dev_channel).send(content=content, embeds=embeds)


@tasks.loop(hours=1)
async def print_cache():
    print_cache_time: float = get_unix_time(datetime.datetime.now())
    cache_file = open(".cache/cache.txt", "w")
    cache_file.write(to_json(message_cache.get_cache()))
    cache_file.close()
    print_to_bot_logs(f'Wrote to cache at {datetime.datetime.now(tz=get_timezone()).isoformat()}, writing time was '
                      f'{round(get_unix_time(datetime.datetime.now()) - print_cache_time, 3)}s')


async def ping_giveaway(message: discord.Message):
    if message.channel.id == birthday_channel_id and 250052006482280449 in [member.id for member in message.mentions]:
        if not message.author.bot and message.created_at.astimezone(tz=get_timezone()).date() == birthday_date:
            member = message.author
            if (member.id not in recent_ping_list or
                    datetime.datetime.now(tz=get_timezone()) - recent_ping_dict[member.id] >= ping_cooldown):
                if len(recent_ping_list) >= recent_ping_list_len:
                    recent_ping_list.pop(0)
                recent_ping_list.append(member.id)
                recent_ping_dict[member.id] = datetime.datetime.now(tz=get_timezone())
                tickets[member.id] += 1
                await message.add_reaction('🎫')


@bot.command(name='giveaway')
async def get_giveaway_dict(ctx: commands.Context):
    if ctx.message.channel.id == log_channel and ctx.author.get_role(admin_role) is not None:
        try:
            if datetime.date.today() > birthday_date:
                if len(tickets.keys()) == 0:
                    log = await bot.get_channel(log_channel).send(
                        content='No one participated in the giveaway.')
                    await log.add_reaction('✉')
                else:
                    ticket_list: np.ndarray = np.array(list(tickets.items()))
                    ticket_list = ticket_list[ticket_list[:, 1].argsort()]
                    string_list = []
                    for pair in ticket_list:
                        member = bot.get_guild(server).get_member(pair[0])
                        if member is not None:
                            string_list.append(f'{member.name}#{member.discriminator}: {pair[1]}')
                    log = await bot.get_channel(log_channel).send(content='Giveaway results:\n' + '\n'.join(string_list))
                    await log.add_reaction('✉')
            elif datetime.date.today() == birthday_date:
                log = await bot.get_channel(log_channel).send(content='Giveaway is ongoing.')
                await log.add_reaction('✉')
            else:
                log = await bot.get_channel(log_channel).send(content='Giveaway has not started.')
                await log.add_reaction('✉')
        except:
            await notify_error(traceback.format_exc(limit=None))


@bot.command(name='status', aliases=['info'])
async def get_info(ctx: commands.Context):
    if ctx.message.channel.id == log_channel and ctx.author.get_role(admin_role) is not None:
        content = (f'```Running version {version}' + '\n' + f'Celestia has been running for '
                   f'{str(datetime.datetime.now(get_timezone()) - start_time).split(".")[0]}' + '\n'
                   f'{get_metrics()}```')
        log = await bot.get_channel(log_channel).send(content=content)
        await log.add_reaction('✉')


@bot.command(name='error')
async def raise_error(ctx: commands.Context):
    if ctx.message.channel.id == log_channel and ctx.author.get_role(admin_role) is not None:
        try:
            raise ExpectedException("This exception is expected.")
        except ExpectedException:
            await notify_error(traceback.format_exc(limit=None), message_model=MessageModel(ctx.message))


@bot.event
async def on_ready():
    global start_time
    try:
        print_to_bot_logs('We have logged in as {0.user}'.format(bot) + '\n')
        start_time = datetime.datetime.now(get_timezone())
        populate_time: float = get_unix_time(datetime.datetime.now())
        print_to_bot_logs('Populating cache\n')
        await populate_cache()
        caching_time = round(get_unix_time(datetime.datetime.now()) - populate_time, 3)
        print_to_bot_logs(f'Cache populated in {caching_time} '
                          f'seconds\n')
        print_cache.start()
        print_to_bot_logs(get_metrics())
        msg = await bot.get_channel(log_channel).send(content=f'Celestia has booted up and is now monitoring '
                                                              f'edits and deletions. Caching time: {caching_time} sec')
        await msg.add_reaction('✉')
        print_to_bot_logs('Celestia is ready.\n')
    except:
        await notify_error(traceback.format_exc(limit=None))


bot.run(bot_token)
