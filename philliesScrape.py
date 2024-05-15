import requests
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
        page.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: Unable to connect to website. {e}")
        return None

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("article", class_="article-item")
    
    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    for entry in results:
        # Extracting title
        title_element = entry.find("h1", class_="article-item__headline")
        if title_element:
            titles.append(title_element.text.strip())
        else:
            titles.append("")

        # Extracting link URL
        link_element = entry.find("a", href=True)
        if link_element:
            href = link_element['href']
            full_url = href if href.startswith('http') else f"https://www.mlb.com{href}"
            urls.append(full_url)
        else:
            urls.append("")

        # Extracting image URL
        image_element = entry.find("img", class_="lazyload")
        if image_element and image_element.has_attr('data-srcset'):
            image_url = image_element['data-srcset'].split(",")[0].strip().split(" ")[0]
            imageURLS.append(image_url)
        else:
            imageURLS.append("")

        # Extracting blurb (in this case, using description as a proxy)
        blurb_element = entry.find("p", class_="article-item__contributor-date")
        if blurb_element:
            blurb = blurb_element.text.strip()
            blurbs.append(blurb)
        else:
            blurbs.append("")

    return titles, blurbs, urls, imageURLS

URL = "https://www.mlb.com/phillies/news"
titles2b, blurbs2b, urls2b, imageURLS2b = scrape_website(URL)

# # Print results to verify
# if titles2b:
#     for title, blurb, url, image in zip(titles2b, blurbs2b, urls2b, imageURLS2b):
#         print(f"Title: {title}")
#         print(f"Blurb: {blurb}")
#         print(f"URL: {url}")
#         print(f"Image URL: {image}")
#         print()
