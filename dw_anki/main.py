import asyncio
import logging
import os

import aiohttp

from dw_anki.anki_api_utils import AnkiHelper
from dw_anki.scraper import measure_time, Course

COURSE_URL = 'https://learngerman.dw.com/hu/nicos-weg/c-65959869'
COURSE_NAME = "A1_NW"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler("run.log"),
                        logging.StreamHandler()
                    ])

@measure_time
async def main():
    async with aiohttp.ClientSession() as session:
        course = Course(COURSE_URL)
        await course.parse(session)
        await course.fetch_all_words(session)
        await course.download_all_audio(session)  # Download all audio files concurrently

        # Initialize AnkiHelper
        anki_helper = AnkiHelper(COURSE_NAME)

        # Iterate through sections and lessons to create Anki decks and add words
        for s_idx, section in enumerate(course.sections):
            for l_idx, lesson in enumerate(section.lessons):
                deck_name = anki_helper.create_deck(f"section_{s_idx}", f"lesson_{l_idx}")

                for word in lesson.words:
                    tags = [COURSE_NAME, section.title, lesson.title]
                    anki_helper.add_word_to_deck(deck_name, word, tags)

        # Optionally sync the deck with Anki
        anki_helper.sync_deck()

    print(course)

if __name__ == "__main__":
    asyncio.run(main())
