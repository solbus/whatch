from app.core.people_db import PeopleDB

if __name__ == "__main__":
    db = PeopleDB()
    db.reset_database()
    db.close()
    print("Database has been reset.")
