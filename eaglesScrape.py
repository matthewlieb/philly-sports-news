import requests 
import re
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("div", {"class":"d3-l-col__col-3"})

        titles = []
        urls = []
        imageURLS = []
        blurbs = []

        for entry in results:
            title_element = entry.find("h3")
            blurb_div = entry.find("div")
            if blurb_div is not None:
                blurb = blurb_div.text.strip()
                blurb = " ".join(blurb.split())
                blurb = re.sub(r"(\w)([A-Z])", r"\1 \2", blurb)
                blurbs.append(blurb[4:])
            
            if title_element is not None: # Check if the element was found
                title = title_element.text.strip()
                titles.append(title)

            link = entry.find("a")
            if link is not None:
                link_url = link["href"]
                urls.append("https://www.philadelphiaeagles.com" + str(link_url))

            image = entry.find("img")
            if image is not None:
                imageURL = image['src']
                modified_url = imageURL.replace("/t_lazy", "")
                imageURLS.append(modified_url)

        return titles, blurbs, urls, imageURLS
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

URL = "https://www.philadelphiaeagles.com/news/all"
titles2, blurbs2, urls2, imageURLS2 = scrape_website(URL)

# print(titles2[0])
# print(blurbs2[0])
# print(urls2[0])
# print(imageURLS2[0])