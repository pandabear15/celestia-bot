# Celestia Bot
# Version 1.1.0

import os
import time
import traceback

import discord
from discord.ext import tasks, commands
import json
import datetime

from dotenv import load_dotenv

from message_model import MessageModel
from message_cache import MessageCache


class ExpectedException(Exception):
    pass


version = '1.1.0'

# read config
load_dotenv()
config_file = open('.conf/prod_config.json')
config = json.load(config_file)
token: str = config['token']
server: int = int(config['server'])
admin_role = int(config['admin'])
max_messages: int = int(config['max_messages'])
backlog_length: int = int(config['backlog_length'])
log_channel: int = int(config['log_channel'])
log_history: int = int(config['log_history'])
ignored_categories: list[int] = config['ignored_categories']
read_cache_file: bool = config['read_cache_file']

# cache
message_cache: MessageCache = MessageCache(max_cache_size=max_messages)
i: int = 0

# other variables
pdt = datetime.timezone(-datetime.timedelta(hours=7))
pst = datetime.timezone(-datetime.timedelta(hours=8))
is_setting_up = True
start_time: datetime.datetime | None = None

# bot setup
bot_token: str = os.getenv(token)
bot: commands.Bot = commands.Bot(command_prefix='+', intents=discord.Intents.all(), status=discord.Status.online,
                                 activity=discord.Activity(type=discord.ActivityType.watching,
                                                           name='over the server'))


async def create_delete_log_embed(message: MessageModel) -> discord.Embed:
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

    while True:
        try:
            previous_message: discord.Message = await anext(message_iterator)
            if previous_message.type != discord.MessageType.default:
                continue
            embed.insert_field_at(index=0, name=f'**{previous_message.author.name}**',
                                  value=get_message_content(previous_message),
                                  inline=False)
            if len(previous_message.attachments) > 0:
                embed.insert_field_at(index=1, name='Attachments',
                                      value='\n'.join([attachment.url for attachment in previous_message.attachments]),
                                      inline=False)
            first_message_url = previous_message.jump_url
        except StopAsyncIteration:
            break
    if first_message_url is not None:
        embed.url = first_message_url
    embed.add_field(name=f'Deleted message - {author.name}', value=await get_message_model_content(message),
                    inline=False)
    if len(message.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join(message.attachments), inline=False)
    #    if message.sticker != '':
    #        embed.set_image(url=message.sticker)
    embed.set_footer(text=f'Deleted at {datetime.datetime.now(get_timezone()).isoformat(sep=" ", timespec="seconds")}')
    return embed


async def create_edit_log_embed(before: MessageModel, after: MessageModel) -> discord.Embed:
    author = bot.get_user(after.user_id)
    channel = bot.get_channel(after.channel_id)

    embed_color = discord.Color.dark_gold()
    embed = discord.Embed(
        title='Message edited',
        description=f'**{author.name} edited a message in <#{channel.id}>**',
        color=embed_color)
    embed.set_author(name=f'{author.name}#{author.discriminator} ({author.display_name})',
                     icon_url=author.display_avatar.url)
    embed.url = (await channel.get_partial_message(after.message_id).fetch()).jump_url
    embed.add_field(name=f'**Before**',
                    value=await get_message_model_content(before), inline=False)
    if len(before.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join(before.attachments), inline=False)
    embed.add_field(name=f'**After**', value=await get_message_model_content(after), inline=False)
    if len(after.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join(after.attachments), inline=False)
    #    if before.sticker != '':
    #        embed.set_image(url=before.sticker)
    embed.set_footer(text=f'Edited at {datetime.datetime.now(get_timezone()).isoformat(sep=" ", timespec="seconds")}')
    return embed


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
            print(f'Loaded cache file in {round(get_unix_time(datetime.datetime.now()) - read_cache_time, 3)}s')
        except json.decoder.JSONDecodeError:
            print("Failed to read cache file")
    guild: discord.Guild = bot.get_guild(server)
    time_start = max([datetime.datetime.now(get_timezone()) - datetime.timedelta(days=backlog_length),
                      message_cache.get_max_time(get_timezone())])
    if guild is not None:
        channels = guild.channels
        for channel in channels:
            if channel.type == discord.ChannelType.text and channel.category_id not in ignored_categories:
                print(f'Caching channel {channel.name}')
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
    channel_str = f'{f"From channel {bot.get_channel(message_model.channel_id).name}"}' if message_model is not None else ''
    user_str = f'{f"From user {bot.get_user(message_model.user_id).name}"}' if message_model is not None else ''
    await bot.get_channel(log_channel).send(content=(f'Celestia ran into an error! Please contact the bot dev with '
                                                     f'the following stacktrace: ```{error}'
                                                     f'{message_str}' + '\n'
                                                     f'{channel_str}' + '\n'
                                                     f'{user_str}'
                                                     f'```'))


