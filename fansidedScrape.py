import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        # Create soup object, set results to desired elements
        soup = BeautifulSoup(page.content, "html.parser")

        results = soup.find_all("a", {"class":"articleLink_1iblg8d"})
        #print(results)

        # Set up lists to store scraped data
        titles = []
        urls = []
        imageURLS = []
        blurbs = []

        # Loop through the sub elements, extract relevant data, add to arrays
        for result in results:
            title_element = result.get("title")
            if title_element:
                titles.append(title_element)
                print(title_element)

            link = result.get('href')
            if link:
                urls.append(link)
                print(link)
            
            article_page = requests.get(link)
            article_soup = BeautifulSoup(article_page.content, "html.parser")
            
            # Find the picture tag with the specific class
            picture_tag = article_soup.find("picture", class_="base_1emrqjj")
            image_url = None
            if picture_tag:
                # Find the nested <img> tag within <picture>
                img_tag = picture_tag.find("img")
                if img_tag and img_tag.has_attr('src'):
                    image_url = img_tag['src']
            print(image_url)
            imageURLS.append(image_url)

            # Extract the blurb (article description)
            blurb_tag = article_soup.find("meta", {"name": "description"})
            blurb = blurb_tag['content'] if blurb_tag else "No blurb found"            
            print(blurb)
            blurbs.append(blurb)

        return titles, urls, imageURLS, blurbs
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

URL1 = "https://insidetheiggles.com/philadelphia-eagles-news/"
URL2 = "https://thesixersense.com/philadelphia-76ers-news/"
URL3 = "https://thatballsouttahere.com/philadelphia-phillies-news/"
URL4 = "https://broadstreetbuzz.com/philadelphia-flyers-news/"

titles5, urls5, imageURLS5, blurbs5 = scrape_website(URL1)
titles5a, urls5a, imageURLS5a, blurbs5a = scrape_website(URL2)
titles5b, urls5b, blurbs5b, imageURLS5b = scrape_website(URL3)
titles5c, urls5c, imageURLS5c, blurbs5c = scrape_website(URL4)