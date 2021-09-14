# Author: Matan Omesi
# ID: 205948771
import dataclasses
import json
from dataclasses import dataclass
from typing import List
import requests
import boto3
import settings
from tinydb import TinyDB, Query, table
import time

rekognition_client = boto3.client('rekognition', aws_access_key_id=settings.AWS_SERVER_PUBLIC_KEY,
                                  aws_secret_access_key=settings.AWS_SERVER_SECRET_KEY,
                                  region_name='us-east-2')


@dataclass
class PhotoData:
    date: int
    user_id: int
    file_path: str
    file_size: int
    photo_id: str
    tags: List[str]
    chat_id: int


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class PhotoModelWrapper:
    @classmethod
    def add_photo(cls, photo_details: PhotoData) -> None:
        """
        adding photo details like photo id, path, date uploaded/taken, chat_id, and more data we need or have
        :param photo_details: contain all the photo details
        :return: None
        """
        settings.PHOTO_TABLE.insert(dataclasses.asdict(photo_details))

    @classmethod
    def get_photo(cls, photo_id: str) -> PhotoData:
        """
        getting data of specific image from photo id, if exists
        :param photo_id: photo id which is the file id on telegram server
        :return: photo data Object
        """
        return settings.PHOTO_TABLE.search(Query().photo_id.matches(photo_id))


