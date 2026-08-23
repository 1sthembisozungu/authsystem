from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
# from werkzeug.security import generate_password_hash


from database import get_db_connection


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT"))
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS") == "True"

mail = Mail(app)




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

        # Check password length
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("register"))

        # Connect to database
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

                # Generate email verification token
                verification_token = secrets.token_urlsafe(32)

                # Token expires after 24 hours
                verification_token_expiry = datetime.now() + timedelta(hours=24)

                # Create the user
                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        username,
                        email,
                        password_hash,
                        verification_token,
                        verification_token_expiry
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        email,
                        password_hash,
                        verification_token,
                        verification_token_expiry
                    )
                )

            connection.commit()

        finally:
            connection.close()


        # Create verification link
        verification_link = url_for(
            "verify_email",
            token=verification_token,
            _external=True
        )

        # Create email
        message = Message(
            subject="Verify your AuthSystem account",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        message.body = f"""
Hello {username},

Welcome to AuthSystem.

Please verify your email address by clicking the link below:

{verification_link}

This verification link will expire in 24 hours.

If you did not create this account, you can ignore this email.

 Regards,
AuthSystem
"""

        # Send email
        mail.send(message)

        flash("Account created. Please check your email to verify your account.")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.")
            return redirect(url_for("login"))

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT id, username, password_hash, email_verified
                    FROM users
                    WHERE email = %s
                    """,
                    (email,)
                )

                user = cursor.fetchone()

        finally:
            connection.close()

        if not user:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

        user_id, username, password_hash, email_verified = user

        # Check email verification
        if not email_verified:
            flash("Please verify your email before logging in.")
            return redirect(url_for("login"))

        # Check password
        if not check_password_hash(password_hash, password):
            flash("Invalid email or password.")
            return redirect(url_for("login"))

        # Create session
        session["user_id"] = user_id
        session["username"] = username

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("login"))


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



# @app.route("/register", methods=["GET", "POST"])
# def register():
#     # all the registration code...
#     ...


@app.route("/verify/<token>")
def verify_email(token):

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id, email_verified, verification_token_expiry
                FROM users
                WHERE verification_token = %s
                """,
                (token,)
            )

            user = cursor.fetchone()

            if not user:
                flash("Invalid verification link.")
                return redirect(url_for("login"))

            user_id, email_verified, token_expiry = user

            if email_verified:
                flash("Your email is already verified.")
                return redirect(url_for("login"))

            if token_expiry < datetime.now():
                flash("This verification link has expired.")
                return redirect(url_for("login"))

            cursor.execute(
                """
                UPDATE users
                SET
                    email_verified = TRUE,
                    verification_token = NULL,
                    verification_token_expiry = NULL
                WHERE id = %s
                """,
                (user_id,)
            )

        connection.commit()

    finally:
        connection.close()

    flash("Email verified successfully. You can now login.")

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)