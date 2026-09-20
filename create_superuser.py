import sys
import getpass
from datetime import datetime
from pathlib import Path

# Add project to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.excel_models import User

def main():
    print("========================================")
    print("   Create Superuser (Administrator)   ")
    print("========================================")
    
    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)
        
    # Check if username exists
    for u in User.all():
        if u.username == username:
            print(f"Error: Username '{username}' is already taken.")
            sys.exit(1)
            
    email = input("Email address: ").strip()
    if not email:
        print("Error: Email cannot be empty.")
        sys.exit(1)
        
    first_name = input("First Name (optional): ").strip()
    last_name = input("Last Name (optional): ").strip()
    
    while True:
        password = getpass.getpass("Password: ")
        if not password:
            print("Error: Password cannot be empty.")
            continue
            
        password_confirm = getpass.getpass("Password (again): ")
        if password != password_confirm:
            print("Error: Passwords do not match. Try again.")
            continue
        break
        
    user_data = {
        'username': username,
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
        'role': 'admin',
        'date_joined': datetime.now().isoformat()
    }

    user = User(**user_data)
    user.set_password(password)
    user.save()
    
    print("\nSuperuser created successfully.")

if __name__ == '__main__':
    main()
