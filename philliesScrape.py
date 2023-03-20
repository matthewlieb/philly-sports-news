import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
    except requests.exceptions.RequestException as e:
        print("Error: Unable to connect to website.")
        return None

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("article")
    images = soup.find_all("div", class_="p-image article-navigation__item-thumb")

    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    for image in images:
        imageURL = image.find("img")
        imageURL = imageURL.get('data-srcset').split(" ")[0]
        if imageURL is not None:
            imageURLS.append(imageURL)
    for entry in results:
        title_element = entry.find("h1")
        blurb = entry.find("p").text.strip()
        if blurb is not None:
            blurb = " ".join(blurb.split())
            blurbs.append(blurb)
        if title_element is not None:  # Check if the element was found
            title = title_element.text.strip()
            titles.append(title)
            link = entry.find("a")
            if link is not None:
                link_url = link["href"]
                urls.append("https:/mlb.com/phillies" + str(link_url))
    
    return titles, blurbs, urls, imageURLS

URL = "https://www.mlb.com/phillies/news"
titles2b, blurbs2b, urls2b, imageURLS2b = scrape_website(URL)


# print("\n")
# for i in range(6):
#     print(titles2b[i])
#     print(blurbs2b[i])
#     print(urls2b[i])
#     print(imageURLS2b[i])
#     print("\n")