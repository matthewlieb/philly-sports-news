import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        # Create soup object, set results to desired elements
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("div", {"class":"article"})

        # Set up lists to store scraped data
        titles = []
        urls = []
        imageURLS = []
        blurbs = []

        # Loop through the sub elements, extract relevant data, add to arrays
        for result in results:
            title_element = result.find("h3", class_="title")
            blurb = result.find("a", class_="excerpt")
            if blurb is not None:
                blurbs.append(blurb.text.strip())

            if title_element is not None:  # Check if the element was found
                title = title_element.text.strip()
                titles.append(title)

                link = result.find("a")
                if link is not None:
                    link_url = link["href"]
                    urls.append(link_url)

                image = result.find("a", class_="article-image")
                if image is not None:
                    if image.get('data-original') is not None:
                        imageURL = image['data-original']
                    else:
                        imageURL = image['style'][22:-2]
                    imageURLS.append(imageURL)

        return titles, urls, imageURLS, blurbs
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

def scrape_website2(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        # Create soup object, set results to desired elements
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("article", {"class":"style_1juuhkm-o_O-wrapper_1wgo221"})

        # Set up lists to store scraped data
        titles = []
        urls = []
        imageURLS = []
        blurbs = []

        # Loop through the sub elements, extract relevant data, add to arrays
        for result in results:
    
            title_element = result.find("h3")
            if title_element is not None:  # Check if the element was found
                title = title_element.text.strip()
                titles.append(title)

            link = result.find("a")
            if link is not None:
                link_url = link["href"]
                urls.append(link_url)
        
        for url in urls:
            page = requests.get(url)
            page.raise_for_status()

            # Create soup object, set results to desired elements
            soup = BeautifulSoup(page.content, "html.parser")
            blurb= soup.find("p")
            if blurb is not None:
                blurbs.append(blurb.text.strip())
            
            imageElement = soup.find("div", class_="wrapper_ctua91")
            if imageElement is not None:
                imageURL = imageElement.find("img", class_="base_1emrqjj")
                imageURLS.append(imageURL.get('src'))

        return titles, urls, blurbs, imageURLS
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

URL1 = "https://insidetheiggles.com/philadelphia-eagles-news/"
URL2 = "https://thesixersense.com/philadelphia-76ers-news/"
URL3 = "https://thatballsouttahere.com/philadelphia-phillies-news/"
URL4 = "https://broadstreetbuzz.com/philadelphia-flyers-news/"

titles5, urls5, imageURLS5, blurbs5 = scrape_website(URL1)
titles5a, urls5a, imageURLS5a, blurbs5a = scrape_website(URL2)
titles5b, urls5b, blurbs5b, imageURLS5b = scrape_website2(URL3)
titles5c, urls5c, imageURLS5c, blurbs5c = scrape_website(URL4)

# for i in range(6):
#     print("\n")
#     print(titles5b[i])
#     print(urls5b[i])
#     print(blurbs5b[i])
#     print(imageURLS5b[i])
#     print("\n")

# You can then use the lists as needed. For example, you could print out the first item in each list like this:
# print(titles5[0])
# print(titles5a[0])

# print(titles5a[0])
# print(imageURLS5a[0])
# print("\n")
# print(titles5[1])
# print(imageURLS5[1])
# print("\n")
# print(titles5[2])
# print(imageURLS5[2])
# print("\n")
# print(titles5[3])
# print(imageURLS5[3])
# print("\n")



