import requests 
from bs4 import BeautifulSoup
from articleEnhancer import enhance_article_data

def scrape_website(URL):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        page = requests.get(URL, headers=headers, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
        
        # Find all list items that correspond to stories
        story_items = soup.find_all("li", class_="story-card story-card__list-item")

        titles = []
        urls = []
        blurbs = []
        imageURLS = []
        authors = []

        for item in story_items:
            # Extracting the title and URL
            title_tag = item.find("h3", class_="story-card__title more-news__story-card-title")
            if title_tag:
                a_tag = title_tag.find("a")  # Find the 'a' tag within the title
                if a_tag and a_tag.text and a_tag.get('href'):
                    titles.append(a_tag.text.strip())  # Title text
                    url = a_tag['href']
                    if not url.startswith('http'):
                        url = 'https://www.nbcsports.com' + url
                    urls.append(url)  # URL
                else:
                    titles.append("")
                    urls.append("")
            else:
                titles.append("")
                urls.append("")
            
            # Extracting the image URL
            image_container = item.find("div", class_="imagewrap2 more-news__thumbnail")
            if image_container:
                img_tag = image_container.find("img")
                if img_tag and img_tag.has_attr('src'):
                    img_src = img_tag['src']
                    if not img_src.startswith('http'):
                        img_src = 'https://www.nbcsports.com' + img_src
                    imageURLS.append(img_src)  # Image URL
                else:
                    imageURLS.append(None)
            else:
                imageURLS.append(None)

            # Extracting the blurb
            excerpt_div = item.find("div", class_="story-card__excerpt more-news__story-card-excerpt")
            if excerpt_div and excerpt_div.find("p"):
                blurbs.append(excerpt_div.find("p").text.strip())  # Blurb text
            else:
                blurbs.append("")
            
            # Add author (NBC Sports site doesn't show authors in list view, so use default)
            authors.append("-- NBC Sports Philadelphia")

        return titles, urls, imageURLS, blurbs, authors
    except requests.exceptions.RequestException as e:
        print(f"An error occurred scraping {URL}: {e}")
        return [], [], [], [], []
    except Exception as e:
        print(f"Unexpected error scraping {URL}: {e}")
        return [], [], [], [], []

# Test with one URL
URL1 = "https://www.nbcsports.com/philadelphia/eagles"
URL2 = "https://www.nbcsports.com/philadelphia/sixers"
URL3 = "https://www.nbcsports.com/philadelphia/phillies"
URL4 = "https://www.nbcsports.com/philadelphia/flyers"

titles3, urls3, imageURLS3, blurbs3, authors3 = scrape_website(URL1)
titles3a, urls3a, imageURLS3a, blurbs3a, authors3a = scrape_website(URL2)
titles3b, urls3b, imageURLS3b, blurbs3b, authors3b = scrape_website(URL3)
titles3c, urls3c, imageURLS3c, blurbs3c, authors3c = scrape_website(URL4)

# Enhance all articles to ensure complete data for every card
print("Enhancing NBC Sports articles with complete data...")
if titles3 and urls3:
    titles3, urls3, imageURLS3, blurbs3, authors3 = enhance_article_data(
        titles3, urls3, imageURLS3, blurbs3, authors3, max_enhance=10, enhance_all=True
    )
if titles3a and urls3a:
    titles3a, urls3a, imageURLS3a, blurbs3a, authors3a = enhance_article_data(
        titles3a, urls3a, imageURLS3a, blurbs3a, authors3a, max_enhance=10, enhance_all=True
    )
if titles3b and urls3b:
    titles3b, urls3b, imageURLS3b, blurbs3b, authors3b = enhance_article_data(
        titles3b, urls3b, imageURLS3b, blurbs3b, authors3b, max_enhance=10, enhance_all=True
    )
if titles3c and urls3c:
    titles3c, urls3c, imageURLS3c, blurbs3c, authors3c = enhance_article_data(
        titles3c, urls3c, imageURLS3c, blurbs3c, authors3c, max_enhance=10, enhance_all=True
    )


# # For demonstration, print out the first item in each list
# print(titles3[0])
# # print(imageURLS3[0])
