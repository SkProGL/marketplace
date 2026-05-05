# Summary of Security and Feature Changes

Here is a summary of all the surgical changes that have been applied to the project to improve its security posture and add requested features, along with instructions on how to verify and test them.

### 1. Argon2id Password Hashing
**What was changed:**
- Added `argon2-cffi` to both `requirements.txt` and `api_requirements.txt`.
- Added the `PASSWORD_HASHERS` list to `marketplace_platform/settings.py` and placed `Argon2PasswordHasher` at the very top. 

**Why:**
Argon2id is the current industry standard and recommended password hashing algorithm. It is highly resistant to both GPU cracking attacks (memory-hard) and side-channel attacks. By putting it at the top of the list, Django will automatically use it for all new passwords and will upgrade older hashes (like PBKDF2) to Argon2id upon the next successful user login.

**How to test:**
1. Create a new user via the signup page.
2. Connect to your database or run `python manage.py shell`.
3. Query the user: `from core.models import User; user = User.objects.last(); print(user.password)`.
4. The output should start with `argon2$argon2id$v=19$m=...` indicating it is hashed with Argon2id.

### 2. Brute Force Protection (Django Axes)
**What was changed:**
- Added `django-axes` to `requirements.txt` and `api_requirements.txt`.
- Added `'axes'` to `INSTALLED_APPS` and `'axes.middleware.AxesMiddleware'` to `MIDDLEWARE` in `settings.py`.
- Configured the authentication backend in `settings.py` by adding `AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend', 'django.contrib.auth.backends.ModelBackend']`.
- Set configuration variables in `settings.py`:
  - `AXES_FAILURE_LIMIT = 5` (lock out after 5 failures)
  - `AXES_COOLOFF_TIME = 1` (lock out lasts for 1 hour)
  - `AXES_RESET_ON_SUCCESS = True` (reset the counter upon a successful login)
  - `AXES_LOCKOUT_URL = '/login/'` (redirect locked out users to the login page)

**Why:**
To prevent attackers from repeatedly guessing passwords (brute forcing) or carrying out credential stuffing attacks. Axes monitors login attempts and locks out IP addresses or usernames after a set threshold, logging the failures to the database.

**How to test:**
1. You will first need to run `python manage.py migrate` because Axes uses database tables to track attempts and lockouts.
2. Go to the login page and attempt to log in with an incorrect password 6 times in a row.
3. On the 6th attempt, you should be locked out (and depending on how Django handles the redirect, you should not be able to authenticate even with the correct password until the cooldown expires or you reset it).
4. Run `python manage.py axes_list_attempts` or `python manage.py axes_reset` in your console to view or clear the lockouts.

### 3. Enumeration Protection (Ambiguous Error Message)
**What was changed:**
- In `core/views.py` (`login_view`), changed the error message on a failed login from `"Invalid email or password."` to `"username or password is incorrect"`.

**Why:**
While the original message was already decent, best practice is to make the error message indistinguishable regardless of whether the email exists in the database or the password is wrong. This prevents attackers from guessing valid email addresses on your platform (user enumeration).

**How to test:**
1. Go to the login page.
2. Try logging in with a completely fake email that doesn't exist. Observe the error message.
3. Try logging in with a real email but the wrong password. Observe the error message.
4. Both should identically say `"username or password is incorrect"`.

### 4. "Remember Me" Functionality
**What was changed:**
- Added a `remember_me` boolean field to `LoginForm` and `SignupForm` in `core/forms.py`.
- Updated `core/templates/login.html` and `core/templates/signup.html` to include a "Remember me" checkbox below the password fields.
- Modified `login_view` and `signup_view` in `core/views.py` to process the checkbox. If checked, `request.session.set_expiry(1209600)` sets the session to expire in 2 weeks. If unchecked, `request.session.set_expiry(0)` makes it a "browser session" that expires when the user closes their browser.

**Why:**
Standard convenience feature for users, managed securely using Django's built-in session expiry mechanisms rather than raw cookies.

**How to test:**
1. Go to the login page and log in **without** checking "Remember me". Close your entire browser (not just the tab), reopen it, and navigate back to the site. You should be logged out.
2. Log in again, this time **checking** "Remember me". Close your entire browser, reopen it, and navigate back. You should still be logged in.

### 5. XSS Mitigation in Utils
**What was changed:**
- In `core/utils.py`, there was a line generating an error message: `error_html = mark_safe(f"<b>Error on row {str(row_id)[:8]}:</b><br>{form.errors}")`.
- Changed this to use Django's `format_html`: `error_html = format_html("<b>Error on row {}:</b><br>{}", str(row_id)[:8], form.errors)`.

**Why:**
Using `mark_safe` on an f-string that contains external variables (like `form.errors`) is a common source of Cross-Site Scripting (XSS). If a malicious user forces a specific payload into `form.errors`, `mark_safe` would render it directly into the HTML unescaped. `format_html` safely escapes the arguments before building the HTML string.

**How to test:**
This is harder to test visually without forcing a validation error containing HTML tags on whatever feature uses `core/utils.py`. The test is mostly structural: verifying the code no longer uses `mark_safe` combined with f-strings.

### 6. Multiple Backend Fix for Signup
**What was changed:**
- In `core/views.py` (`signup_view`), explicitly defined the backend during automatic login: `login(request, user, backend='django.contrib.auth.backends.ModelBackend')`.

**Why:**
Because `axes` was added to `AUTHENTICATION_BACKENDS`, Django didn't know which backend to assign to a newly created user upon signup, resulting in a 500 error. Explicitly stating the `ModelBackend` resolves this.

**How to test:**
1. Go to the signup page.
2. Fill out the form and submit.
3. You should successfully be redirected to the home page and automatically logged in, without receiving a 500 server error.