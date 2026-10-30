from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify
)
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
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

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

        # Accept either a username or an email address
        login_identifier = request.form.get(
            "login_identifier", ""
        ).strip()

        password = request.form.get("password", "")

        if not login_identifier or not password:
            flash("Please enter your username or email and password.")
            return redirect(url_for("login"))

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT id, username, password_hash, email_verified, theme
                    FROM users
                    WHERE LOWER(username) = LOWER(%s)
                       OR LOWER(email) = LOWER(%s)
                    """,
                    (login_identifier, login_identifier)
                )

                user = cursor.fetchone()

        finally:
            connection.close()

        # Check whether the account exists
        if not user:
            flash("Invalid username/email or password.")
            return redirect(url_for("login"))

        user_id, username, password_hash, email_verified, theme = user

        # Email verification is required before login
        if not email_verified:
            flash("Please verify your email before logging in.")
            return redirect(url_for("login"))

        # Verify the submitted password against the stored hash
        if not check_password_hash(password_hash, password):
            flash("Invalid username/email or password.")
            return redirect(url_for("login"))

        # Start a fresh authenticated session
        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["theme"] = theme

        # Redirect in the same browser tab
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT username, created_at, theme
                FROM users
                WHERE id = %s
                """,
                (session["user_id"],)
            )

            user = cursor.fetchone()

    finally:
        connection.close()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    username, created_at, theme = user

    return render_template(
        "dashboard.html",
        username=username,
        created_at=created_at,
        theme=theme
    )



@app.route("/api/theme", methods=["POST"])
def update_theme():

    # Only logged-in users can change their saved preference
    if "user_id" not in session:
        return jsonify({"error": "Please log in first."}), 401

    data = request.get_json(silent=True) or {}
    theme = data.get("theme")

    # Accept only the two supported themes
    if theme not in ("light", "dark"):
        return jsonify({"error": "Invalid theme."}), 400

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET theme = %s
                WHERE id = %s
                """,
                (theme, session["user_id"])
            )

            if cursor.rowcount == 0:
                connection.rollback()
                session.clear()
                return jsonify({"error": "Account not found."}), 404

        connection.commit()

    except Exception:
        connection.rollback()
        app.logger.exception("Could not save theme preference")
        return jsonify({"error": "Could not save theme preference."}), 500

    finally:
        connection.close()

    # Keep the session in sync with the database
    session["theme"] = theme

    return jsonify({
        "message": "Theme preference saved.",
        "theme": theme
    }), 200



@app.route("/logout")
def logout():

    session.clear() #this removes user_id, username from session

    flash("You have been logged out.")

    return redirect(url_for("login"))

# if __name__ == "__main__":
#     app.run(debug=True)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        # Always show the same message to protect account privacy.
        confirmation_message = (
            "If an account exists with that email, "
            "you will receive a password reset link."
        )

        if not email:
            flash("Please enter your email address.")
            return redirect(url_for("forgot_password"))

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email
                    FROM users
                    WHERE LOWER(email) = LOWER(%s)
                    """,
                    (email,)
                )
                user = cursor.fetchone()

                if user:
                    user_id, account_email = user

                    # Generate a secure, unpredictable token. Hard-to-guess toekn
                    reset_token = secrets.token_urlsafe(32)
                    #sets the expiry time
                    reset_expiry = datetime.now() + timedelta(minutes=30)

                    cursor.execute(
                        """
                        UPDATE users
                        SET reset_token = %s,
                            reset_token_expiry = %s
                        WHERE id = %s
                        """,
                        (reset_token, reset_expiry, user_id)
                    )

            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("Failed to create a password reset token")
            flash("Something went wrong. Please try again.")
            return redirect(url_for("forgot_password"))

        finally:
            connection.close()

        # Send the reset email after saving the token.
        if user:
            reset_url = url_for(
                "reset_password",
                token=reset_token,
                _external=True
            )

            message = Message(
                subject="Reset your AuthSystem password",
                sender=app.config["MAIL_USERNAME"],
                recipients=[account_email]
            )

            message.body = (
                "We received a request to reset your AuthSystem password.\n\n"
                f"Use this link to choose a new password:\n{reset_url}\n\n"
                "This link expires in 30 minutes and can only be used once.\n"
                "If you did not request this reset, you can ignore this email."
            )

            try:
                mail.send(message)
            except Exception:
                app.logger.exception("Failed to send the password reset email")

        flash(confirmation_message)
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# if __name__ == "__main__":
#     app.run(debug=True)



@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, reset_token_expiry
                FROM users
                WHERE reset_token = %s
                """,
                (token,)
            )
            user = cursor.fetchone()
    finally:
        connection.close()

    # Reject missing, expired, or already-used tokens.
    if not user:
        flash("This password reset link is invalid or has expired.")
        return redirect(url_for("forgot_password"))

    user_id, reset_expiry = user

    if not reset_expiry or reset_expiry <= datetime.now():
        flash("This password reset link is invalid or has expired.")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Your password must be at least 8 characters long.")
            return render_template("reset_password.html", token=token)

        if password != confirm_password:
            flash("The passwords do not match.")
            return render_template("reset_password.html", token=token)

        password_hash = generate_password_hash(password)

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                # Check the token and expiry again before changing the password.
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        reset_token = NULL,
                        reset_token_expiry = NULL
                    WHERE id = %s
                      AND reset_token = %s
                      AND reset_token_expiry > %s
                    """,
                    (password_hash, user_id, token, datetime.now())
                )

                if cursor.rowcount != 1:
                    connection.rollback()
                    flash("This password reset link is invalid or has expired.")
                    return redirect(url_for("forgot_password"))

            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("Failed to reset password")
            flash("Something went wrong. Please try again.")
            return redirect(url_for("forgot_password"))

        finally:
            connection.close()

        flash("Your password has been reset successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


@app.route("/test-db")
def test_db():

    try:
        connection = get_db_connection()
        connection.close()

        return "Database connection successful!"

    except Exception as e:
        return f"Database connection failed: {e}"





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