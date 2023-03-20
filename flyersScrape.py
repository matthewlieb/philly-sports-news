import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("article", {"class":"article-item"})
        images = soup.find_all("div", {"class":"article-item__img-container"})

        titles = []
        urls = []
        blurbs = []
        imageURLS = []

        for image in images:
            image = image.find("img")
            if image is not None:
                if image.get('src') is not None:
                    imageURL = str(image.get('src'))
                    imageURLS.append(imageURL)
                elif image.get('data-src') is not None:
                    imageURL = str(image.get('data-src'))
                    imageURLS.append(imageURL)
                else:
                    imageURLS.append("")

        for entry in results:
            title_element = entry.find("h1")
            blurb = entry.find("h2")
            if blurb is not None:
                blurbs.append(blurb.text.strip())

            if title_element is not None:  # Check if the element was found
                title = title_element.text.strip()
                titles.append(title)

                link = entry.find("a", {"class":"article-item__more"})
                if link is not None:
                    link_url = link["href"]
                    urls.append("https://www.nhl.com" + str(link_url))

        return titles, blurbs, urls, imageURLS
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

URL = "https://www.nhl.com/flyers/news"
titles2c, blurbs2c, urls2c, imageURLS2c = scrape_website(URL)

# print(titles2c[0])
# print(blurbs2c[0])
# print(urls2c[0])
# print(imageURLS2c[0])