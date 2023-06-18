import datetime
import discord
from tracked_audio_source import TrackedAudioSource

ffmpeg_options = {
    'executable': 'ffmpeg.exe',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class Song:
    def __init__(self, info_dict: dict, queuer: discord.Member):
        self.id: str = info_dict['id']
        self.title: str = info_dict['title']
        self.uploader: str = info_dict['uploader']
        self.duration: int = int(info_dict['duration'])
        self.upload_date: datetime.date = datetime.datetime.strptime(info_dict['upload_date'], '%Y%m%d').date()
        self.queuer: discord.Member = queuer
        self.source_url = info_dict['url']
        self.source: TrackedAudioSource = TrackedAudioSource(self.source_url, **ffmpeg_options)

    def refresh_source(self):
        self.source = TrackedAudioSource(self.source_url, **ffmpeg_options)
