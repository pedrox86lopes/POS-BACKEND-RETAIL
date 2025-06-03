import jwt
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify 
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__) # Flask Instance required for the application

# LOAD SECRET_KEY from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")

# JUST TO CHECK IF .ENV exists
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not defined. Create a .env with SECRET_KEY='STRONG_KEY_'.")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify(message="NO LOGIN DATA PROVIDED"), 400
    if "username" not in data or "password" not in data:
        return jsonify(message="NO USERNAME OR PASSWORD PROVIDED!"), 400

    # Simulating a user authentication
    if data["username"] == "admin" and data["password"] == "PassW0rd1r@98H8":
        # Generate JWT token
        token = jwt.encode(
            {"user": data["username"], "exp": datetime.now() + timedelta(minutes=30)},
            SECRET_KEY,
            algorithm="HS256"
        )
        return jsonify(message="WELCOME BABY!", token=token)

    return jsonify(message="wrong!"), 401

@app.route("/protected_resource" , methods=["GET"])
def protected_resource():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify(message="No AUTH Token provided"), 401

    try:
        # Check if the header starts with "Bearer " and extract the token
        # Ex: "Bearer YOUR_TOKEN_HERE"
        token_parts = auth_header.split(" ")
        if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
            return jsonify(message="Invalid token format. Use 'Bearer <token>'."), 401
        
        token = token_parts[1]

        # The same secret key used for encoding the token
        # Decode the token to get the user information
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = payload["user"]
        
        return jsonify(message=f"Welcome, {user}! Thats a protected resource, you are in!"), 200
    
    except jwt.ExpiredSignatureError:
        return jsonify(message="Expired token!"), 401
    except jwt.InvalidTokenError:
        return jsonify(message="Token is broken or invalid"), 401
    except Exception as e:
        # catch any other unexpected errors
        print(f"unexpected error: {e}") # for debug
        return jsonify(message=f"Internal Error: {str(e)}"), 500 # 500 Internal Server Error

if __name__ == "__main__":
    app.run(debug=True) # debug=True for development purposes