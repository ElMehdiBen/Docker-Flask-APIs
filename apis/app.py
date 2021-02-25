import os
from flask import Flask
from flask import request
app = Flask(__name__)

# Below function is an example to test the API giving it a body as a request and getting it back as a response
@app.route('/leyton/API/v1/apitrial', methods=['POST'])
def api_trial():
    req = request.json
    return {"result": {"request": req}}, 200


if __name__ == '__main__':
    # define the localhost ip and the port that is going to be used
    # in some future article, we are going to use an env variable instead a hardcoded port 
    app.run(host='0.0.0.0', port=os.getenv('PORT'))
