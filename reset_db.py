from app.core.people_db import PeopleDB

if __name__ == "__main__":
    db = PeopleDB()
    db.reset_database()
    db.close()
    print("Database tables 'people' and 'watching' have been reset.")
