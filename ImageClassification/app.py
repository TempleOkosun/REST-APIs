"""
Chart of API
---------------
Resource            Address     Protocol    Param               Responses
----------------------------------------------------------------------------------------------
Register            /register    POST       username,           200 OK
                                            password            301: Invalid username

Classify            /classify    POST       username,           200 OK: return predictions
                                            password,           301: Invalid username
                                            image_url           302: Invalid password
                                                                303: Out of tokens

Refill              /refill      POST       username,           200 OK
                                            admin_password      301: Invalid username
                                            refill_amount       302: Invalid admin password
"""

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json


# noinspection DuplicatedCode
app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://localhost:27017")
db = client.ImageRecognition
users = db["Users"]


def user_exists(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        if user_exists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username."
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        users.insert(
            {
                "Username": username,
                "Password": hashed_pw,
                "Tokens": 5
            }
        )
        retJson = {
            "status": 200,
            "msg": "You successfully signed up for this API."
        }
        return jsonify(retJson)


def verify_credentials(username, password):
    if not user_exists(username):
        return generate_return_dict(301, "Invalid Username"), True

    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return generate_return_dict(302, "Invalid Password"), True
    return None, False


def verify_pw(username, password):
    if not user_exists(username):
        return False

    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode("utf8"), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def generate_return_dict(status, msg):
    retJson = {
        "status": status,
        "msg": msg
    }
    return retJson

    pass


class Classify(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        url = posted_data["url"]

        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)

        tokens = users.find({
            "Username": username
        })[0]["Tokens"]

        if tokens <= 0:
            return jsonify(generate_return_dict(303, "Not enough tokens!."))

        r = requests.get(url)
        retJson = {}

        with open('temp.jpg', 'wb') as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg',
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            ret = proc.communicate()[0]
            proc.wait()
            with open("text.txt") as f:
                retJson = json.load(f)

        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": tokens - 1
            }
        })
        return retJson


class Refill(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["admin_pw"]
        amount = posted_data["amount"]

        if not user_exists():
            return jsonify(generate_return_dict(301, "Invalid Username."))

        correct_pw = "abc123"

        if not password == correct_pw:
            return jsonify(generate_return_dict(301, "Invalid admin password."))

        users.update({
            "Username": username
        }, {
            "#set": {
                "Tokens": amount
            }
        })

        return jsonify(generate_return_dict(200, "Refilled successfully"))


api.add_resource(Register, "/register")
api.add_resource(Classify, "/classify")
api.add_resource(Refill, "/refill")

if __name__ == "__main__":
    app.run(host="0.0.0.0")
