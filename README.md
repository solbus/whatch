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

The **Watching** section lets you keep track of any shows or movies you are currently following. From the main menu, click the TV icon to open the list. Use **Add New** to record a title and **Update Progress** when you watch more. Items are stored in the `currently_watching` table with `id`, `title`, `type` and `progress` columns.

## Database reset

Running `reset_db.py` deletes the database file so that the `people`, `watching` and `currently_watching` tables are recreated from scratch.
