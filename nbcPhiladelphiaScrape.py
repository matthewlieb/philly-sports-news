import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    
    # Find all list items that correspond to stories
    story_items = soup.find_all("li", class_="story-card story-card__list-item")

    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    for item in story_items:
        # Extracting the title and URL
        title_tag = item.find("h3", class_="story-card__title more-news__story-card-title")
        if title_tag:
            a_tag = title_tag.find("a")  # Find the 'a' tag within the title
            if a_tag and a_tag.text and a_tag['href']:
                titles.append(a_tag.text.strip())  # Title text
                urls.append(a_tag['href'])  # URL
        
        # Extracting the image URL
        image_container = item.find("div", class_="imagewrap2 more-news__thumbnail")
        if image_container:
            img_tag = image_container.find("img")
            if img_tag and img_tag.has_attr('src'):
                imageURLS.append(img_tag['src'])  # Image URL

        # Extracting the blurb
        excerpt_div = item.find("div", class_="story-card__excerpt more-news__story-card-excerpt")
        if excerpt_div and excerpt_div.find("p"):
            blurbs.append(excerpt_div.find("p").text.strip())  # Blurb text

    return titles, urls, imageURLS, blurbs

# Test with one URL
URL1 = "https://www.nbcsports.com/philadelphia/eagles"
URL2 = "https://www.nbcsports.com/philadelphia/sixers"
URL3 = "https://www.nbcsports.com/philadelphia/phillies"
URL4 = "https://www.nbcsports.com/philadelphia/flyers"

titles3, urls3, imageURLS3, blurbs3 = scrape_website(URL1)
titles3a, urls3a, imageURLS3a, blurbs3a = scrape_website(URL2)
titles3b, urls3b, imageURLS3b, blurbs3b = scrape_website(URL3)
titles3c, urls3c, imageURLS3c, blurbs3c = scrape_website(URL4)


# # For demonstration, print out the first item in each list
# print(titles3[0])
# # print(imageURLS3[0])
