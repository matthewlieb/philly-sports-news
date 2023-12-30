import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return [], [], [], []
    soup = BeautifulSoup(page.content, "html.parser")

    # Define the class selectors
    article_selector = "div.brand-font.tile-article-link-wrapper.TileArticle_tileArticleLinkWrapper__k0V39"
    image_selector = "img.TileArticle_tileArticleImage__epak1"

    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    # Extracting image URLs
    images = soup.find_all(image_selector)
    for image in images:
        imageURL = image.get("src")
        if imageURL and "https://" in imageURL:
            imageURLS.append(imageURL)

    # Extracting articles
    results = soup.find_all(article_selector)
    for entry in results:
        title_element = entry.find("h3")
        blurb_element = entry.find("p")
        
        if title_element: 
            titles.append(title_element.text.strip())
        
        if blurb_element:
            blurbs.append(blurb_element.text.strip())
        
        link_element = entry.find("a")
        if link_element and link_element.has_attr("href"):
            urls.append(link_element['href'])  # Adjust base URL if needed

    return titles, blurbs, urls, imageURLS

URL = "https://www.nba.com/sixers/archives"
titles2a, blurbs2a, urls2a, imageURLS2a = scrape_website(URL)

# Print out the first few items for testing
# for i in range(min(6, len(titles2a))):  # Ensuring not to go out of index
#     print("Title:", titles2a[i])
#     print("Blurb:", blurbs2a[i])
#     print("URL:", urls2a[i])
#     print("Image URL:", imageURLS2a[i], "\n")
