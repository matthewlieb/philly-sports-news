import requests
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        # Send a GET request to the URL and check if the response is successful
        page = requests.get(URL)
        page.raise_for_status()

        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("article", class_="nhl-c-card -default oc-card--boxed-vertical-80 -no-description")

        titles = []
        urls = []
        blurbs = []
        imageURLS = []

        for entry in results:
            # Extracting title
            title_element = entry.find("h3", class_="fa-text__title")
            if title_element:
                titles.append(title_element.text.strip())
            
            # Extracting link URL
            link_element = entry.find_parent("a")  # Find the parent <a> tag
            full_url = ""
            if link_element and link_element.has_attr('href'):
                href = link_element['href']
                # Check if the URL is absolute or relative
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = "https://www.nhl.com" + href
                urls.append(full_url)

            # Extracting image URL
            image_element = entry.find("img")
            if image_element and image_element.has_attr('src'):
                imageURLS.append(image_element['src'])
            else:
                imageURLS.append("")

            # Extracting blurb from the article page
            if full_url:
                article_page = requests.get(full_url)
                article_page.raise_for_status()
                article_soup = BeautifulSoup(article_page.content, "html.parser")
                blurb_element = article_soup.find("p", class_="nhl-c-article__summary nhl-ty-subtitle--2")
                if blurb_element:
                    blurbs.append(blurb_element.text.strip())
                else:
                    blurbs.append("")

        return titles, blurbs, urls, imageURLS
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

URL = "https://www.nhl.com/flyers/news"
titles2c, blurbs2c, urls2c, imageURLS2c = scrape_website(URL)

# # Print results to verify
# if titles2c:
#     for title, blurb, url, image in zip(titles2c, blurbs2c, urls2c, imageURLS2c):
#         print(f"Title: {title}")
#         print(f"Blurb: {blurb}")
#         print(f"URL: {url}")
#         print(f"Image URL: {image}")
#         print()