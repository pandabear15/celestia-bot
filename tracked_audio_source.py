import io
from typing import Union, Optional
from typing.io import IO
import discord


class TrackedAudioSource(discord.FFmpegPCMAudio):
    def __init__(
            self,
            source: Union[str, io.BufferedIOBase],
            *,
            executable: str = 'ffmpeg',
            pipe: bool = False,
            stderr: Optional[IO[str]] = None,
            before_options: Optional[str] = None,
            options: Optional[str] = None,
    ):
        super().__init__(source, executable=executable, pipe=pipe, stderr=stderr, before_options=before_options,
                         options=options)
        self.count_20ms = 0

    def read(self) -> bytes:
        self.count_20ms += 1
        return super().read()

    def ms_elapsed(self) -> int:
        return self.count_20ms * 20
