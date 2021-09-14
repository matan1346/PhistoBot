# Author: Matan Omesi
# ID: 205948771
# Author: Omer Hadad
# ID: 315723940

import requests
import settings
from flask import Flask, Response, request
from controller import BotCommandsController


TELEGRAM_INIT_WEBHOOK_URL = 'https://api.telegram.org/bot{}/setWebhook?' \
                            'url=https://59a06b776463.ngrok.io/message'.format(settings.TOKEN)

requests.get(TELEGRAM_INIT_WEBHOOK_URL)

app = Flask(__name__)


@app.route('/message', methods=["POST"])
def handle_message() -> Response:
    try:
        print('request:')
        get_json = request.get_json()
        print(get_json)
        chat_id = get_json['message']['chat']['id']

        if 'text' in get_json['message']:
            command = get_json['message']['text']

            # processing command
            answer = BotCommandsController.process_command(chat_id, command)
            print(f'Command: {command}')
            print('answer: ', answer)
            # preparing sending a reply message text
            if answer[0] == 1:  # text
                BotCommandsController.send_message(chat_id, answer[1])
            if answer[0] == 2:  # photos
                BotCommandsController.send_photos(chat_id, answer[1])
        elif 'photo' in get_json['message']:
            text_to_send = BotCommandsController.upload_image(chat_id, get_json)
            BotCommandsController.send_message(chat_id, text_to_send)

            print('photo sent')
    except Exception as e:
        print("Error: ", e)
    return Response("success")


if __name__ == '__main__':
    app.run(port=5002)
