import os
import requests

ANKI_CONNECT_URL = 'http://localhost:8765'


class AnkiHelper:
    def __init__(self, course_name: str):
        self.course_name = course_name

    def _create_deck_json(self, deck_name: str) -> dict:
        return {
            "action": "createDeck",
            "version": 6,
            "params": {
                "deck": deck_name
            }
        }

    def _add_note_json(self, deck_name: str, tags: list, front_text: str, back_text: str, local_audio_path: str) -> dict:
        audio_filename = os.path.basename(local_audio_path)
        return {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Basic (type in the answer)",
                    "fields": {
                        # "Front": f"{front_text}<br>[sound:{audio_filename}]",
                        "Front": front_text,
                        "Back": back_text
                    },
                    "audio": [{
                        "filename": audio_filename,
                        "path": local_audio_path,
                        "fields": ["Front"]
                    }],
                    "options": {
                        "allowDuplicate": True
                    },
                    "tags": tags
                }}}

    def _store_media_file(self, filename: str, file_path: str) -> dict:
        return {
            "action": "storeMediaFile",
            "version": 6,
            "params": {
                "filename": filename,
                "path": file_path
            }
        }

    def _sync_json(self) -> dict:
        return {
            "action": "sync",
            "version": 6
        }

    def _post_to_anki_connect(self, body: dict):
        response = requests.post(ANKI_CONNECT_URL, json=body)
        response_json = response.json()

        if 'error' in response_json and response_json['error'] is not None:
            raise Exception(f"AnkiConnect error: {response_json['error']}")

        return response_json['result']

    def create_deck(self, section_name: str, lesson_name: str):
        deck_name = f"{self.course_name}_{section_name}_{lesson_name}"
        body = self._create_deck_json(deck_name)
        self._post_to_anki_connect(body)
        return deck_name

    def add_word_to_deck(self, deck_name: str, word, tags: list):
        front = word.german  # German word
        back = word.hungarian  # Hungarian translation
        audio_filename = os.path.basename(word.local_audio_path)

        # Store audio file in Anki's media collection
        media_body = self._store_media_file(audio_filename, word.local_audio_path)
        self._post_to_anki_connect(media_body)

        # Add note (card) to deck
        note_body = self._add_note_json(deck_name, tags, front, back, word.local_audio_path)
        self._post_to_anki_connect(note_body)

    def sync_deck(self):
        self._post_to_anki_connect(self._sync_json())
