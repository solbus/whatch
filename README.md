# Whatch

A simple PyQt6 application for managing people.

## Setup

Install the dependencies and run the application:

```bash
pip install -r requirements.txt
python main.py
```

To reset all user data, run:

```bash
python reset_db.py
```

## Watching section

The **Watching** section lets you keep track of TV series you're currently following. From the main menu, click the TV icon to open the list of series. Use **Add Series** to record a new title and **Edit** to update your progress. Your progress is stored in the `watching` table alongside the `people` table.

## Database reset

Running `reset_db.py` now clears both the `people` and `watching` tables.
