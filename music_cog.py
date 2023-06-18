import asyncio
import datetime
import time
import random
from typing import Optional, Any

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from urllib.parse import urlparse

from song import Song

ytdl_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'default_search': 'auto',
    'quiet': True,
    'no_warnings': True,
    'logtostderr': False,
    'source_address': '0.0.0.0'
}

yt_netloc = ['www.youtube.com', 'youtube.com', 'youtu.be']

num_query_choices = 5

error_actions = ['do ten pushups',
                 'polish your eyes',
                 'do a barrel roll',
                 'rickroll your friend',
                 'touch grass',
                 'twiddle your thumbs',
                 'go to bed']

search_selection = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
playlist_nav_selection = ['⏮', '⏪', '⏩', '⏭']

num_playlist_nav_display = 10


class MusicBot(commands.Cog):
    # TODO: look for async race conditions
    def __init__(self, bot, voice_channel, cmd_channel):
        self.bot: commands.Bot = bot
        self.voice_channel: discord.VoiceChannel = voice_channel  # reference to voice channel
        self.cmd_channel: discord.TextChannel = cmd_channel  # reference to cmd channel
        self.connection: Optional[discord.VoiceClient] = None
        self.controllers: list[discord.Member] = []
        self.public: bool = False
        self.current_song: Optional[Song] = None
        self.current_song_message: Optional[discord.Message] = None
        self.is_stopped: bool = False
        self.playlist: list[Song] = []
        self.playlist_message: dict[str, Any] = {}
        self.repeat: bool = False
        self.queries: dict[discord.Member, tuple[discord.Message, list[Song]]] = {}

    @commands.command()
    async def join(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if ctx.author not in self.voice_channel.members:
                await self._user_error('You are not in the voice channel.', ctx)
            elif self.bot.user in self.voice_channel.members:
                await self._user_error('I am already in the voice channel.', ctx)
            else:
                await self._join(ctx.author)

    @commands.command()
    async def leave(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am already not in the voice chat.', ctx)
            elif self.current_song is not None or len(self.playlist) > 0:
                await self._user_error('Cannot disconnect while there is music to be played.', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error(f'You is not a controller of the music bot.', ctx)
            else:
                await self._reset()
                await self._info(None, 'Successfully disconnected.', ctx)

    @commands.command()
    async def search(self, ctx: commands.Context, *, arg):
        if ctx.channel == self.cmd_channel:
            if len(arg) == 0:
                await self._user_error('I can\'t search for nothing.', ctx)
            else:
                search_result, exec_time = self._ytdlp_search(arg, num_query_choices, ctx)
                if search_result is None:
                    return
                else:
                    song_list = [Song(result, ctx.author) for result in search_result]
                    embed = self._create_search_embed(ctx.author, arg, song_list, exec_time)
                    query_message = await self.cmd_channel.send(embed=embed, reference=ctx.message,
                                                                mention_author=False)
                    self.queries[ctx.author] = (query_message, song_list)
                    for i in range(len(song_list)):
                        await query_message.add_reaction(search_selection[i])

    def _create_search_embed(self, author: discord.Member, query: str, search_result: list[Song],
                             exec_time: float) -> discord.Embed:
        embed = discord.Embed(title=f'Searched for "{query}"', description=f'Query time: {round(exec_time, 3)} seconds',
                              color=author.color)
        embed.set_author(name=f'{author.global_name} ({author.display_name})',
                         icon_url=author.display_avatar.url)
        for i in range(len(search_result)):
            song = search_result[i]
            embed.add_field(name=f'{i + 1}: {song.title}',
                            value=f'Length {str(datetime.timedelta(seconds=song.duration))}, '
                                  f'Uploaded by {song.uploader} on {str(song.upload_date)}',
                            inline=False)
        embed.set_footer(text='React to this message to select a video option above.')
        return embed

    @commands.command()
    async def play(self, ctx: commands.Context, *, arg):
        if ctx.channel == self.cmd_channel:
            if ctx.author not in self.voice_channel.members:
                await self._user_error(error_message='You are not in the voice channel.', ctx=ctx)
            else:
                # attempt to parse as URL
                url = urlparse(arg)
                if url.scheme and url.netloc:
                    if ' ' in arg:
                        await self._user_error('Cannot currently queue multiple videos at the same time.')
                    elif url.netloc not in yt_netloc:
                        await self._user_error('Only YouTube links are currently supported.', ctx)
                    elif url.path != '/watch' and url.netloc != 'youtu.be':
                        await self._user_error('This is not a link to a video on YouTube.')
                    else:  # should be a YouTube video that can be directly searched
                        with YoutubeDL(ytdl_options) as ytdl:
                            try:
                                await self.cmd_channel.typing()
                                info_dict = ytdl.extract_info(url=arg, download=False, process=True)
                                song_result = Song(info_dict, ctx.author)
                            except:
                                await self._user_error('Could not parse your search.', ctx)
                                return
                            await self._add_to_playlist(song_result)
                else:
                    search_result, exec_time = await self._ytdlp_search(arg, 1, ctx)
                    if search_result is None:
                        return
                    else:
                        song_result = Song(search_result[0], ctx.author)
                        await self._add_to_playlist(song_result)

    @commands.command()
    async def playnow(self, ctx: commands.Context, arg: Optional[str] = None):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif arg is None or not arg.isnumeric() or int(arg) <= 0:
                await self._user_error('The playnow command takes a single non-negative integer.', ctx)
            elif int(arg) > len(self.playlist):
                await self._user_error('There aren\'t that many songs in the current queue.', ctx)
            else:
                next_song = self.playlist.pop(int(arg) - 1)
                self.playlist.insert(0, next_song)
                await self._end_song()
                await self._info(None, f'Skipping current song to play {next_song.title}.', ctx)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif self.connection.is_paused():
                await self._user_error('The music is *already* paused.', ctx)
            elif not self.connection.is_playing():
                await self._user_error('There is no music to pause.', ctx)
            else:
                self.connection.pause()
                await self._info(None, 'Music has been paused.', ctx)

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif self.connection.is_paused():
                self.connection.resume()
                await self._info(None, 'Music has been resumed. Happy listening!', ctx)
            elif self.connection.is_playing():
                await self._user_error('Music is already playing.', ctx)
            else:  # music is stopped
                if len(self.playlist) == 0:
                    await self._user_error('There is no music in the queue to play.', ctx)
                else:
                    self.is_stopped = False
                    await self._info(None, 'Music has been restarted. Happy listening!', ctx)
                    await self._play_song()

    @commands.command()
    async def stop(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif self.is_stopped:
                await self._user_error('There is nothing to stop.', ctx)
            else:
                self.is_stopped = True
                self.connection.stop()
                await self._end_song(play_next=False)
                await self._info(None, 'Music has been stopped.', ctx)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            else:
                self.connection.stop()
                await self._end_song()

    @commands.command()
    async def repeat(self, ctx: commands.Context, arg: Optional[str] = None):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            else:
                if arg is None:
                    await self._user_error('Repeat command expects "on" or "off".', ctx)
                elif arg == 'on':
                    self.repeat = True
                    await self._info(None, 'Repeat is now on.', ctx)
                elif arg == 'off':
                    self.repeat = False
                    await self._info(None, 'Repeat is now off.', ctx)
                else:
                    await self._user_error('Repeat command expects "on" or "off".', ctx)

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif len(self.playlist) == 0:
                await self._user_error('There are no songs in the queue to shuffle.', ctx)
            else:
                random.shuffle(self.playlist)
                await self._info(None, 'Queue has been shuffled.', ctx)

    @commands.command()
    async def clear(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            else:
                self.playlist = []
                await self._info(None, 'Queue has been cleared.', ctx)

    @commands.command()
    async def dequeue(self, ctx: commands.Context, arg: Optional[str] = None):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif arg is None or not arg.isnumeric() or int(arg) <= 0:
                await self._user_error('The dequeue command takes a single non-negative integer.', ctx)
            elif int(arg) > len(self.playlist):
                await self._user_error('There isn\'t a song in that position to dequeue.', ctx)
            elif not self._has_control(ctx.author) and ctx.author != self.playlist[int(arg)].queuer:
                await self._user_error('You do not have control over the music bot.', ctx)
            else:
                song = self.playlist.pop(int(arg) - 1)
                await self._info(None, f'Dequeued {int(arg)}: {song.title}.', ctx)

    @commands.command()
    async def control(self, ctx: commands.Context, *args):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif len(args) == 0:  # requesting control
                if ctx.author not in self.voice_channel.members:
                    await self._user_error('You can\'t control the music bot if you are not in the voice channel.', ctx)
                elif self.public:
                    await self._user_error('Bot is public, and everyone in the voice channel has control.', ctx)
                elif len(set(self.voice_channel.members) & set(self.controllers)) > 0:
                    await self._user_error('Someone who already has control must give you control.', ctx)
                else:
                    self.controllers.append(ctx.author)
                    await self._info(None, f'Added {ctx.author.global_name} as a music bot controller.', ctx)
            else:  # giving control
                if self.public:
                    await self._user_error('Bot is public, and everyone in the voice channel has control.', ctx)
                elif ctx.author not in self.controllers:
                    await self._user_error('You do not have control of the music bot.', ctx)
                else:
                    valid_users = []
                    for string in args:
                        user = ctx.guild.get_member_named(string)
                        if user is not None and user in self.voice_channel.members and user not in self.controllers:
                            valid_users.append(f'{user.global_name} ({user.display_name})')
                            self.controllers.append(user)
                    if len(valid_users) == 0:
                        await self._user_error('No valid users in the voice channel matched your request.', ctx)
                    else:
                        nl = '\n'
                        await self._info(None, f'Found the following members and gave them music bot control:'
                                               f'\n{nl.join(valid_users)}')

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def controllers(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif self.public:
                await self._info(None, 'Bot control is public, and everyone in the voice chat is a controller.', ctx)
            else:
                await self._info('Music Bot Controllers',
                                 '\n'.join([f'{member.global_name} '
                                            f'({member.display_name})' for member in self.controllers]), ctx)

    @commands.command()
    async def public(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif not self._has_control(ctx.author):
                await self._user_error('You do not have control over the music bot.', ctx)
            elif self.public:
                await self._user_error('Bot control is already public.', ctx)
            else:
                self.public = True
                await self._info(None, 'Everyone in the voice channel now has control over the bot.')

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def playlist(self, ctx: commands.Context):
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            if len(self.playlist) == 0:
                await self._user_error('Queue is currently empty.', ctx)
            else:
                await self._clear_playlist_nav_message()
                embed = self._create_playlist_embed(requester=ctx.author, page_number=0)  # should never be None
                message = await self.cmd_channel.send(embed=embed, reference=ctx.message, mention_author=False)
                self.playlist_message = {'message': message, 'user': ctx.author, 'page_number': 0}
                for reaction in playlist_nav_selection:
                    await message.add_reaction(reaction)

    def _create_playlist_embed(self, requester: discord.Member, page_number: int) -> Optional[discord.Embed]:
        if len(self.playlist) == 0:
            return discord.Embed(title='Current Queue', description='Nothing here!')
        elif page_number < 0 or page_number * num_playlist_nav_display > len(self.playlist):
            return None
        else:
            max_idx = min(len(self.playlist), (page_number + 1) * num_playlist_nav_display) - 1
            embed = discord.Embed(title='Current Queue',
                                  description=f'Displaying {page_number * num_playlist_nav_display + 1}-'
                                              f'{max_idx + 1} of {len(self.playlist)} song(s),'
                                              f'Total time {str(datetime.timedelta(seconds=self._queue_length()))}',
                                  color=requester.color)
            embed.set_author(name=f'{requester.global_name} ({requester.display_name})',
                             icon_url=requester.display_avatar.url)
            for i in range(page_number * num_playlist_nav_display, max_idx + 1):
                song = self.playlist[i]
                embed.add_field(name=f'{i + 1}: {song.title} by {song.uploader}',
                                value=f'Length {str(datetime.timedelta(seconds=song.duration))}, '
                                      f'Requested by {song.queuer}',
                                inline=False)
            return embed

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def current(self, ctx: commands.Context):
        progress_bar_length = 20
        if ctx.channel == self.cmd_channel:
            if self.connection is None:
                await self._user_error('I am not even in a voice channel!', ctx)
            elif self.current_song is None or self.is_stopped:
                await self._user_error('No song is currently playing.', ctx)
            else:
                queuer = self.current_song.queuer
                song = self.current_song
                sec_elapsed = self.current_song.source.ms_elapsed() // 1000
                elapsed_squares = int(sec_elapsed / song.duration * progress_bar_length)
                embed = discord.Embed(title=song.title, description=f'Uploaded by {song.uploader}',
                                      color=song.queuer.color)
                embed.set_author(name=f'Requested by {queuer.global_name} ({queuer.display_name})',
                                 icon_url=queuer.display_avatar.url)
                progress_bar = ''
                for i in range(progress_bar_length):
                    if i < elapsed_squares:
                        progress_bar += '🟦'
                    else:
                        progress_bar += '⬜'
                embed.add_field(name=f'Elapsed: {str(datetime.timedelta(seconds=sec_elapsed))}',
                                value=f'0:00:00 {progress_bar} {str(datetime.timedelta(seconds=song.duration))}',
                                inline=False)
                embed.add_field(name='\u200b', value=f'[Link to video](https://www.youtube.com/watch?v={song.id})',
                                inline=False)
                await self.cmd_channel.send(embed=embed, reference=ctx.message, mention_author=False)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction,
                              user: discord.Member):
        message = reaction.message
        if message.channel == self.cmd_channel and user != self.bot.user:
            # selecting a song from a search prompt
            if user in self.queries.keys() and message == self.queries[user][0]:
                if user not in self.voice_channel.members:
                    await self._user_error('Only voice channel participants can add songs.', user=user)
                song_list = self.queries[user][1]
                if reaction.emoji.__str__() in search_selection:
                    idx = search_selection.index(reaction.emoji.__str__())
                    if idx < len(song_list):
                        del self.queries[user]
                        await message.clear_reactions()
                        await self._add_to_playlist(song_list[idx])
            # selecting playlist navigation
            elif len(self.playlist_message.keys()) > 0 and user == self.playlist_message['user'] \
                    and reaction.emoji.__str__() in playlist_nav_selection:
                if reaction.emoji.__str__() == '⏮':
                    page_num = 0
                elif reaction.emoji.__str__() == '⏪':
                    page_num = max(0, self.playlist_message['page_number'] - 1)
                elif reaction.emoji.__str__() == '⏩':
                    page_num = min((len(self.playlist) - 1) // num_playlist_nav_display,
                                   self.playlist_message['page_number'] + 1)
                else:  # elif reaction.emoji.__str__() == '⏭':
                    page_num = (len(self.playlist) - 1) // num_playlist_nav_display
                await self._edit_playlist_nav_message(page_num, reaction.emoji.__str__())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if len(self.voice_channel.members) == 1 and self.bot.user in self.voice_channel.members:
            await self._reset()
            await self._info(None, 'Disconnected from the voice channel due to being empty.')
        elif member not in self.voice_channel.members and member in self.controllers:
            self.controllers.remove(member)

    async def _join(self, user: discord.Member):
        self.controllers.append(user)
        self.connection = await self.voice_channel.connect(self_deaf=True)

    async def _ytdlp_search(self, query: str, num_search: int, ctx: commands.Context) -> tuple[Optional[dict], float]:
        with YoutubeDL(ytdl_options) as ytdl:
            try:
                await self.cmd_channel.typing()
                start = time.time()
                search_result = ytdl.extract_info(f'ytsearch{num_search}:{query}', download=False,
                                                  process=True)['entries']
                exec_time = time.time() - start
                return search_result, exec_time
            except:
                await self._user_error('Could not parse your search.', ctx)
                return None, -1

    async def _add_to_playlist(self, song: Song):
        await self._info(None, f'Added {song.title} by {song.uploader} to the queue.',
                         user=song.queuer)
        self.playlist.append(song)
        if self.current_song is None:
            await self._play_song()

    async def _delete_current_song_message(self):
        await self.current_song_message.delete()
        self.current_song_message = None

    async def _edit_playlist_nav_message(self, page_number: int, reaction: str):
        message = self.playlist_message['message']
        embed = self._create_playlist_embed(self.playlist_message['user'], page_number)
        new_message = await message.edit(embed=embed)
        try:
            await message.remove_reaction(reaction, self.playlist_message['user'])
        except:
            pass
        self.playlist_message['message'] = new_message
        self.playlist_message['page_number'] = page_number

    async def _clear_playlist_nav_message(self):
        if self.playlist_message != {}:
            await self.playlist_message['message'].clear_reactions()
            self.playlist_message = {}

    async def _play_song(self):
        self.current_song = self.playlist.pop(0)
        source = self.current_song.source
        if self.connection is None:
            await self._join(self.current_song.queuer)
        self.connection.play(source,
                             after=lambda e: asyncio.run_coroutine_threadsafe(self._end_song(), self.bot.loop))
        embed = discord.Embed(title=f'Now playing {self.current_song.title} by {self.current_song.uploader}',
                              description=f'Requested by {self.current_song.queuer}, '
                                          f'Length {str(datetime.timedelta(seconds=self.current_song.duration))}',
                              color=self.current_song.queuer.color)
        self.current_song_message = await self.cmd_channel.send(embed=embed)

    async def _end_song(self, play_next: bool = True):
        if self.current_song_message is not None:
            await self._delete_current_song_message()
        if self.repeat and self.current_song is not None:
            self.current_song.refresh_source()
            self.playlist.append(self.current_song)
        self.current_song = None
        if not self.is_stopped and play_next and len(self.playlist) > 0:
            asyncio.run_coroutine_threadsafe(self._play_song(), self.bot.loop)

    def _has_control(self, user: discord.User):
        return self.public or user in self.controllers

    def _queue_length(self) -> int:
        length = 0
        for song in self.playlist:
            length += song.duration
        return length

    async def _reset(self):
        if self.connection is not None:
            await self._end_song()
            await self.connection.disconnect()
            self.connection = None
        self.controllers = []
        self.public = False
        self.current_song = None
        self.current_song_message = None
        self.is_stopped = False
        self.playlist = []
        self.playlist_message = {}
        self.repeat = False
        self.queries = {}

    async def _user_error(self, error_message: str, ctx: Optional[commands.Context] = None,
                          user: Optional[discord.Member] = None):
        random_error = random.choice(error_actions)
        error_message = error_message + f' Please {random_error} and try again.'
        embed = discord.Embed(title='Error!', color=discord.Color.red(), description=error_message)
        if ctx is not None:
            author = ctx.author
            message_call = ctx.message
            embed.set_author(name=f'{author.global_name} ({author.display_name})',
                             icon_url=author.display_avatar.url)
        elif user is not None:
            message_call = None
            embed.set_author(name=f'{user.global_name} ({user.display_name})',
                             icon_url=user.display_avatar.url)
        else:
            message_call = None
        await self.cmd_channel.send(embed=embed, reference=message_call, mention_author=False)

    async def _info(self, title: Optional[str], info_message: str, ctx: Optional[commands.Context] = None,
                    user: Optional[discord.Member] = None):
        embed = discord.Embed(title=title, description=info_message, color=discord.Color.blue())
        if ctx is not None:
            author = ctx.author
            message_call = ctx.message
            embed.set_author(name=f'{author.global_name} ({author.display_name})',
                             icon_url=author.display_avatar.url)
        elif user is not None:
            message_call = None
            embed.set_author(name=f'{user.global_name} ({user.display_name})',
                             icon_url=user.display_avatar.url)
        else:
            message_call = None
        await self.cmd_channel.send(embed=embed, reference=message_call, mention_author=False)
