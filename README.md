# RcDevDash - Project Planning Dashboard

A simple yet powerful project planning dashboard built with Flask and Bootstrap for tracking project hours, work items, and tasks.

## Features

- **User Authentication**: Secure login system with admin access
- **Project Management**: Create and manage multiple projects
- **Hours Tracking**: Track hours budget vs hours used with visual progress bars
- **Work Items**: Log work completed with hours and descriptions
- **Task Lists**: Create and manage tasks with deadlines
- **PDF Reports**: Generate professional weekly reports for each project
- **Responsive Design**: Modern Bootstrap 5 UI that works on all devices

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Database**: MySQL (PythonAnywhere)
- **PDF Generation**: ReportLab
- **Authentication**: Flask-Login

## Project Structure

```
RcDevDash/
├── app.py                 # Main Flask application
├── auth.py                # Authentication routes
├── models.py              # Database models
├── config.py              # Configuration settings
├── reports.py             # PDF report generation
├── init_db.py            # Database initialization script
├── wsgi.py               # WSGI configuration for deployment
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── static/
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── main.js       # JavaScript functionality
└── templates/
    ├── base.html          # Base template
    ├── login.html         # Login page
    ├── home.html          # Project dashboard
    └── project_detail.html # Project detail page
```

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- MySQL database (or use SQLite for local testing)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Crschnicker/RcDevDash.git
   cd RcDevDash
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv

   # On Windows:
   venv\Scripts\activate

   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   copy .env.example .env   # Windows
   cp .env.example .env     # macOS/Linux

   # Edit .env and add your database credentials
   ```

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Admin Login Credentials

- **Username**: `ConnerS`
- **Password**: `Future!2000`

## PythonAnywhere Deployment

For detailed deployment instructions, see [PYTHONANYWHERE_DEPLOYMENT.md](PYTHONANYWHERE_DEPLOYMENT.md)

### Quick Start

1. **Clone repository on PythonAnywhere**:
   ```bash
   git clone https://github.com/Crschnicker/RcDevDash.git
   cd RcDevDash
   ```

2. **Set up virtual environment**:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 rcdevdash
   pip install -r requirements.txt
   ```

3. **Configure database** - Create `.env` file with your credentials
4. **Initialize database** - Run `python init_db.py`
5. **Configure web app** in PythonAnywhere Web tab
6. **Reload** and access at `https://YOUR_USERNAME.pythonanywhere.com`

See the [full deployment guide](PYTHONANYWHERE_DEPLOYMENT.md) for step-by-step instructions with troubleshooting tips.

## Usage Guide

### Creating a Project

1. Log in with admin credentials
2. Click "New Project" button on the dashboard
3. Enter project name, description, and hours budget
4. Click "Create Project"

### Adding Work Items

1. Navigate to a project detail page
2. In the "Work Items" section, fill out the form:
   - Description of work completed
   - Hours spent
   - Date (defaults to today)
3. Click "Add Work Item"

### Managing Tasks

1. On the project detail page, go to the "Tasks" section
2. Enter task description and optional deadline
3. Click "Add Task"
4. Check the checkbox to mark tasks as complete

### Generating Reports

1. Open any project detail page
2. Click the "Generate Report" button
3. A professional PDF report will be downloaded

## Features Explained

### Project Dashboard

- View all projects in a card layout
- See hours budget vs hours used at a glance
- Visual progress bars show project status
- Over-budget projects are highlighted in red

### Project Detail Page

- Complete project information
- Real-time hours summary
- Work items history log
- Task list with completion tracking
- One-click PDF report generation

### PDF Reports

Professional reports include:
- Project information and description
- Hours summary table
- Complete work items history
- Task list with status
- Recent activity summary (last 7 days)

## Security Notes

- Change the default admin password after first login
- Use strong, unique `SECRET_KEY` in production
- Enable HTTPS in production (automatically enabled on PythonAnywhere)
- Keep your `.env` file secure and never commit it to version control

## Troubleshooting

### Database Connection Issues

- Verify your database credentials in `.env`
- Ensure your MySQL database is running
- Check that the database user has proper permissions

### Import Errors

- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using the correct virtual environment

### Static Files Not Loading

- Check that static files are properly configured in PythonAnywhere
- Verify the static files path is correct
- Clear your browser cache

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on the GitHub repository.

## Changelog

### Version 1.0.0 (Initial Release)
- User authentication with admin access
- Project management with hours tracking
- Work item logging
- Task management with deadlines
- PDF report generation
- Bootstrap 5 responsive UI
- PythonAnywhere deployment ready

---

Built with Flask and Bootstrap by Conner Schnicker
