import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)

        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("h2", {"class":"card__title font-founders-condensed js-wrap"})
        headline = soup.find_all("h2", {"class":"card__title card__title--promoted font-founders"})
        headlineLink = soup.find_all("a", {"class":"card card--promoted"})
        links = soup.find_all("a", {"class":"card d-flex relative"})
        divImages = soup.find_all("div", {"class":"card__image"})

        titles = []
        urls = []
        blurbs = []
        imageURLS = []

        for result in divImages:
            image = result.find("img")
            imageURL = "https://www.nbcsports.com" + str(image.get('data-src'))
            imageURLS.append(imageURL)

        for entry in headline:
            title_element = entry.find("span")
            if title_element is not None:
                titles.append(entry.text.strip())

        for entry in headlineLink:
            link_url = entry["href"]
            if link_url is not None:
                urls.append("https://www.nbcsports.com" + str(link_url))

        for entry in results:
            title_element = entry.find("div")
            if title_element is not None:
                titles.append(title_element.text.strip())

        for entry in links:
            link_url = entry["href"]
            if link_url is not None:
                urls.append("https://www.nbcsports.com" + str(link_url))

        for url in urls[:6]:
            page = requests.get(str(url))
            soup = BeautifulSoup(page.content, "html.parser")
            article = soup.find("article")
            if article is not None:
                bigLetter = article.find("span").text.strip()
                if article.find("p"):
                    blurb = article.find("p").text.strip()
                    blurb = blurb.strip()
                    blurbs.append(bigLetter[1:] + blurb)
                else: 
                    blurbs.append("")
        return titles, urls, imageURLS, blurbs

    except requests.exceptions.HTTPError as errh:
        print ("HTTP Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        print ("Something went wrong",err)

URL1 = "https://www.nbcsports.com/philadelphia/eagles"
URL2 = "https://www.nbcsports.com/philadelphia/sixers"
URL3 = "https://www.nbcsports.com/philadelphia/phillies"
URL4 = "https://www.nbcsports.com/philadelphia/flyers"

titles3, urls3, imageURLS3, blurbs3 = scrape_website(URL1)
titles3a, urls3a, imageURLS3a, blurbs3a = scrape_website(URL2)
titles3b, urls3b, imageURLS3b, blurbs3b = scrape_website(URL3)
titles3c, urls3c, imageURLS3c, blurbs3c = scrape_website(URL4)

# You can then use the lists as needed. For example, you could print out the first item in each list like this:
# print(titles3[0])
# print(urls3[0])
# print(imageURLS3[0])

