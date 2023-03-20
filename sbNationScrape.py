import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        images = soup.find_all('img')
        results = soup.find_all("div", {"class":"c-entry-box--compact__body"})

        titles = []
        urls = []
        authors = []
        imageURLS = []
        blurbs = []

        for image in images:
            if 'https://' in image.get('src', ''):
                imageURLS.append(image['src'])

        imageURLS = imageURLS[2:]

        for result in results:
            title_element = result.find("h2", class_="c-entry-box--compact__title")
            author = result.find("span", class_="c-byline__author-name")

            if title_element is not None:
                titles.append(title_element.text.strip())
                link = result.find("a")
                blurb = result.find("p")
                if blurb is not None:
                    blurbs.append(blurb.text.strip())
                if link is not None:
                    link_url = link["href"]
                    urls.append(link_url)

            if author is None:
                authors.append("-- None")
            if author is not None:
                authors.append("-- " + author.text)

        return titles, urls, authors, imageURLS, blurbs
    except requests.exceptions.RequestException as e:
        print("An error occurred: ", e)
        return [], [], [], [], []

URL1 = "https://www.bleedinggreennation.com/"
URL2 = "https://www.libertyballers.com/"
URL3 = "https://www.thegoodphight.com/"
URL4 = "https://www.broadstreethockey.com/"

titles1, urls1, authors1, imageURLS1, blurbs1 = scrape_website(URL1)
titles1a, urls1a, authors1a, imageURLS1a, blurbs1a = scrape_website(URL2)
titles1b, urls1b, authors1b, imageURLS1b, blurbs1b = scrape_website(URL3)
titles1c, urls1c, authors1c, imageURLS1c, blurbs1c = scrape_website(URL4)

# You can then use the lists as needed. For example, you could print out the first item in each list like this:
# print(titles1[0])
# print(titles1a[0])



