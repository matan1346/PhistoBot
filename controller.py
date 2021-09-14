# Author: Matan Omesi, Omer Hadad
from datetime import datetime
from typing import Tuple, List

import settings
from model import BotCommandModelWrapper, PhotoModelWrapper


class BotCommandsController:
    # commands definitions, names -> func names and parameters size
    COMMANDS = {'start': {'type_answer': 1, 'func': 'start_description', 'min_params_size': 0},
                'get_images': {'type_answer': 2, 'func': 'get_images', 'min_params_size': 0},
                'upload_image': {'type_answer': 2, 'func': 'upload_image', 'min_params_size': 2},
                'filter': {'type_answer': 1, 'func': 'filter_command', 'min_params_size': 2},
                'all': {'type_answer': 1, 'func': 'all_photos', 'min_params_size': 0},
                'delete': {'type_answer': 1, 'func': 'delete_filter', 'min_params_size': 2},
                'delete_all': {'type_answer': 1, 'func': 'delete_all', 'min_params_size': 0}}

    @classmethod
    def process_command(cls, chat_id: int, command: str) -> Tuple:
        if not command.startswith('/'):
            return 1, 'Invalid command'

        cmd, *params = command[1:].split()
        # if command name not exists or parameters size not equal to definition
        if cmd not in cls.COMMANDS or cls.COMMANDS[cmd]['min_params_size'] > len(params):
            return 1, 'Invalid command'

        # call current function command with parameters and return result
        return cls.COMMANDS[cmd]['type_answer'], getattr(BotCommandsController,
                                                         cls.COMMANDS[cmd]['func'])(chat_id, *params)

    @classmethod
    def start_description(cls, chat_id: int) -> str:
        description_file = open('commands_description.txt', 'r')
        text = description_file.read()
        description_file.close()
        return text

    @classmethod
    def filter_command(cls, chat_id: int, start_date: str, end_date: str, *tags) -> str:

        try:
            start_date = datetime.strptime(start_date, settings.DATE_FORMAT)
            start_date = (start_date - settings.EPOC).total_seconds()

            end_date = datetime.strptime(end_date, settings.DATE_FORMAT)
            end_date = (end_date - settings.EPOC).total_seconds() + 23 * 60 * 60 + 59 * 60 + 59
        except Exception as e:
            start_date = None
            end_date = None
        photos = BotCommandModelWrapper.get_photos_filter(chat_id, start_date, end_date, 5, *tags)
        if photos:
            for photo in photos:
                BotCommandModelWrapper.send_photo_by_path(chat_id, photo['file_path'])
            return 'Sent photos with filter'
        return 'No photos were found for this filter'

    @classmethod
    def get_images(cls, chat_id: int):
        return BotCommandModelWrapper.get_images(chat_id)

    @classmethod
    def upload_image(cls, chat_id: int, image_data) -> str:
        return BotCommandModelWrapper.upload_image(chat_id, image_data)

    @classmethod
    def send_photos(cls, chat_id: int, photos: List[str]) -> None:
        BotCommandModelWrapper.send_photos(chat_id, photos)

    @classmethod
    def send_message(cls, chat_id: int, message: str) -> None:
        BotCommandModelWrapper.send_message(chat_id, message)

    @classmethod
    def all_photos(cls, chat_id: int) -> str:
        photos = BotCommandModelWrapper.get_photos_filter(chat_id, '*', '*', last=None)
        if photos:
            for photo in photos:
                BotCommandModelWrapper.send_photo_by_path(chat_id, photo['file_path'])
            return 'Sent all photos'  # PhotoModelWrapper.get_photos_filter(*tag, start_date, end_date)
        return 'No photos were found in the database'

    @classmethod
    def delete_filter(cls, chat_id: int, start_date: str, end_date: str, *tags) -> str:
        try:
            start_date = datetime.strptime(start_date, settings.DATE_FORMAT)
            start_date = (start_date - settings.EPOC).total_seconds()

            end_date = datetime.strptime(end_date, settings.DATE_FORMAT)
            end_date = (end_date - settings.EPOC).total_seconds() + 23 * 60 * 60 + 59 * 60 + 59
        except Exception as e:
            start_date = None
            end_date = None
        text = BotCommandModelWrapper.delete_photo_filter(chat_id, start_date, end_date, *tags)
        return text

    @classmethod
    def delete_all(cls, chat_id: int) -> str:
        BotCommandModelWrapper.delete_photo_filter(chat_id, '*', '*')
        return 'Delete all the photos successfully'
