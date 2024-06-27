import requests
from bs4 import BeautifulSoup as bs
import json
import argparse


def get_info_page_html(html: bytes) -> bytes:
    soup = bs(html, "lxml")
    link = soup.find("div", {"data-testid": "hero-subnav-bar-right-block"}).find("a")["href"]
    info_page_html = requests.get("https://www.imdb.com/" + link, headers=headers).content

    return info_page_html


def get_director(html: bytes) -> list[str]:
    soup = bs(html, "lxml")
    all_director = soup.find("h4", {"name": "director"}).find_next("table").find_all("a")

    directors = []
    for director in all_director:
        directors.append(director.text.strip())

    return directors


def get_cast(info_page_html: bytes) -> list[str]:
    soup = bs(info_page_html, "lxml")
    all_cast = soup.find("table", {"class": "cast_list"}).find_all("img")

    cast = []
    for i in all_cast:
        if "alt" in i.attrs:
            cast.append(i.attrs["alt"])

    return cast[0:10]


def get_writer(info_page_html: bytes) -> list[str]:
    soup = bs(info_page_html, "lxml")
    all_writers = soup.find("h4", {"name": "writer"}).find_next("table").find_all("a")

    writers = []
    for writer in all_writers:
        writers.append(writer.text.strip())

    return writers


def get_producer(info_page_html: bytes) -> list[str]:
    soup = bs(info_page_html, "lxml")
    all_producers = soup.find("h4", {"name": "producer"}).find_next("table").find_all("a")

    producers = []
    for producer in all_producers:
        producers.append(producer.text.strip())

    return producers


def get_contry_of_origin(html: bytes) -> list[str]:
    soup = bs(html, "lxml")
    all_country = soup.find("li", {"class": "ipc-metadata-list__item", "data-testid": "title-details-origin"}).find_all("a")

    country_of_origin = []
    for country in all_country:

        country_of_origin.append(country.text.strip())

    return country_of_origin


def get_prodaction_companies(html: bytes) -> list[str]:
    soup = bs(html, "lxml")
    all_production = json.loads(soup.find("script", {"id": "__NEXT_DATA__"}).text)['props']["pageProps"]["aboveTheFoldData"]["production"]["edges"]

    production_companies = []
    for production in all_production:
        production_companies.append(production["node"]["company"]["companyText"]["text"])

    return production_companies


def get_taglines(taglines_html: bytes) -> list[str]:
    soup = bs(taglines_html, "lxml")
    all_taglines = soup.find_all("div",  {"class": "ipc-html-content-inner-div", "role": "presentation"})

    taglines = []
    for tagline in all_taglines:
        taglines.append(tagline.text.strip())

    return taglines


def get_episodes(seasons_numbers: int) -> dict:
    url = main_url + "episodes/"

    seasons = {"count": seasons_numbers, "seasons": []}
    for number in range(1, seasons_numbers+1):
        params = {"season": number}
        episodes_html = requests.get(url, headers=headers, params=params).content

        soup = bs(episodes_html, "lxml")
        all_episodes = soup.find_all("article")

        episodes = []
        for episode in all_episodes:
            data = episode.find_next("div", {"class": "ipc-title__text"}).text.split("∙")

            episode_number = data[0].split(".")[1].replace("E", "").strip()
            episode_title = data[1].strip()
            episode_date = episode.find("span").text

            episodes.append({
                "episode_number": episode_number,
                "episode_title": episode_title,
                "episode_date": episode_date
            })

        seasons["seasons"].append({
            "seasons_numbers": number,
            "episodes": episodes
        })

    return seasons


if __name__ == "__main__":

    # Argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('page_link', type=str)
    args = parser.parse_args()

    main_url = args.page_link.split("?")[0]
    headers = {
        "Accept-Language": "en-US, en;q=0.9, es;q=0.8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }

    html = requests.get(main_url, headers=headers).content
    soup = bs(html, "lxml")

    json_data = json.loads(soup.find("script", {"type": "application/ld+json"}).text)
    content_type = json_data["@type"]

    info_page_html = get_info_page_html(html)
    episodes_html = requests.get(main_url + "episodes/", headers=headers).content
    taglines_html = requests.get(main_url + "taglines/", headers=headers).content

    data = {
        "title": json_data["name"],
        "genre": json_data["genre"],
        "poster": json_data["image"],
        "short_description": json_data["description"],
        "cast": get_cast(info_page_html),
        "director": get_director(info_page_html),
        "producer": get_producer(info_page_html),
        "writer": get_writer(info_page_html),
        "release_date": json_data["datePublished"],
        "country_of_origin": get_contry_of_origin(html),
        "production_companies": get_prodaction_companies(html),
        "certificate": json_data["contentRating"],
        "taglines": get_taglines(taglines_html),
        "imdb_rating": {
            "rating_value": json_data["aggregateRating"]["ratingValue"],
            "rating_count": json_data["aggregateRating"]["ratingCount"]
        },
        "runtime": soup.find("meta", {"property": "og:description"})["content"].split("|")[0].strip().replace(" ", "")
    }

    if content_type == "TVSeries":
        seasons_numbers = int(soup.find("label", {"for": "browse-episodes-season"}).text.split(" ")[0])
        seasons = get_episodes(seasons_numbers)

        data = {
            **data,
            **seasons
        }

    # Create file
    filename = data["title"].replace(" ", "_") + ".json"
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)



