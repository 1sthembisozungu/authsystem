from flask import Flask, render_template

app = Flask(__name__)

@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")

@app.route("/forgot-password")
def forgot_password():
    return "Forgot password page coming soon"


if __name__ == "__main__":
    app.run(debug=True)