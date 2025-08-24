#!/usr/bin/env python3
"""
Setup script for Metabolome Handbook
Creates virtual environment and installs dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def main():
    """Main setup function"""
    print("🚀 Setting up Metabolome Handbook...")
    
    # Check if we're on Windows
    is_windows = os.name == 'nt'
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment
    if not os.path.exists(".venv"):
        run_command("python -m venv .venv", "Creating virtual environment")
    else:
        print("📋 Virtual environment already exists")
    
    # Determine activation script
    if is_windows:
        activate_script = ".venv\\Scripts\\activate"
        pip_command = ".venv\\Scripts\\pip"
        python_command = ".venv\\Scripts\\python"
    else:
        activate_script = "source .venv/bin/activate"
        pip_command = ".venv/bin/pip"
        python_command = ".venv/bin/python"
    
    # Upgrade pip
    run_command(f"{pip_command} install --upgrade pip", "Upgrading pip")
    
    # Install dependencies
    run_command(f"{pip_command} install -r requirements.txt", "Installing dependencies")
    
    # Create data directory
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        print("✅ Created data directory")
    
    # Import sample data
    print("📋 Importing sample data...")
    try:
        result = subprocess.run(
            f"{python_command} data/import_data.py",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Sample data imported successfully")
    except subprocess.CalledProcessError as e:
        print("⚠️  Sample data import failed - you can run it manually later")
        print(f"Error: {e.stderr}")
    
    # Create startup scripts
    if is_windows:
        # Windows batch files
        with open("start_api.bat", "w") as f:
            f.write("@echo off\n")
            f.write("call .venv\\Scripts\\activate\n")
            f.write("uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload\n")
        
        with open("start_ui.bat", "w") as f:
            f.write("@echo off\n")
            f.write("call .venv\\Scripts\\activate\n")
            f.write("streamlit run ui/main.py --server.address 0.0.0.0 --server.port 8501\n")
        
        print("✅ Created Windows startup scripts (start_api.bat, start_ui.bat)")
    else:
        # Unix shell scripts
        with open("start_api.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("source .venv/bin/activate\n")
            f.write("uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload\n")
        
        with open("start_ui.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("source .venv/bin/activate\n")
            f.write("streamlit run ui/main.py --server.address 0.0.0.0 --server.port 8501\n")
        
        # Make scripts executable
        os.chmod("start_api.sh", 0o755)
        os.chmod("start_ui.sh", 0o755)
        
        print("✅ Created Unix startup scripts (start_api.sh, start_ui.sh)")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start the API server:")
    if is_windows:
        print("   start_api.bat")
    else:
        print("   ./start_api.sh")
    
    print("2. In another terminal, start the UI:")
    if is_windows:
        print("   start_ui.bat")
    else:
        print("   ./start_ui.sh")
    
    print("\n🌐 Access the application:")
    print("   Web Interface: http://localhost:8501")
    print("   API Docs: http://localhost:8000/docs")
    print("\n📚 See README.md for more information")

if __name__ == "__main__":
    main()
