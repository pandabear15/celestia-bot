import os
import time
import traceback

import discord
import json
import datetime

from dotenv import load_dotenv

from message_model import MessageModel
from message_cache import MessageCache

# read config
load_dotenv()
config_file = open('.conf/prod_config.json')
config = json.load(config_file)
server: int = int(config['server'])
max_messages: int = int(config['max_messages'])
backlog_length: int = int(config['backlog_length'])
log_channel: int = int(config['log_channel'])
log_history: int = int(config['log_history'])
ignored_categories: list[int] = config['ignored_categories']

# cache
message_cache: MessageCache = MessageCache(max_cache_size=max_messages)
i: int = 0

# other variables
pdt = datetime.timezone(-datetime.timedelta(hours=7))
pst = datetime.timezone(-datetime.timedelta(hours=8))
is_setting_up = True

# bot setup
bot_token: str = os.getenv('TOKEN')
bot: discord.Client = discord.Client(intents=discord.Intents.all(), status=discord.Status.online,
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
            embed.insert_field_at(index=0, name=previous_message.author.name,
                                  value=previous_message.content,
                                  inline=False)
            first_message_url = previous_message.jump_url
        except StopAsyncIteration:
            break
    if first_message_url is not None:
        embed.url = first_message_url
    embed.add_field(name=f'Deleted message - {author.name}', value=message.content,
                    inline=False)
    if len(message.attachments) > 0:
        embed.add_field(name='Attachments', value='\n'.join(message.attachments), inline=False)
    if message.sticker != '':
        embed.set_image(url=message.sticker)
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
    embed.add_field(name=f'Before',
                    value=before.content, inline=False)
    embed.add_field(name=f'After', value=after.content, inline=False)
    if len(before.attachments) > 0:
        embed.add_field(name='Attachments before edit', value='\n'.join(before.attachments), inline=False)
    if before.sticker != '':
        embed.set_image(url=before.sticker)
    embed.set_footer(text=f'Edited at {datetime.datetime.now(get_timezone()).isoformat(sep=" ", timespec="seconds")}')
    return embed


async def populate_cache():
    global is_setting_up
    guild: discord.Guild = bot.get_guild(server)
    if guild is not None:
        channels = guild.channels
        for channel in channels:
            if channel.type == discord.ChannelType.text and channel.category_id not in ignored_categories:
                print(f'Caching channel {channel.name}')
                message_iterator = channel.history(limit=None,
                                                   after=datetime.datetime.now() - datetime.timedelta(days=backlog_length))
                while True:
                    try:
                        next_message: discord.Message = await anext(message_iterator)
                        message_cache.add_message_model(MessageModel(next_message), append=False)
                    except StopAsyncIteration:
                        break
                    except discord.errors.Forbidden:
                        break
    is_setting_up = False


async def notify_error(error: str):
    print(error)
    await bot.get_channel(log_channel).send(content=(f'Celestia ran into an error! Please contact the bot dev with '
                                                     f'the following stacktrace: ```{error}```'))


def print_metrics():
    length = message_cache.len()
    size = message_cache.__sizeof__()
    print(f'Cache length: {length}')
    print(f'Cache size: {size}')
    print(f'Average entry size: {round(size / length, 2)}')


def get_unix_time() -> float:
    return datetime.datetime.timestamp(datetime.datetime.now())


def is_daylight_savings() -> bool:
    return bool(time.localtime().tm_isdst)


def get_timezone() -> datetime.tzinfo:
    return pdt if is_daylight_savings() else pst


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    try:
        if not is_setting_up:
            after_message = await bot.get_channel(payload.channel_id).get_partial_message(payload.message_id).fetch()
            if after_message.author.bot or after_message.guild.id != server:
                return
            after = MessageModel(after_message)
            before = message_cache.get_message_model(message=after, update=True)
            if before is not None:
                embed = await create_edit_log_embed(before=before, after=after)
                await bot.get_channel(log_channel).send(embed=embed)
    except:
        await notify_error(traceback.format_exc(limit=None))


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    try:
        if not is_setting_up:
            if payload.cached_message is not None:
                if payload.cached_message.author.bot or payload.cached_message.guild.id != server:
                    return
            message = message_cache.get_message_model(MessageModel(message=payload.cached_message, payload=payload))
            if message is not None:
                embed = await create_delete_log_embed(message=message)
                await bot.get_channel(log_channel).send(embed=embed)
    except:
        await notify_error(traceback.format_exc(limit=None))


@bot.event
async def on_message(message: discord.Message):
    global i
    try:
        if (not message.author.bot) and message.guild.id == server and message.channel.category_id not in ignored_categories:
            message_cache.add_message_model(MessageModel(message=message))
            i = i + 1
            if i % 100 == 0:
                print_metrics()
    except:
        await notify_error(traceback.format_exc(limit=None))


@bot.event
async def on_ready():
    try:
        print('We have logged in as {0.user}'.format(bot))
        populate_time = get_unix_time()
        print('Populating cache')
        await populate_cache()
        print(f'Cache populated in {round(get_unix_time() - populate_time, 3)} seconds')
        print_metrics()
        await bot.get_channel(log_channel).send(content='Celestia has booted up and is now '
                                                        'monitoring edits and deletions.')
    except:
        await notify_error(traceback.format_exc(limit=None))


bot.run(bot_token)
