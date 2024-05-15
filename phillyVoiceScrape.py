import requests
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
    except requests.exceptions.RequestException as e:
        print("Error: Failed to establish a connection to the website")
        return None

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("div", {"class":"article-text"})

    titles = []
    urls = []
    imageURLS = []
    blurbs = []

    for entry in results:
        title_element = entry.find("h1")
        link = entry.find_all("a")
        if link:
            link_url = link[1]["href"]
            if title_element:
                titles.append(title_element.text)
            if link_url:
                urls.append("https://www.phillyvoice.com" + str(link_url))

    for url in urls[:4]:
        if "https://www.phillyvoice.com/" in url:
            try:
                page = requests.get(url)
            except requests.exceptions.RequestException as e:
                print("Error: Failed to establish a connection to the website")
                return None
            soup = BeautifulSoup(page.content, "html.parser")
            results = soup.find_all("div", {"class":"body-content"})
            image_div = soup.find('div', class_='feature-image')
            sponsor_div = image_div.find('div', class_='sponsor')
            if sponsor_div:
                sponsor_div.decompose() # remove sponsor div from the image div
            image_url = image_div.img['src']            
            imageURLS.append(image_url)
            for entry in results:
                blurb = entry.find("p").text.strip()
                if blurb:
                    blurbs.append(blurb)
        else:
            blurbs.append("")
    return titles, urls, imageURLS, blurbs

URL1 = "https://www.phillyvoice.com/tags/eagles/"
URL2 = "https://www.phillyvoice.com/tags/sixers/"
URL3 = "https://www.phillyvoice.com/tags/phillies/"
URL4 = "https://www.phillyvoice.com/tags/flyers/"

titles4, urls4, imageURLS4, blurbs4 = scrape_website(URL1)
titles4a, urls4a, imageURLS4a, blurbs4a = scrape_website(URL2)
titles4b, urls4b, imageURLS4b, blurbs4b = scrape_website(URL3)
titles4c, urls4c, imageURLS4c, blurbs4c = scrape_website(URL4)

#you can then use the lists as needed. For example, you could print out the first item in each list like this:
# print(titles4[0])
# print(titles4a[0])
# print(blurbs4a[0])
# print(urls4a[0])
# print(imageURLS4a[0])