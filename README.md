# Whatch

A small PyQt6 application that demonstrates a simple menu system with a people management interface backed by SQLite.

## Requirements

- **Python 3.10+** (tested with Python 3.11)
- **PyQt6**

## Setup

1. Install the required Python package:

   ```bash
   python -m pip install PyQt6
   ```

2. Clone this repository and change into its directory (if you are not already here).

3. Run the application:

   ```bash
   python main.py
   ```

The first time you run the program, a SQLite database file named `whatch.db` is created in the project root automatically. No additional setup is required.

## Project Structure

- `main.py` – launches the main window.
- `app/` – contains UI widgets and the simple database layer.

Enjoy exploring the app!
