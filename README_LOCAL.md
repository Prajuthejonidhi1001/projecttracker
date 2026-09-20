# Project Scheduler - Local Excel Edition

A lightweight task and project management application that runs completely locally using Excel files for data storage. Perfect for office environments with restricted access to databases or cloud storage.

## 🌟 Features

- ✅ **Task Management** - Create, edit, and track tasks with priorities and statuses
- 📊 **Step Tracking** - Break down tasks into manageable steps
- 📈 **Dashboard** - Visual overview of your work with statistics and alerts
- 🔒 **100% Local** - All data stored in Excel files on your computer
- 🚫 **No Database Required** - Works without SQL, PostgreSQL, or any database server
- 👥 **Multi-User** - Support for multiple users with authentication
- 📝 **Audit Trail** - Track all actions and changes
- 🎯 **Progress Tracking** - Monitor task completion percentages
- ⏰ **Due Date Management** - Track overdue and upcoming items

## 📋 Requirements

- **Python 3.10 or higher**
- **Internet connection** (only for initial setup to download packages)
- **Operating System**: Windows, macOS, or Linux

## 🚀 Quick Start Guide

### Step 1: Install Python

If you don't have Python installed:
1. Download from [python.org](https://www.python.org/downloads/)
2. During installation, **check "Add Python to PATH"**
3. Verify installation: `python --version`

### Step 2: Setup the Application

1. Open Command Prompt or Terminal in the project directory
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the setup script:
   ```bash
   python setup_local.py
   ```

   This will:
   - Create necessary directories
   - Initialize Excel storage files
   - Create a `.env` configuration file
   - Optionally create demo data

### Step 3: Start the Application

```bash
python run_local.py
```

### Step 4: Access the Application

Open your web browser and go to:
```
http://127.0.0.1:8000
```

### Step 5: Login

If you created demo data during setup, use these credentials:

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Regular User Account:**
- Username: `user1`
- Password: `user123`

## 📁 Data Storage

All your data is stored locally in the `excel_data` directory as Excel files:

```
excel_data/
├── users.xlsx              # User accounts
├── tasks.xlsx              # Task records
├── task_steps.xlsx         # Task steps
├── projects.xlsx           # Projects
├── audit_logs.xlsx         # Activity history
└── ...other files
```

### Backup Your Data

Simply copy the entire `excel_data` folder to back up all your data:

```bash
# Windows
xcopy excel_data excel_data_backup /E /I

# macOS/Linux
cp -r excel_data excel_data_backup
```

## 🔧 Configuration

Edit the `.env` file to customize settings:

```ini
# Application settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Time zone
TIME_ZONE=Asia/Kolkata

# Excel storage location
USE_EXCEL_STORAGE=True
```

## 📱 Usage Guide

### Creating a Task

1. Click **"New Task"** in the sidebar
2. Fill in the task details:
   - Title (required)
   - Description
   - Priority (Low, Medium, High, Critical)
   - Status (Draft, Not Started, In Progress, etc.)
   - Start and due dates
3. Click **"Create Task"**

### Adding Steps to a Task

1. Open a task by clicking on it
2. Click **"Add Step"**
3. Enter step details:
   - Title (required)
   - Description
   - Estimated time (in days)
   - Status
4. Click **"Create Step"**

### Tracking Progress

- The dashboard shows:
  - Total tasks and steps
  - Overdue items
  - In-progress work
  - Upcoming deadlines
- Task progress is automatically calculated from completed steps

## 🛠️ Troubleshooting

### "Python is not recognized"
- Make sure Python is added to your PATH
- Restart your terminal/command prompt after installing Python

### "pip is not recognized"
- Python 3.10+ includes pip by default
- Try `python -m pip install -r requirements.txt`

### Port 8000 is already in use
Edit `run_local.py` and change the port:
```python
app.run(host='127.0.0.1', port=8001, debug=True)  # Changed to 8001
```

### Excel files are corrupted
1. Stop the application
2. Delete the `excel_data` folder
3. Run `python setup_local.py` again

### Can't login
1. Ensure you ran `python setup_local.py` and created demo data
2. Check that `excel_data/users.xlsx` exists and has data
3. Try creating a new user in the Excel file directly

## 🔐 Security Notes

### For Office Use:
- Change the `SECRET_KEY` in `.env` to a strong random value
- Set `DEBUG=False` in production
- Don't share the `excel_data` folder (contains user passwords)
- Regular backups recommended

### Password Security:
- Passwords are hashed using Django's secure hashers
- Never stored in plain text
- Can't be recovered if forgotten (reset required)

## 📊 Excel File Structure

### users.xlsx
| Column | Description |
|--------|-------------|
| id | Unique identifier (UUID) |
| username | Login username |
| email | Email address |
| password | Hashed password |
| is_active | Account status |
| is_staff | Staff privileges |
| role | User role |

### tasks.xlsx
| Column | Description |
|--------|-------------|
| id | Unique identifier |
| title | Task name |
| description | Details |
| status | Current status |
| priority | Importance level |
| progress_percent | Completion % |
| owner_id | Assigned user |

### task_steps.xlsx
| Column | Description |
|--------|-------------|
| id | Unique identifier |
| task_id | Parent task |
| title | Step name |
| order | Sequence number |
| status | Current status |
| estimated_tat_days | Time estimate |

## 🆘 Getting Help

### Common Issues:

**Q: Can I use this without internet?**
A: Yes! After initial setup, no internet connection is needed.

**Q: Can multiple people use it simultaneously?**
A: No, this is designed for single-user local use. Excel file locking prevents concurrent access.

**Q: How do I add more users?**
A: Currently, users must be added by editing `excel_data/users.xlsx` or through the setup script. Admin interface coming soon!

**Q: Can I export data?**
A: Yes! The data is already in Excel format. Simply open the files in `excel_data/` with Excel.

**Q: Will this work on a USB drive?**
A: Yes! Copy the entire project folder to a USB drive and run from there.

## 📝 System Requirements

### Minimum:
- **CPU**: Any modern processor
- **RAM**: 512 MB available
- **Disk**: 100 MB free space
- **OS**: Windows 7+, macOS 10.12+, Linux (any modern distro)

### Recommended:
- **CPU**: Dual-core or better
- **RAM**: 1 GB available
- **Disk**: 500 MB free space (for data growth)

## 🔄 Updates and Maintenance

### Updating the Application:
1. Back up your `excel_data` folder
2. Replace application files with new version
3. Run `pip install -r requirements.txt` for new dependencies
4. Restart the application

### Cleaning Up:
```bash
# Remove cached Python files
find . -type d -name __pycache__ -exec rm -rf {} +

# Clear logs
rm -rf logs/*

# Fresh start (keeps data)
rm -rf .venv
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 📄 License

This is a private/internal project for office use.

## 🎯 Perfect For:

- ✅ Office environments with restricted internet/database access
- ✅ Personal project tracking
- ✅ Small teams (1-5 people)
- ✅ Temporary/portable installations
- ✅ Learning and demonstration purposes
- ✅ Quick deployment without IT approval

## 🚀 Next Steps

After getting started:
1. Create your first real task
2. Break it down into steps
3. Track your progress on the dashboard
4. Explore different views and filters
5. Customize settings in `.env`

---

**Made with ❤️ for local, offline productivity**

For issues or questions, refer to the troubleshooting section above.
