"""
WSGI Configuration for PythonAnywhere

This file is used to configure the WSGI application for deployment on PythonAnywhere.

PythonAnywhere Configuration Instructions:
1. Go to the "Web" tab in your PythonAnywhere dashboard
2. Click "Add a new web app"
3. Choose "Manual configuration" and select Python 3.10 (or latest available)
4. In the "Code" section, set:
   - Source code: /home/YOUR_USERNAME/RcDevDash
   - WSGI configuration file: /var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py

5. Edit the WSGI configuration file and replace its contents with:

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/RcDevDash'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DB_USERNAME'] = 'YOUR_USERNAME'
os.environ['DB_PASSWORD'] = 'YOUR_DB_PASSWORD'
os.environ['DB_HOST'] = 'YOUR_USERNAME.mysql.pythonanywhere-services.com'
os.environ['DB_NAME'] = 'YOUR_USERNAME$rcdevdash'
os.environ['SECRET_KEY'] = 'GENERATE_A_RANDOM_SECRET_KEY_HERE'

# Import Flask app
from app import app as application

6. In the "Static files" section, add:
   - URL: /static/
   - Directory: /home/YOUR_USERNAME/RcDevDash/static

7. Click "Reload" button to restart your web app
"""

import sys
import os

# This file can be used as a reference when setting up PythonAnywhere
# The actual WSGI file will be edited directly in PythonAnywhere's interface

# Add your project directory to the sys.path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import Flask app
from app import app as application

# This allows the file to be run directly for testing
if __name__ == "__main__":
    application.run()
