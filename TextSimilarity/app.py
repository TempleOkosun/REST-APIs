"""
Chart of API
---------------
Resource             Address     Protocol   Params              Responses
----------------------------------------------------------------------------------------------
Register            /register    POST       username,           200 OK
                                            password            301: Invalid username

Detect              /detect      POST       username,           200 OK: return similarity
                                            password,           301: Invalid username
                                            text1,              302: Invalid password
                                            text2               303: Out of tokens

Refill              /refill      POST       username,           200 OK
                                            admin_password      301: Invalid username
                                            refill_amount       302: Invalid admin password
"""


from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import spacy

# Construct a Flask application
app = Flask(__name__)
api = Api(app)  # Initialize that the app will be an API

# Connect to MongoDB and create a new database as well as collection
client = MongoClient("mongodb://localhost:27017")
db = client.SimilarityDB
users = db["Users"]


def user_exist(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


# Implement the class Register inheriting from Resource
class Register(Resource):
    def post(self):
        # Get the posted data
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]

        if user_exist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username."
            }
            return jsonify(retJson)

        hashed_pwd = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        users.insert(
            {
                "Username": username,
                "Password": hashed_pwd,
                "Tokens": 6
            }
        )
        retJson = {
            "staus": 200,
            "msg": "You have successfully registered for the API."
        }
        return jsonify(retJson)


def verify_pwd(username, password):
    if not user_exist(username):
        return False

    hashed_pwd = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode("utf8"), hashed_pwd) == hashed_pwd:
        return True
    else:
        return False


def count_tokens(username):
    tokens = users.find(
        {
            "Username": username,
        }
    )[0]["Tokens"]
    return tokens


class Detect(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        text1 = posted_data["text1"]
        text2 = posted_data["text2"]

        if not user_exist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        correct_pwd = verify_pwd(username, password)

        if not correct_pwd:
            retJson = {
                "status": 302,
                "msg": "Invalid Password"
            }
            return jsonify(retJson)

        num_tokens = count_tokens(username)

        if num_tokens <= 0:
            retJson = {
                "status": 303,
                "msg": "You are out of tokens pls refill"
            }
            return jsonify(retJson)

        # calculate the edit distance
        nlp = spacy.load('en_core_web_sm')

        text1 = nlp(text1)
        text2 = nlp(text2)

        # ratio is a number between 0 and 1 the closer to 1, the more similar text1 and text2 are.

        ratio = text1.similarity(text2)

        retJson = {
            "status": 200,
            "similarity": ratio,
            "msg": "Similarity score calculated successfully"
        }

        current_tokens = count_tokens(username)

        users.update(
            {
                "Username": username,
            }, {
                "$set": {
                    "Tokens": current_tokens - 1
                }
            }
        )

        return jsonify(retJson)


class Refill(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["admin_pwd"]
        refill_amount = posted_data["refill"]

        if not user_exist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        correct_pw = "abc123"

        if not password == correct_pw:
            retJson = {
                "status": 304,
                "msg": "Invalid Admin Password"
            }
            return jsonify(retJson)

        current_tokens = count_tokens(username)
        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": refill_amount + current_tokens
            }
        })

        retJson = {
            "status": 200,
            "msg": "Refilled successfully"
        }
        return jsonify(retJson)


api.add_resource(Register, "/register")
api.add_resource(Detect, "/detect")
api.add_resource(Refill, "/refill")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
