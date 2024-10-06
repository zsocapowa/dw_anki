import os
import time
from functools import wraps

import requests
from tqdm import tqdm

from lxml import html

from urllib.parse import urlparse


def get_lesson_urls(url: str) -> dict:
    page = requests.get(url)
    tree = html.fromstring(page.content)

    sections = tree.xpath('//div[@class="accordion"]')

    parsed_url = urlparse(url)
    base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    data = {}

    for section in sections:
        title = section.xpath('.//h2')[0].text  # TODO: add error handling
        data.setdefault(title, [])
        lessons = section.xpath('.//li')
        for lesson in lessons:
            lesson_url = lesson.xpath('.//@href')[0]
            lesson_title = lesson.xpath('.//h3')[0].text
            lesson_subtitle = '. '.join(e.text for e in lesson.xpath('.//span') if e.text)
            data[title].append(
                {
                    "lesson_title": lesson_title,
                    "lesson_subtitle": lesson_subtitle,
                    "lesson_url": f"{base_url}{lesson_url}/lv"
                }
            )
    return data


def get_words(lesson_url: str) -> list:
    words = []
    # lesson_url = "https://learngerman.dw.com/hu/hallo/l-66033816/lv"
    page = requests.get(lesson_url)
    tree = html.fromstring(page.content)
    rows = tree.xpath('//div[@class="knowledge-wrapper"]//div[a/audio]')
    for row in rows:
        german = row.xpath('a/strong')[0].text
        german_extra = row.xpath('span')[0].text if row.xpath('span') else None
        german_audio_link = str(row.xpath('a/audio/source/@src')[0])
        # img = row.getparent().xpath('.//img[contains(@class, "hq-img")]')
        hungarian = row.getparent().xpath('.//span/p')[0].text
        words.append({
            "german": german,
            "german_extra": german_extra,
            "german_audio_link": german_audio_link,
            "hungarian": hungarian
        })
    return words


def download_from_url(url: str, path: str) -> bool:
    # Check if the file already exists
    if os.path.isfile(path):
        return True

    try:
        # Stream the content from the URL
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Get the total file size in bytes (if available)
        total_size = int(response.headers.get('content-length', 0))
        chunk_size = 8192  # 8 KB per chunk

        # Use one `with` statement for both the file and progress bar
        with open(path, 'wb') as file, tqdm(total=total_size, unit='B', unit_scale=True, desc=path,
                                            ncols=80) as progress_bar:
            # Write the file in chunks
            for chunk in response.iter_content(chunk_size=chunk_size):
                file.write(chunk)
                progress_bar.update(len(chunk))  # Update progress bar

        return True  # Download successful

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False  # Download failed


if __name__ == "__main__":
    start_time = time.time()
    course_url = 'https://learngerman.dw.com/hu/nicos-weg/c-65959869'
    lesson_urls = get_lesson_urls(course_url)