def get_metrics() -> str:
    length = message_cache.len()
    size = message_cache.__sizeof__()
    ret_str = (f'Cache length: {length} entries' + '\n' + f'Cache size: {size} bytes' + '\n'
               f'Average entry size: {round(size / length, 2)} bytes')
    return ret_str


def get_unix_time(time: datetime.datetime) -> float:
    return datetime.datetime.timestamp(time)


def is_daylight_savings() -> bool:
    return bool(time.localtime().tm_isdst)


def get_timezone() -> datetime.tzinfo:
    return pdt if is_daylight_savings() else pst


def to_json(obj):
    return json.dumps(obj, default=lambda o: o.__dict__, indent=4)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    after_message = None
    try:
        if not is_setting_up:
            after_message = await bot.get_channel(payload.channel_id).get_partial_message(payload.message_id).fetch()
            if after_message.author.bot or after_message.guild.id != server:
                return
            after = MessageModel(after_message)
            before = message_cache.get_message_model(message=after, update=True)
            if before is not None and not before.total_eq(after):
                embed = await create_edit_log_embed(before=before, after=after)
                await bot.get_channel(log_channel).send(embed=embed)
    except:
        await notify_error(traceback.format_exc(limit=None), message_model=after_message)


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
                embed = await create_delete_log_embed(message=message)
                await bot.get_channel(log_channel).send(embed=embed)
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
                print(get_metrics())
    except:
        await notify_error(traceback.format_exc(limit=None), message_model=MessageModel(message))
    await bot.process_commands(message)


@tasks.loop(hours=1)
async def print_cache():
    print_cache_time: float = get_unix_time(datetime.datetime.now())
    cache_file = open(".cache/cache.txt", "w")
    cache_file.write(to_json(message_cache.get_cache()))
    cache_file.close()
    print(f'Wrote to cache at {datetime.datetime.now(tz=get_timezone()).isoformat()}, writing time was '
          f'{round(get_unix_time(datetime.datetime.now()) - print_cache_time, 3)}s')


@bot.command(name='info')
async def get_info(ctx: commands.Context):
    if ctx.message.channel.id == log_channel and ctx.author.get_role(admin_role) is not None:
        content = (f'```Running version {version}' + '\n' + f'Celestia has been running for '
                   f'{str(datetime.datetime.now(get_timezone()) - start_time).split(".")[0]}' + '\n'
                   f'{get_metrics()}```')
        await bot.get_channel(log_channel).send(content=content)


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
        print('We have logged in as {0.user}'.format(bot))
        start_time = datetime.datetime.now(get_timezone())
        populate_time: float = get_unix_time(datetime.datetime.now())
        print('Populating cache')
        await populate_cache()
        print(f'Cache populated in {round(get_unix_time(datetime.datetime.now()) - populate_time, 3)} seconds')
        print_cache.start()
        print(get_metrics())
        await bot.get_channel(log_channel).send(content='Celestia has booted up and is now '
                                                        'monitoring edits and deletions.')
        print('Celestia is ready.')
    except:
        await notify_error(traceback.format_exc(limit=None))


bot.run(bot_token)
