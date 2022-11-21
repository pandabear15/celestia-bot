import discord
import json


def _list_attachments(attachments: list[discord.Attachment]) -> list[(str, bool)]:
    str_list: list[(str, bool)] = []
    for i in range(len(attachments)):
        str_list.append((attachments[i].proxy_url, attachments[i].is_spoiler()))
    return str_list


class MessageModel:
    def __init__(self, message: discord.Message = None, payload: discord.RawMessageUpdateEvent |
                                                                 discord.RawMessageDeleteEvent = None, **kwargs):
        if message is None and payload is None and kwargs is None:
            raise ValueError('At least one of message, payload, and kwargs must be non-None')
        if message is not None:
            self.message_id: int = message.id
            self.channel_id: int = message.channel.id
            self.user_id: int = message.author.id
            self.content: str = message.content
            self.sticker: int = 0 if len(message.stickers) <= 0 else message.stickers[0].id
            self.attachments: list[(str, bool)] = _list_attachments(message.attachments)
            if self.content == '':
                self.content = '*[Empty message body]*'
        elif payload is not None:
            self.message_id: int = payload.message_id
            self.channel_id: int = payload.channel_id
            self.user_id: int = 0
            self.content: str = ''
            self.sticker: int = 0
            self.attachments: list[(str, bool)] = []
        else:
            self.__dict__.update(kwargs['dict'])

    def __lt__(self, other):
        return self.message_id < other.message_id

    def __gt__(self, other):
        return self.message_id > other.message_id

    def __le__(self, other):
        return self.message_id <= other.message_id

    def __ge__(self, other):
        return self.message_id >= other.message_id

    def __ne__(self, other):
        return self.message_id != other.message_id

    def __eq__(self, other):
        return self.message_id == other.message_id

    def __sizeof__(self) -> int:
        attachment_size = 0
        for attachment in self.attachments:
            attachment_size += attachment.__sizeof__()
        return (self.message_id.__sizeof__() +
                self.channel_id.__sizeof__() +
                self.user_id.__sizeof__() +
                self.content.__sizeof__() +
                self.sticker.__sizeof__() +
                self.attachments.__sizeof__() +
                attachment_size)

    def total_eq(self, other):
        return (self.message_id == other.message_id and self.content == other.content
                and self.sticker == other.sticker and self.attachment_eq(other))

    def attachment_eq(self, other):
        if len(self.attachments) != len(other.attachments):
            return False
        for i in range(len(self.attachments)):
            if self.attachments[i][0] != other.attachments[i][0]:
                return False
        return True

    @staticmethod
    def is_image(url: str) -> str | None:
        img_suffixes = ['.jpg', '.jpeg', '.png', '.gif']
        for suffix in img_suffixes:
            if url.endswith(suffix):
                return suffix
        return None