#
class BotCommandModelWrapper:
    @classmethod
    def get_images(cls, chat_id: int) -> List[str]:
        return ['./picture.png', './cloudy.png']

    @classmethod
    def upload_image(cls, chat_id:int , image_data) -> str:
        photo = image_data['message']['photo'][-1]
        photo_id = photo['file_id']
        message_data = cls.send_message(chat_id, 'Status Uploading - 10%: *Processing Photo*....')
        message_decode = json.loads(message_data.content.decode())
        message_id = message_decode['result']['message_id']
        print('message data: ', message_data.content.decode())
        photo_url_data = requests.get('https://api.telegram.org/bot{}/getFile?file_id={}'
                                      .format(settings.TOKEN, photo_id))

        photo_json = photo_url_data.json()
        text_to_send = 'Photo Sent'
        if photo_json['ok']:
            photo_path = photo_json['result']['file_path']
            get_photo_data = requests.get('https://api.telegram.org/file/bot{}/{}'.format(settings.TOKEN, photo_path))

            cls.delete_message(chat_id, message_id)
            message_data = cls.send_message(chat_id, 'Status Processing - 35%: *Recognize Celebrity Faces* if exist....')
            message_decode = json.loads(message_data.content.decode())
            message_id = message_decode['result']['message_id']

            labels = []
            celebrities_urls = {}
            # recognize celebrity faces
            celebrity_data = rekognition_client.recognize_celebrities(Image={'Bytes': get_photo_data.content})
            print('found celebrity data: ', celebrity_data)
            if 'CelebrityFaces' in celebrity_data:
                for celebrity in celebrity_data['CelebrityFaces']:
                    labels.append(celebrity['Name'])
                    name_splitted = celebrity['Name'].split()
                    if len(name_splitted) > 1:
                        labels.extend(name_splitted)
                    if celebrity['Urls']:
                        celebrities_urls[celebrity['Name']] = []
                        for url in celebrity['Urls']:
                            celebrities_urls[celebrity['Name']].append(url)

            cls.delete_message(chat_id, message_id)
            message_data = cls.send_message(chat_id, 'Status Processing - 60%: *Detecting text* if exist....')
            message_decode = json.loads(message_data.content.decode())
            message_id = message_decode['result']['message_id']

            text_detection_data = rekognition_client.detect_text(Image={'Bytes': get_photo_data.content})
            print('text detection:', text_detection_data)
            detected_lines = []
            if 'TextDetections' in text_detection_data and text_detection_data['TextDetections']:
                for item in text_detection_data['TextDetections']:
                    if item['Type'] == 'LINE':
                        detected_lines.append(item['DetectedText'])

            if 'caption' in image_data['message']:
                labels.extend(list(map(lambda x: x.strip(), image_data['message']['caption'].split(','))))

            cls.delete_message(chat_id, message_id)
            message_data = cls.send_message(chat_id, 'Status Processing - 90%: *Detecting labels* if exist....')
            message_decode = json.loads(message_data.content.decode())
            message_id = message_decode['result']['message_id']

            result = rekognition_client.detect_labels(Image={'Bytes': get_photo_data.content})
            for label in result['Labels']:
                labels.append(label['Name'])

            labels_str = ', '.join(labels)

            if detected_lines:
                labels_str += '\n*Detected lines text*:'
                for line in detected_lines:
                    labels_str += '\n\t' + line

            if celebrities_urls:
                for celebrity_name, celebrity_url_list in celebrities_urls.items():
                    labels_str += '\n*' + celebrity_name + '*:'
                    for celebrity_url in celebrity_url_list:
                        labels_str += '\n\t' + celebrity_url

            labels.extend(list(map(lambda x: x.lower(), detected_lines)))
            labels.append('all')  # for all

            labels_lower = list(map(lambda x: x.lower(), labels))
            detail_to_save = PhotoData(date=image_data['message']['date'],
                                       user_id=image_data['message']['from']['id'],
                                       file_path=photo_json['result']['file_path'],
                                       file_size=photo_json['result']['file_size'],
                                       photo_id=photo_id,
                                       tags=labels_lower,
                                       chat_id=chat_id)
            PhotoModelWrapper.add_photo(detail_to_save)

            text_to_send += '\nDetected Labels: ' + labels_str
            print(text_to_send)

            cls.delete_message(chat_id, message_id)
            cls.send_message(chat_id, 'Status Processing - 100%: *Done*')

            url_to_send = "https://api.telegram.org/bot{}/sendPhoto?chat_id={}" \
                .format(settings.TOKEN, chat_id)
            requests.post(url_to_send, files={'photo': get_photo_data.content})

        else:
            print('could not fetch file path')

        return text_to_send

    @classmethod
    def send_photos(cls, chat_id: int, photos: List[str]):
        url_to_send = "https://api.telegram.org/bot{}/sendPhoto?chat_id={}" \
            .format(settings.TOKEN, chat_id)
        for file in photos:
            requests.post(url_to_send, files={'photo': open(file, 'rb')})

    @classmethod
    def send_photo_by_path(cls, chat_id: int, photo_path: str):
        get_photo_data = requests.get('https://api.telegram.org/file/bot{}/{}'.format(settings.TOKEN, photo_path))
        url_to_send = "https://api.telegram.org/bot{}/sendPhoto?chat_id={}" \
            .format(settings.TOKEN, chat_id)
        requests.post(url_to_send, files={'photo': get_photo_data.content})

    @classmethod
    def send_message(cls, chat_id: int, message: str):
        url_to_send = "https://api.telegram.org/bot{}/sendMessage" \
            .format(settings.TOKEN)
        data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        return requests.post(url_to_send, data)

    @classmethod
    def delete_message(cls, chat_id: int, message_id: int):
        url_to_send = "https://api.telegram.org/bot{}/deleteMessage?chat_id={}&message_id={}" \
            .format(settings.TOKEN, chat_id, message_id)
        requests.get(url_to_send)

    @classmethod
    def get_photos_filter(cls, chat_id: int, start_date: str = None, end_date: str = None,
                          last: int = 3, *tags) -> List[PhotoData]:
        """
        scan for photos with tags that appears on tags, take the last x photos with the range of dates if specified
        :param chat_id: chat id
        :param start_date: start date of uploaded photo to scan
        :param end_date:  end date of uploaded photo to scan
        :param last: max number of photo to be returned
        :param tags: list of tags to scan for each photo that has at least one of the tags
        :return: List[PhotoData]
        """
        if tags:
            tags_s = ' '.join(list(map(lambda x: x.strip(' '), tags)))
            tags = (list(map(lambda x: x.strip(), tags_s.split(','))))
        if start_date == '*':
            start_date = None
        if end_date == '*':
            end_date = None
        tags = list(tags)
        if len(tags) == 0:
            tags.append('all')
        print(tags)
        # if last is None:
        #
        tags = list(map(lambda x: x.lower(), tags))
        photo_dict = Query()
        if start_date and end_date:
            lst_photo_ret = settings.PHOTO_TABLE.search((start_date <= photo_dict.date <= end_date) &
                                                        (photo_dict.tags.any(tags)) &
                                                        (photo_dict.chat_id == chat_id))
        elif start_date:
            lst_photo_ret = settings.PHOTO_TABLE.search((start_date <= photo_dict.date) &
                                                        (photo_dict.tags.any(tags)) &
                                                        (photo_dict.chat_id == chat_id))
        elif end_date:
            lst_photo_ret = settings.PHOTO_TABLE.search((photo_dict.date <= end_date) &
                                                        (photo_dict.tags.any(tags)) &
                                                        (photo_dict.chat_id == chat_id))
        else:
            lst_photo_ret = settings.PHOTO_TABLE.search((photo_dict.tags.any(tags)) & (photo_dict.chat_id == chat_id))
        if last is None:
            return lst_photo_ret
        return lst_photo_ret[:last]

    @classmethod
    def delete_photo_filter(cls, chat_id: int, start_date: str = None, end_date: str = None, *tags) -> List[PhotoData]:
        """
        scan for photos with tags that appears on tags, take the last x photos with the range of dates if specified
        :param chat_id: chat id
        :param start_date: start date of uploaded photo to scan
        :param end_date:  end date of uploaded photo to scan
        :param last: max number of photo to be returned
        :param tags: list of tags to scan for each photo that has at least one of the tags
        :return: List[PhotoData]
        """
        if tags:
            tags_s = ' '.join(list(map(lambda x: x.strip(' '), tags)))
            tags = (list(map(lambda x: x.strip(), tags_s.split(','))))
        if start_date == '*':
            start_date = None
        if end_date == '*':
            end_date = None

        tags = list(tags)
        if len(tags) == 0:
            tags.append('all')
        print(tags)
        # if last is None:
        #
        tags = list(map(lambda x: x.lower(), tags))
        photo_dict = Query()
        delta_epoch = 23 * 60 * 60
        text = ""
        if tags:
            text = ' with the following tags: ' + ', '.join(tags)

        if start_date and end_date:
            settings.PHOTO_TABLE.remove((start_date <= photo_dict.date <= end_date) &
                                        (photo_dict.tags.any(tags)) &
                                        (photo_dict.chat_id == chat_id))
            text = ' from ' + time.strftime(settings.DATE_FORMAT, time.localtime(start_date)) + ' to ' + \
                   time.strftime(settings.DATE_FORMAT, time.localtime(end_date - delta_epoch)) + text
        elif start_date:
            settings.PHOTO_TABLE.remove((start_date <= photo_dict.date) &
                                        (photo_dict.tags.any(tags)) &
                                        (photo_dict.chat_id == chat_id))
            text = ' from ' + time.strftime(settings.DATE_FORMAT, time.localtime(start_date)) + text
        elif end_date:
            settings.PHOTO_TABLE.remove((photo_dict.date <= end_date) &
                                        (photo_dict.tags.any(tags)) &
                                        (photo_dict.chat_id == chat_id))
            text = ' until ' + time.strftime(settings.DATE_FORMAT, time.localtime(end_date - delta_epoch)) + text
        else:
            settings.PHOTO_TABLE.remove((photo_dict.tags.any(tags)) & (photo_dict.chat_id == chat_id))

        return 'delete all photos ' + text + ' successfully'
