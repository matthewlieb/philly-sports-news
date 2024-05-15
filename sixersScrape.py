import requests
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
        page.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return [], [], [], []

    soup = BeautifulSoup(page.content, "html.parser")

    # Define the selectors
    article_selector = "li.ContentGrid_contentGridColumnQuarter__Uiwvc"
    title_selector = "h3.TileArticle_tileArticleTitle__lzLJZ"
    blurb_selector = "p.TileArticle_tileArticleExcerpt__NpVq1"
    link_selector = "a.TileArticle_tileLink__9vE5P"
    image_selector = "img.TileArticle_tileArticleImage__epak1"

    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    # Extracting articles
    results = soup.find_all("li", class_=article_selector)
    print(f"Found {len(results)} articles.")
    for entry in results:
        # Extracting title
        title_element = entry.find("h3", class_=title_selector)
        if title_element:
            titles.append(title_element.text.strip())
            print(f"Found title: {title_element.text.strip()}")
        else:
            titles.append("")
            print("No title found.")

        # Extracting blurb
        blurb_element = entry.find("p", class_=blurb_selector)
        if blurb_element:
            blurbs.append(blurb_element.text.strip())
            print(f"Found blurb: {blurb_element.text.strip()}")
        else:
            blurbs.append("")
            print("No blurb found.")

        # Extracting URL
        link_element = entry.find("a", class_=link_selector)
        if link_element and link_element['href']:
            href = link_element['href']
            full_url = f"https://www.nba.com{href}" if href.startswith('/') else href
            urls.append(full_url)
            print(f"Found URL: {full_url}")
        else:
            urls.append("")
            print("No URL found.")

        # Extracting image URL
        image_element = entry.find("img", class_=image_selector)
        if image_element and image_element.get("src"):
            imageURL = image_element["src"]
            if "https://" in imageURL:
                imageURLS.append(imageURL)
                print(f"Found image URL: {imageURL}")
            else:
                imageURLS.append("")
                print("No valid image URL found.")
        else:
            imageURLS.append("")
            print("No image found.")

    return titles, blurbs, urls, imageURLS

URL = "https://www.nba.com/sixers/archives"
titles2a, blurbs2a, urls2a, imageURLS2a = scrape_website(URL)

# Print out the first few items for testing
for i in range(min(6, len(titles2a))):  # Ensuring not to go out of index
    print("Title:", titles2a[i])
    print("Blurb:", blurbs2a[i])
    print("URL:", urls2a[i])
    print("Image URL:", imageURLS2a[i], "\n")
