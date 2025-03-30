# Testing Setup Guide

This guide will help you set up your testing environment using Visual Studio Code (VS Code) and Python. Follow the steps below to install the necessary tools, configure your Python environment, and install dependencies.

## Step 1: Install Visual Studio Code (VS Code)

1. **Download VS Code**: Go to the [official VS Code download page](https://code.visualstudio.com/) and download the installer for your operating system (Windows, macOS, or Linux).
2. **Install VS Code**: Run the installer and follow the on-screen instructions to install VS Code on your system.

## Step 2: Install Python

1. **Download Python**: Visit [python.org](https://www.python.org/downloads/) and download the latest version of Python for your operating system.
2. **Install Python**: Run the installer. Make sure to check the option "Add Python to PATH" during installation.

## 3. Clone the Repository

1. Open your terminal.
2. Run the following commands to clone the repository and navigate to the project folder:

   ```bash
   git clone https://github.com/Duck2Live/whitelabel-e2e-tests.git
   cd <repository-folder>
   
   
## Step 4: Open Your Project in VS Code

1. **Open VS Code**: Launch VS Code from your desktop or Start menu.
2. **Open Your Project Folder**: In VS Code, click on `File > Open Folder` and select the folder containing your project files.

## Step 5: Install the Python Extension in VS Code

1. Open Visual Studio Code.
2. Click on the Extensions icon in the Activity Bar on the side of the window.
3. In the Extensions Marketplace, search for "Python".
4. Install any of the Python extension.
   
## Step 6: Create a New Python Virtual Environment in VS Code

1. Open the Command Palette by pressing `Cmd + Shift + P` (on macOS) or `Ctrl + Shift + P` (on Windows/Linux).
2. Type "Python: Select Interpreter" and select it.
3. Choose the option "Create Environment".
4. Follow the prompts to create the virtual environment using `venv`.

VS Code will automatically activate the virtual environment once it's created.

## Step 7: Install Project Dependencies

1. Ensure your virtual environment is activated.
2. Open the terminal in VS Code.
3. Run the following command to install the required packages:

   ```bash
   pip install -r requirements.txt
