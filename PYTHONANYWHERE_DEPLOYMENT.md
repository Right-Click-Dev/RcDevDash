# PythonAnywhere Deployment Guide

This guide will walk you through deploying RcDevDash to PythonAnywhere.

## Prerequisites

- A PythonAnywhere account (free or paid)
- Your application code ready to deploy
- Git installed locally (optional, but recommended)

## Step 1: Prepare Your Code

1. **Create a Git repository** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Push to GitHub/GitLab** (recommended for easier deployment):
   ```bash
   git remote add origin https://github.com/yourusername/RcDevDash.git
   git push -u origin main
   ```

## Step 2: Set Up PythonAnywhere

### 2.1 Clone Your Repository

1. Log in to PythonAnywhere
2. Open a Bash console from the "Consoles" tab
3. Clone your repository:
   ```bash
   git clone https://github.com/yourusername/RcDevDash.git
   cd RcDevDash
   ```

### 2.2 Create Virtual Environment

```bash
mkvirtualenv --python=/usr/bin/python3.10 rcdevdash
workon rcdevdash
pip install -r requirements.txt
```

### 2.3 Set Up MySQL Database

1. Go to the "Databases" tab in PythonAnywhere
2. Set a MySQL password if you haven't already
3. Create a new database named: `yourusername$rcdevdash`
4. Note your database connection details:
   - Username: `yourusername`
   - Host: `yourusername.mysql.pythonanywhere-services.com`
   - Database name: `yourusername$rcdevdash`

### 2.4 Initialize Database

Back in your Bash console:

```bash
# Create .env file with your settings
nano .env
```

Add the following (replace with your actual values):

```bash
SECRET_KEY=generate-a-random-secret-key-here
DB_USERNAME=yourusername
DB_PASSWORD=your_mysql_password
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_NAME=yourusername$rcdevdash
SESSION_COOKIE_SECURE=True
```

To generate a secure SECRET_KEY, you can run:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Initialize the database:
```bash
python init_db.py
```

## Step 3: Configure Web App

### 3.1 Create Web App

1. Go to the "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10 (or latest available)

### 3.2 Configure Virtual Environment

In the "Virtualenv" section:
- Enter: `/home/yourusername/.virtualenvs/rcdevdash`
- Click the checkmark

### 3.3 Configure Source Code

In the "Code" section:
- Source code: `/home/yourusername/RcDevDash`
- Working directory: `/home/yourusername/RcDevDash`

### 3.4 Configure WSGI File

1. Click on the WSGI configuration file link (something like `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
2. Replace the entire contents with:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/RcDevDash'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import Flask app
from app import app as application
```

**Important**: Replace `yourusername` with your actual PythonAnywhere username!

### 3.5 Configure Static Files

In the "Static files" section, add:
- URL: `/static/`
- Directory: `/home/yourusername/RcDevDash/static`

## Step 4: Create Admin User

In your Bash console:

```bash
cd ~/RcDevDash
workon rcdevdash
python
```

Then in the Python shell:

```python
from app import app
from models import db, User

with app.app_context():
    # Create admin user
    admin = User(username='admin', email='admin@example.com', is_admin=True)
    admin.set_password('your_secure_password_here')
    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")
    exit()
```

## Step 5: Reload and Test

1. Go back to the "Web" tab
2. Click the green "Reload" button
3. Visit your site: `https://yourusername.pythonanywhere.com`
4. Log in with your admin credentials

## Troubleshooting

### Check Error Logs

If something goes wrong, check the logs:
- Go to "Web" tab
- Click on "Log files" section
- Check both error log and server log

### Common Issues

**Database Connection Errors**:
- Verify your database credentials in `.env`
- Make sure the database exists in the Databases tab
- Check that you've run `init_db.py`

**Module Not Found Errors**:
- Make sure you're using the correct virtual environment
- Re-run `pip install -r requirements.txt` in your virtualenv

**Static Files Not Loading**:
- Verify the static files path in the Web tab
- Make sure the directory exists: `/home/yourusername/RcDevDash/static`

**500 Internal Server Error**:
- Check the error log in the Web tab
- Verify your WSGI configuration file
- Make sure all environment variables are set correctly

### Debugging in Console

```bash
cd ~/RcDevDash
workon rcdevdash
python

# Test database connection
from app import app
from models import db

with app.app_context():
    try:
        db.create_all()
        print("Database connection successful!")
    except Exception as e:
        print(f"Error: {e}")
```

## Updating Your Application

When you make changes to your code:

```bash
cd ~/RcDevDash
git pull origin main
workon rcdevdash
pip install -r requirements.txt  # if requirements changed
# Then reload your web app from the Web tab
```

## Security Best Practices

1. **Never commit your .env file** - it's already in .gitignore
2. **Use a strong SECRET_KEY** - generate it with `secrets.token_hex(32)`
3. **Use strong passwords** for all user accounts
4. **Keep dependencies updated** - regularly update your requirements.txt
5. **Enable HTTPS** - PythonAnywhere provides this by default
6. **Set SESSION_COOKIE_SECURE=True** in production

## Backup Your Database

Regularly backup your database from the Databases tab:
1. Go to "Databases" tab
2. Click "Download" next to your database
3. Store backups securely

## Need Help?

- PythonAnywhere Help: https://help.pythonanywhere.com/
- PythonAnywhere Forums: https://www.pythonanywhere.com/forums/
- Check error logs in the Web tab
