import requests 
from bs4 import BeautifulSoup

def scrape_website(URL):
    try:
        page = requests.get(URL)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None, None, None, None
    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("div", {"class":"brand-font tile-article-link-wrapper TileArticle_tileArticleLinkWrapper__k0V39"})

    titles = []
    urls = []
    blurbs = []
    imageURLS = []

    images = soup.find_all("img", class_="TileArticle_tileArticleImage__epak1")
    image1 = soup.find("span", class_="bg-cover bg-center overflow-hidden rounded-t-md md:rounded-l-md md:rounded-tr-none h-full group-hover:scale-105 transform transition duration-500 ease-in-out block motion-reduce:transform-none")
    if image1:
        imageURL1 = image1.get("style")[97:-1]
        imageURLS.append(imageURL1)

    for image in images:
        imageURL = image.get("src")
        if imageURL and "https://" in imageURL:
            imageURLS.append(imageURL)

    for entry in results:
        title_element = entry.find("h3")
        blurb = entry.find("p").text.strip()
        if title_element: 
            title = title_element.text.strip()
            titles.append(title)
            blurbs.append(blurb)
            link = entry.find("a")
            if link:
                link_url = link["href"]
                urls.append("https:/nba.com" + str(link_url))
    return titles, blurbs, urls, imageURLS

URL = "https://www.nba.com/sixers/archives"
titles2a, blurbs2a, urls2a, imageURLS2a = scrape_website(URL)


# print("\n")
# for i in range(6):
#     print(titles2a[i])
#     print(blurbs2a[i])
#     print(urls2a[i])
#     print(imageURLS2a[i])
#     print("\n")