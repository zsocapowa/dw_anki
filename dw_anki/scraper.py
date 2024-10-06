import os
import re
import time
import asyncio
import aiohttp

from lxml import html
from typing import List, Optional
from urllib.parse import urlparse, urljoin
from functools import wraps


# Decorator to measure execution time
def measure_time(func):
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds")
            return result

        return wrapper
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()  # Start time
            result = func(*args, **kwargs)  # Execute sync function
            elapsed_time = time.time() - start_time  # Measure elapsed time
            print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds")
            return result

        return wrapper


class Fetchable:
    def __init__(self, url: str):
        self.url = url

    async def fetch(self, session: aiohttp.ClientSession) -> str:
        print(f"Fetching data from {self.url}")
        async with session.get(self.url) as response:
            return await response.text()


class Word:
    def __init__(self, german: str, hungarian: str, german_extra: Optional[str] = None,
                 german_audio_link: Optional[str] = None):
        self.german = german
        self.hungarian = hungarian
        self.german_extra = german_extra
        self.german_audio_link = german_audio_link
        self.local_audio_path: Optional[str] = None

    def __repr__(self):
        return f"Word(german='{self.german}', hungarian='{self.hungarian}')"

    def sanitize_filename(self) -> str:
        # Replace spaces with underscores and invalid characters with an underscore
        return re.sub(r'[<>:"/\\|?*]', '_', self.german.replace(' ', '_')) + '.mp3'

    # Async method to download audio if it doesn't exist yet
    async def download_audio(self, session: aiohttp.ClientSession):
        if self.german_audio_link:
            audio_filename = self.sanitize_filename()
            self.local_audio_path = os.path.abspath(os.path.join("audio_files", audio_filename))

            # Check if the file already exists
            if not os.path.exists(self.local_audio_path):
                os.makedirs("audio_files", exist_ok=True)  # Ensure directory exists

                try:
                    async with session.get(self.german_audio_link) as response:
                        response.raise_for_status()  # Ensure we catch any HTTP errors

                        # Write the audio content to a file
                        with open(self.local_audio_path, 'wb') as file:
                            file.write(await response.content.read())

                    return True  # Download successful

                except Exception as e:
                    print(f"Error downloading {self.german_audio_link}: {e}")
                    return False  # Download failed
            else:
                return True  # Audio already exists, no need to download


class Lesson(Fetchable):
    def __init__(self, title: str, url: str):
        super().__init__(url)
        self.title = title
        self.words: List[Word] = []

    async def parse(self, session: aiohttp.ClientSession):
        content = await self.fetch(session)
        tree = html.fromstring(content)
        rows = tree.xpath('//div[@class="knowledge-wrapper"]//div[a/audio]')
        for row in rows:
            german = row.xpath('a/strong')[0].text
            german_extra = row.xpath('span')[0].text if row.xpath('span') else None
            german_audio_link = str(row.xpath('a/audio/source/@src')[0])
            hungarian = row.getparent().xpath('.//span/p')[0].text
            word = Word(german, hungarian, german_extra, german_audio_link)
            self.words.append(word)

    async def download_all_audio(self, session: aiohttp.ClientSession):
        tasks = [word.download_audio(session) for word in self.words]
        await asyncio.gather(*tasks)  # Download all audio concurrently

    def __repr__(self):
        return f"Lesson(title='{self.title}', words={len(self.words)})"


class Section:
    def __init__(self, title: str):
        self.title = title
        self.lessons: List[Lesson] = []

    def parse_lessons(self, section_element, base_url: str):
        lesson_elements = section_element.xpath('.//li')
        for lesson_element in lesson_elements:
            lesson_url = lesson_element.xpath('.//@href')[0]
            lesson_title = lesson_element.xpath('.//h3')[0].text
            full_lesson_url = urljoin(base_url, f"{lesson_url}/lv")
            self.lessons.append(Lesson(lesson_title, full_lesson_url))

    def __repr__(self):
        return f"Section(title='{self.title}', lessons={len(self.lessons)})"


class Course(Fetchable):
    def __init__(self, url: str):
        super().__init__(url)
        self.sections: List[Section] = []

    async def parse(self, session: aiohttp.ClientSession):
        content = await self.fetch(session)
        tree = html.fromstring(content)
        parsed_url = urlparse(self.url)
        base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
        section_elements = tree.xpath('//div[@class="accordion"]')

        for section_element in section_elements:
            section_title = section_element.xpath('.//h2')[0].text
            section = Section(section_title)
            section.parse_lessons(section_element, base_url)
            self.sections.append(section)

    async def fetch_all_words(self, session: aiohttp.ClientSession):
        tasks = []
        for section in self.sections:
            print(f"Fetching lessons from section: {section.title}")
            for lesson in section.lessons:
                tasks.append(lesson.parse(session))
        await asyncio.gather(*tasks)

    async def download_all_audio(self, session: aiohttp.ClientSession):
        tasks = [lesson.download_all_audio(session) for section in self.sections for lesson in section.lessons]
        await asyncio.gather(*tasks)  # Download all audio concurrently

    def __repr__(self):
        return f"Course(url='{self.url}', sections={len(self.sections)})"


@measure_time
async def main():
    course_url = 'https://learngerman.dw.com/hu/nicos-weg/c-65959869'
    async with aiohttp.ClientSession() as session:
        course = Course(course_url)
        await course.parse(session)
        await course.fetch_all_words(session)
        await course.download_all_audio(session)  # Download all audio files concurrently
    return course


if __name__ == "__main__":
    courses = asyncio.run(main())
