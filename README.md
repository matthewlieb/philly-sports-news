# philly-sports-news

Project description: 

This is a project I made using primarily HTML, Python, and CSS which scrapes the web for the latest news on the Philadelphia Eagles, Sixers, Phillies, and Flyers. The site uses Beautiful Soup 4 to scrape the web for the latest news articles. The YouTube API is used to deliver the latest YouTube videos for each team. The site is designed using custom CSS, and Bootstrap. And Flask is used for the web framework.

Installation instructions: 

The project is hosted using Heroku and can be found at https://www.phillysportdaily.com. To run the project locally, download the files into a directory, navigate to the directory, and run the app.py file using ‘python3 app.py’. It may take a few moments, but this should run the app on a local host, which can be launched in any browser. 

Usage instructions: 

To use the project, ensure that all files from the GitHub repo are downloaded in a single directory. Open a terminal and navigate to that directory using ‘cd [DIRECTORY PATH]’. Once in the project directory, the app can be run using ‘python3 app.py’. Changes can be made to any of the files in the directory to customize the web app as desired. However, unique API keys are required to avoid rate limits and security issues. 

Project structure: 

The web app is structured as follows:

Philly-Sports-News

Procfile
app.py
config.py
eaglesScrape.py
fansidedScrape.py
flyersScrape.py
nbcPhiladelphiaScrape.py
philliesScrape.py
phillyVoiceScrape.py
rateLimiter.py
requirements.txt
sbNationScrape.py
sixersScrape.py
-------> static
	-------> phillySportsNewsEagles.png
	-------> phillySportsNewsSixers.png
	-------> phillySportsNewsPhillies.png
	-------> phillySportsNewsFlyers.png
	-------> phillySports.css
-------> templates
	-------> index.html
	-------> index2a.html
	-------> index3a.html
	-------> index4a.html

