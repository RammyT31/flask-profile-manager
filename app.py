import re
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "profiles.db"

app = Flask(__name__)

# Flask uses this key to protect session-based flash messages.
app.config["SECRET_KEY"] = "vw35467e7ib67hh8rbue678rbuesb7ddmi8"


def get_db_connection():
    """Connect to the SQLite database and return accessible rows."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database():
    """Create the profiles table if it does not already exist."""
    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                date_of_birth TEXT NOT NULL
            )
        """)
        connection.commit()


def validate_profile(full_name, email, phone, date_of_birth):
    """Validate profile information and return any errors."""
    errors = []

    # Check that the full name is not empty.
    if not full_name.strip():
        errors.append("Full name is required.")
    elif len(full_name.strip()) < 2:
        errors.append("Full name must contain at least 2 characters.")

    # Check email format, including a domain extension of at least 2 letters.
    email_pattern = r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"

    if not email.strip():
        errors.append("Email address is required.")
    elif not re.match(email_pattern, email.strip()):
        errors.append("Enter a valid email address, for example name@example.com.")

    # Allow an optional leading + and common phone-number separators.
    cleaned_phone = re.sub(r"[\s()-]", "", phone)

    if not phone.strip():
        errors.append("Phone number is required.")
    elif not re.fullmatch(r"\+?[0-9]{7,15}", cleaned_phone):
        errors.append("Enter a valid phone number containing 7 to 15 digits.")

    # Check that the date of birth has been provided.
    if not date_of_birth:
        errors.append("Date of birth is required.")

    return errors


@app.route("/")
def index():
    """Display all profiles stored in the database."""
    with get_db_connection() as connection:
        profiles = connection.execute(
            "SELECT * FROM profiles ORDER BY id DESC"
        ).fetchall()

    return render_template("index.html", profiles=profiles)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Display the registration form and save a valid new profile."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()

        # Validate user information before saving it.
        errors = validate_profile(full_name, email, phone, date_of_birth)

        if not errors:
            try:
                with get_db_connection() as connection:
                    connection.execute(
                        """INSERT INTO profiles
                           (full_name, email, phone, date_of_birth)
                           VALUES (?, ?, ?, ?)""",
                        (full_name, email, phone, date_of_birth)
                    )
                    connection.commit()

                flash("Profile registered successfully.", "success")
                return redirect(url_for("index"))

            except sqlite3.IntegrityError:
                # Prevent duplicate email addresses.
                errors.append("That email address is already registered.")

        # Display validation errors to the user.
        for error in errors:
            flash(error, "error")

        # Preserve submitted values so the user does not need to retype them.
        return render_template("register.html", form_data=request.form)

    return render_template("register.html", form_data={})


@app.route("/profile/<int:profile_id>")
def view_profile(profile_id):
    """Display one saved profile."""
    with get_db_connection() as connection:
        profile = connection.execute(
            "SELECT * FROM profiles WHERE id = ?",
            (profile_id,)
        ).fetchone()

    if profile is None:
        flash("Profile not found.", "error")
        return redirect(url_for("index"))

    return render_template("profile.html", profile=profile)


@app.route("/profile/<int:profile_id>/edit", methods=["GET", "POST"])
def edit_profile(profile_id):
    """Preload an existing profile and save validated changes."""
    with get_db_connection() as connection:
        profile = connection.execute(
            "SELECT * FROM profiles WHERE id = ?",
            (profile_id,)
        ).fetchone()

    if profile is None:
        flash("Profile not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()

        # Apply the same validation used during registration.
        errors = validate_profile(full_name, email, phone, date_of_birth)

        if not errors:
            try:
                with get_db_connection() as connection:
                    connection.execute(
                        """UPDATE profiles
                           SET full_name = ?, email = ?, phone = ?, date_of_birth = ?
                           WHERE id = ?""",
                        (full_name, email, phone, date_of_birth, profile_id)
                    )
                    connection.commit()

                flash("Profile updated successfully.", "success")
                return redirect(url_for("view_profile", profile_id=profile_id))

            except sqlite3.IntegrityError:
                errors.append(
                    "That email address is already used by another profile."
                )

        for error in errors:
            flash(error, "error")

        # Preserve submitted information if validation fails.
        profile_data = {
            "id": profile_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "date_of_birth": date_of_birth
        }

        return render_template("edit.html", profile=profile_data)

    return render_template("edit.html", profile=profile)


if __name__ == "__main__":
    initialise_database()
    app.run(debug=True)