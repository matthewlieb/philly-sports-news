from jinja2 import Template
from rateLimiter import *
from flask import Flask

from sbNationScrape import *
from nbcPhiladelphiaScrape import *
from phillyVoiceScrape import *
from fansidedScrape import * 

from eaglesScrape import *
from sixersScrape import *
from philliesScrape import *
from flyersScrape import *

app = Flask(__name__)

def create_dict(titles, urls):

    return {k: v for k, v in zip(titles[:5], urls[:5])}

@app.route('/')
def home():
    dict1 = create_dict(titles1, urls1)
    dict2 = create_dict(titles2, urls2)
    dict3 = create_dict(titles3, urls3)
    dict4 = create_dict(titles4, urls4)
    dict5 = create_dict(titles5, urls5)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}
   
    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    # Create a new dictionary from the shuffled list
    shuffled_dict = dict(combined_list)
    keys = list(shuffled_dict.keys())
    values = list(shuffled_dict.values())

    video_id = eagles_request()

    # Create the embed code for the embeddable and available video
    embed_code = '<iframe width="560" height="315" src="https://www.youtube.com/embed/' + video_id + '" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    # Read the contents of the template file into a string
    with open('templates/index.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html = template.render(zip=zip, column1=titles1, column2=titles2, column3=titles3, column4=titles4, column5=titles5, urls1=urls1, urls2=urls2, urls3=urls3, urls4=urls4, urls5=urls5, imageURLS1=imageURLS1, imageURLS2=imageURLS2, imageURLS3=imageURLS3,imageURLS4=imageURLS4, imageURLS5=imageURLS5, keys=keys, values=values, embed_code=embed_code, blurbs1=blurbs1, blurbs2=blurbs2, blurbs3=blurbs3, blurbs4=blurbs4, blurbs5=blurbs5)

    return html

@app.route('/sixers')
def sixers():
    dict1 = create_dict(titles1a, urls1a)
    dict2 = create_dict(titles2a, urls2a)
    dict3 = create_dict(titles3a, urls3a)
    dict4 = create_dict(titles4a, urls4a)
    dict5 = create_dict(titles5a, urls5a)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}

    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    # Create a new dictionary from the shuffled list
    shuffled_dict = dict(combined_list)
    keys1 = list(shuffled_dict.keys())
    values1 = list(shuffled_dict.values())

    video_id = sixers_request()

    # Create the embed code for the embeddable and available video
    embed_code1 = '<iframe width="560" height="315" src="https://www.youtube.com/embed/' + video_id + '" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    # Read the contents of the template file into a string
    with open('templates/index2a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html2 = template.render(zip1=zip, column1a=titles1a, column2a=titles2a, column3a=titles3a, column4a=titles4a, column5a=titles5a, urls1a=urls1a, urls2a=urls2a, urls3a=urls3a, urls4a=urls4a, urls5a=urls5a, imageURLS1a=imageURLS1a, imageURLS2a=imageURLS2a, imageURLS3a=imageURLS3a, imageURLS4a=imageURLS4a, imageURLS5a=imageURLS5a, keys1=keys1, values1=values1, embed_code1=embed_code1, blurbs1a=blurbs1a, blurbs2a=blurbs2a, blurbs3a=blurbs3a, blurbs4a=blurbs4a, blurbs5a=blurbs5a)

    return html2

@app.route('/phillies')
def phillies():
    dict1 = create_dict(titles1b, urls1b)
    dict2 = create_dict(titles2b, urls2b)
    dict3 = create_dict(titles3b, urls3b)
    dict4 = create_dict(titles4b, urls4b)
    dict5 = create_dict(titles5b, urls5b)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}

    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    shuffled_dict = dict(combined_list)
    keys2 = list(shuffled_dict.keys())
    values2 = list(shuffled_dict.values())

    video_id = phillies_request()

    # Create the embed code for the embeddable and available video
    embed_code2 = '<iframe width="560" height="315" src="https://www.youtube.com/embed/' + video_id + '" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    # Read the contents of the template file into a string
    with open('templates/index3a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html3 = template.render(zip2=zip, column1b=titles1b, column2b=titles2b, column3b=titles3b, column4b=titles4b, column5b=titles5b, urls1b=urls1b, urls2b=urls2b, urls3b=urls3b, urls4b=urls4b, urls5b=urls5b, imageURLS1b=imageURLS1b,imageURLS2b=imageURLS2b, imageURLS3b=imageURLS3b, imageURLS4b=imageURLS4b, imageURLS5b=imageURLS5b, keys2=keys2, values2=values2, embed_code2=embed_code2, blurbs1b=blurbs1b, blurbs2b=blurbs2b, blurbs3b=blurbs3b, blurbs4b=blurbs4b, blurbs5b=blurbs5b)

    return html3

@app.route('/flyers')
def flyers():
    dict1 = create_dict(titles1c, urls1c)
    dict2 = create_dict(titles2c, urls2c)
    dict3 = create_dict(titles3c, urls3c)
    dict4 = create_dict(titles4c, urls4c)
    dict5 = create_dict(titles5c, urls5c)

    combined_dict = {**dict1, **dict2, **dict3, **dict4, **dict5}

    # Convert the dictionary to a list of tuples
    combined_list = list(combined_dict.items())

    # Shuffle the list
    random.shuffle(combined_list)

    shuffled_dict = dict(combined_list)
    keys3 = list(shuffled_dict.keys())
    values3 = list(shuffled_dict.values())

    video_id = flyers_request()

    # Create the embed code for the embeddable and available video
    embed_code3 = '<iframe width="560" height="315" src="https://www.youtube.com/embed/' + video_id + '" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    # Read the contents of the template file into a string
    with open('templates/index4a.html', 'r') as f:
        template_str = f.read()

    # Create a Template object from the template string
    template = Template(template_str)

    # Render the template with the headlines and URLs
    html4 = template.render(zip3=zip, column1c=titles1c, column2c=titles2c, column3c=titles3c, column4c=titles4c, column5c=titles5c, urls1c=urls1c, urls2c=urls2c, urls3c=urls3c, urls4c=urls4c, urls5c=urls5c, imageURLS1c=imageURLS1c,imageURLS2c=imageURLS2c, imageURLS3c=imageURLS3c, imageURLS4c=imageURLS4c, imageURLS5c=imageURLS5c, keys3=keys3, values3=values3, embed_code3=embed_code3, blurbs1c=blurbs1c, blurbs2c=blurbs2c, blurbs3c=blurbs3c, blurbs4c=blurbs4c, blurbs5c=blurbs5c)

    return html4

if __name__ == '__main__':
    app.run()
