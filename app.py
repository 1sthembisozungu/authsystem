from flask import Flask, render_template, request, redirect, url_for, flash
import os

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from database import get_db_connection


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check that all fields were entered
        if not username or not email or not password or not confirm_password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        # Check passwords
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        # Minimum password length
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("register"))

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:

                # Check if username or email already exists
                cursor.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE username = %s OR email = %s
                    """,
                    (username, email)
                )

                existing_user = cursor.fetchone()

                if existing_user:
                    flash("Username or email is already registered.")
                    return redirect(url_for("register"))

                # Hash the password
                password_hash = generate_password_hash(password)

                # Insert user into database
                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        username,
                        email,
                        password_hash
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (username, email, password_hash)
                )

            connection.commit()

        finally:
            connection.close()

        flash("Account created successfully. You can now login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


@app.route("/forgot-password")
def forgot_password():
    return "Forgot password page coming soon"


@app.route("/test-db")
def test_db():

    try:
        connection = get_db_connection()
        connection.close()

        return "Database connection successful!"

    except Exception as e:
        return f"Database connection failed: {e}"


if __name__ == "__main__":
    app.run(debug=True)