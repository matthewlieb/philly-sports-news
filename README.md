<img width="468" alt="image" src="https://user-images.githubusercontent.com/4676246/227815885-fd616655-c1a8-436b-ba81-2b6f1cee8026.png">

# Philly Sports News 🔍

Philly Sports News is a web application that displays the latest news on the Philadelphia Eagles, Sixers, Phillies, and Flyers. The site uses Beautiful Soup 4 to scrape the web for the latest news articles. The YouTube API is used to deliver the latest YouTube videos for each team. The site is designed using custom CSS, and Bootstrap. And Flask is used for the web framework. 

## Features ✨

- Latest headlines for Eagles, Sixers, Phillies, and Flyers news 🚀
- YouTube videos featuring updates on Philly sports news 🌟
- Betting odds for latest matches 🎉

## Installation 🛠️

To install Philly Sports News, follow these steps:

1. Clone this repository: `git clone https://github.com/matthewlieb/philly-sports-news.git`
2. Navigate to the directory where you cloned the repository: `cd philly-sports-news`
3. Install the required packages: `pip install -r requirements.txt`
4. Obtain unique YouTube API keys and add them to `config.py`
5. Run the app: `python3 app.py`

## Usage 🚀

The project is hosted using Heroku and can be found at https://www.phillysportdaily.com. The latest news is displayed for the Eagles by default, but switching pages will provide Sixers news, Phillies news, and Flyers news. A ticker displays headlines at the top of the page. Random YouTube videos are embedded, and a widget shows the latest betting odds.

## Contributing 🤝

Anyone is welcome to contribute to the development of Philly Sports News. To contribute:

1. Fork the repository
2. Make your changes and commit them to your forked repository
3. Create a pull request to this repository

## License 📝

This project does not yet have a license. 

## Contact 📞

If you have any questions or suggestions regarding Philly Sports News, feel free to reach out to me via GitHub or LinkedIn:

- GitHub: https://github.com/matthewlieb
- LinkedIn: https://www.linkedin.com/in/matthew-lieb/

## Acknowledgements 🙏

Special thanks to this YouTube video for inspiration: https://www.youtube.com/watch?v=gvdSkBmjpbY&t=568s. 

The project file structure is as follows:

- README.md
- static/
- templates/
- Procfile
- app.py
- config.py
- eaglesScrape.py
- fansidedScrape.py
- flyersScrape.py
- nbcPhiladelphiaScrape.py
- philliesScrape.py
- phillyVoiceScrape.py
- rateLimiter.py
- requirements.txt
- sbNationScrape.py
- sixersScrape.py

Note: The `static/` directory contains static files like CSS and images, and the `templates/` directory contains the HTML templates.



