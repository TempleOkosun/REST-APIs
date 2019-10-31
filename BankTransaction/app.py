
"""
Chart of API
---------------
Resource            Address        Protocol        Params              Responses
----------------------------------------------------------------------------------------------
Register            /register       POST           username,           200 OK
                                                   password            301: Invalid username

Add                 /add            POST           username,           200 OK: return similarity
                                                   password,           301: Invalid username
                                                   Amount              302: Invalid password
                                                                       304: Invalid Amount

Withdraw            /withdraw       POST           username,           200 OK: return similarity
                                                   password,           301: Invalid username
                                                   Amount              302: Invalid password
                                                                       303: Insufficient Funds
                                                                       304: Invalid Amount


Transfer             /transfer       POST          username,           200 OK: return similarity
                                                   password,           301: Invalid username
                                                   Amount              302: Invalid password
                                                   username2           303: Insufficient Funds
                                                                       304: Invalid Amount


Balance              /balance        POST          username,           200 OK
                                                   password            301: Invalid username


TakeLoan             /take-loan      POST          username,           200 OK
                                                   password            301: Invalid username
                                                   amount              304: Invalid Amount


Pay Loan            /refill          POST          username,           200 OK
                                                   password            301: Invalid username
                                                   amount              304: Invalid Amount

"""


from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

# Construct a Flask application
app = Flask(__name__)
api = Api(app)  # Initialize the app to be an API

# Connect to MongoDB and create a new database as well as collection
client = MongoClient("mongodb://localhost:27017")
db = client.BankAPI
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
                "Own": 0,
                "Debt":0
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


def user_balance(username):
    balance = users.find(
        {
            "Username": username,
        }
    )[0]["Own"]
    return balance


def user_debt(username):
    debt = users.find(
        {
            "Username": username,
        }
    )[0]["Debt"]
    return debt


def generate_return_dict(status, msg):
    retJson = {
        "status": status,
        "msg": msg
    }
    return retJson


def verify_credentials(username, password):
    if not user_exist(username):
        return generate_return_dict(301, "Invalid Username"), True

    correct_pw = verify_pwd(username, password)
    if not correct_pw:
        return generate_return_dict(302, "Incorrect Password"), True

    return None, False


def update_account(username, balance):
    users.update(
        {"Username": username}, {"$set": {"Own": balance}}
    )


def update_debt(username, balance):
    users.update({"Username": username},
                 {"$set": {"Debt": balance}})


class Add(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return jsonify(retJson)

        if money <= 0:
            return jsonify(generate_return_dict(304, "Invalid amount"))

        cash = user_balance(username)
        money -= 1
        bank_cash = user_balance("BANK")
        update_account("BANK", bank_cash + 1)
        update_account(username, cash + money)

        return jsonify(generate_return_dict(200, "Amount successfully added."))


class Transfer(Resource):
    def post(self):

        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        to = posted_data["to"]
        money = posted_data["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return jsonify(retJson)

        cash = user_balance(username)
        if cash <= 0:
            return jsonify(generate_return_dict(304, "Insufficient funds, please add or take a loan."))

        if not user_exist(to):
            return jsonify(301, "Receiver username is invalid.")

        cash_from = user_balance(username)
        cash_to = user_balance(to)
        bank_cash = user_balance("BANK")

        update_account("BANK", bank_cash + 1)
        update_account(to, cash_to + money - 1)
        update_account(username, cash_from - money)

        return  jsonify(generate_return_dict(200, "Amount transferred successfully."))


class Balance(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        retJson, error = verify_credentials(username, password)

        if error:
            return jsonify(retJson)

        retJson = users.find({
            "Username": username
        }, {
            "Password": 0,
            "_id": 0
            })[0]

        return jsonify(retJson)


class TakeLoan(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return jsonify(retJson)


        cash = user_balance(username)
        debt = user_debt(username)

        update_account(username, cash + money)
        update_debt(username, debt + money)

        return  jsonify(generate_return_dict(200, "Loan added to your account."))


class PayLoan(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        retJson, error = verify_credentials(username, password)

        if error:
            return jsonify(retJson)

        cash = user_balance(username)

        if cash < money:
            return jsonify(generate_return_dict(303, "Not enough cash in your account."))

        debt = user_debt(username)

        update_account(username, cash - money)
        update_debt(username, debt - money)

        return jsonify(generate_return_dict(200, "You have successfully paid your loan."))


api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/take_loan')
api.add_resource(PayLoan, '/pay_loan')

# TO DO
# api.add_resource(Withdraw, '/withdraw')


if __name__ ==  "__main__":
    app.run(host='0.0.0.0')


































