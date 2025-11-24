import os
import subprocess
import sys

def setup_venv():
    # Get the absolute path to the current directory
    base_path = os.path.abspath(os.path.dirname(__file__))
    venv_path = os.path.join(base_path, 'venv')
    venv_created = False

    # Create virtual environment if it doesn't exist
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
        print("Virtual environment created successfully!")
        venv_created = True
    else:
        print("Virtual environment already exists.")
    
    # Install requirements if we just created the venv
    if venv_created:
        print("\nInstalling requirements...")
        # Use the venv's pip to install requirements
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        else:
            pip_path = os.path.join(venv_path, 'bin', 'pip')
        requirements_path = os.path.join(base_path, 'requirements.txt')
        subprocess.run([pip_path, 'install', '-r', requirements_path], check=True)
        print("Requirements installed successfully!")

if __name__ == "__main__":
    setup_venv()
