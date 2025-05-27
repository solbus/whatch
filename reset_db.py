from app.core.people_db import PeopleDB
from app.core.watching_db import WatchingDB

if __name__ == "__main__":
    people_db = PeopleDB()
    people_db.reset_database()
    people_db.close()

    watching_db = WatchingDB()
    watching_db.close()

    print("Database has been reset.")
