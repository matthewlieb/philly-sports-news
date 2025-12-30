import requests 
from bs4 import BeautifulSoup
from articleEnhancer import enhance_article_data

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
        authors = []

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
            else:
                urls.append("")
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                article_page = requests.get(link, headers=headers, timeout=10)
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
                
                # Try to find author
                author_tag = article_soup.find("span", class_="c-byline__author-name") or article_soup.find("a", class_="c-byline__author-name")
                if author_tag:
                    authors.append("-- " + author_tag.get_text().strip())
                else:
                    authors.append("-- FanSided")
                    
            except Exception as e:
                print(f"Error processing article {link}: {e}")
                imageURLS.append(None)
                blurbs.append("")
                authors.append("-- FanSided")

        return titles, urls, imageURLS, blurbs, authors
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None

URL1 = "https://insidetheiggles.com/philadelphia-eagles-news/"
URL2 = "https://thesixersense.com/philadelphia-76ers-news/"
URL3 = "https://thatballsouttahere.com/philadelphia-phillies-news/"
URL4 = "https://broadstreetbuzz.com/philadelphia-flyers-news/"

titles5, urls5, imageURLS5, blurbs5, authors5 = scrape_website(URL1)
titles5a, urls5a, imageURLS5a, blurbs5a, authors5a = scrape_website(URL2)
titles5b, urls5b, imageURLS5b, blurbs5b, authors5b = scrape_website(URL3)
titles5c, urls5c, imageURLS5c, blurbs5c, authors5c = scrape_website(URL4)

# Enhance all articles to ensure complete data for every card
# Note: FanSided already fetches from individual pages, but we'll enhance to ensure completeness
print("Enhancing FanSided articles with complete data...")
if titles5 and urls5:
    titles5, urls5, imageURLS5, blurbs5, authors5 = enhance_article_data(
        titles5, urls5, imageURLS5, blurbs5, authors5, max_enhance=10, enhance_all=True
    )
if titles5a and urls5a:
    titles5a, urls5a, imageURLS5a, blurbs5a, authors5a = enhance_article_data(
        titles5a, urls5a, imageURLS5a, blurbs5a, authors5a, max_enhance=10, enhance_all=True
    )
if titles5b and urls5b:
    titles5b, urls5b, imageURLS5b, blurbs5b, authors5b = enhance_article_data(
        titles5b, urls5b, imageURLS5b, blurbs5b, authors5b, max_enhance=10, enhance_all=True
    )
if titles5c and urls5c:
    titles5c, urls5c, imageURLS5c, blurbs5c, authors5c = enhance_article_data(
        titles5c, urls5c, imageURLS5c, blurbs5c, authors5c, max_enhance=10, enhance_all=True
    )

# print(titles5[0])