from selenium import webdriver
import datetime
import re
import os
from flask import Flask
from flask import request
from time import time
app = Flask(__name__)


def formaturl(url):
    if not re.match('(?:http|ftp|https)://', url):
        return 'http://{}'.format(url)
    return url

# Below function is an example to test the API giving it a body as a request and getting it back as a response
@app.route('/leyton/API/v1/apitrial', methods=['POST'])
def api_trial():
    req = request.json
    return {"result": {"request": req}}, 200

@app.route('/leyton/API/v1/rendtime', methods=['POST'])
def get_rendtime():
    url = formaturl(request.json["url"])
    options = webdriver.FirefoxOptions()
    # options.add_argument("disable-gpu")
    options.add_argument("--headless")
    # options.add_argument("no-default-browser-check")
    options.add_argument("--window-size=1366,768")
    driver = webdriver.Firefox(options=options)
    start = time()
    driver.get(url)
    b = datetime.datetime.now()
    loading_time = round((time() - start),2)
    return {"results": {"redering_time_s": loading_time}}, 200

if __name__ == '__main__':
    # define the localhost ip and the port that is going to be used
    # in some future article, we are going to use an env variable instead a hardcoded port 
    app.run(host='0.0.0.0', port=os.getenv('PORT'))
