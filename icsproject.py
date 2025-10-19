import mysql.connector

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",          # MySQL username
    password="06062003",  # MySQL password
    database="RACING"     
)

cursor = db.cursor()

def main_menu():
    print("Welcome! Are you:")
    print("1. Admin")
    print("2. Guest")
    choice = input("Choose: ")

    if choice == "1":
        admin_menu()
    else:
        print("Guest features not ready yet.")

def admin_menu():
    while True:
        print("\nAdmin Menu:")
        print("1. Add a new race")
        print("2. Delete an owner")
        print("3. Move a horse")
        print("4. Approve a new trainer")
        print("5. Exit")

        choice = input("Choose: ")

        if choice == "1":
            add_race()
        elif choice == "2":
            delete_owner()
        elif choice == "3":
            move_horse()
        elif choice == "4":
            approve_trainer()
        elif choice == "5":
            break
        else:
            print("Invalid choice!")

def add_race():
	raceId = input("Enter race ID: ")
	raceName = input("Enter race name: ")
	trackName = input("Enter track name: ")
	raceDate = input("Enter race date (YYYY-MM-DD): ")
	raceTime = input("Enter race time (HH:MM): ")
	values = (raceId, raceName, trackName, raceDate, raceTime)

	sql = "INSERT INTO Race VALUES (%s, %s, %s, %s, %s)"
	cursor.execute(sql, values)

	# db.commit() # I commented this so it does not change the database (so it can only be changed temporarily)
	print("Race added successfully!")

def delete_owner():
	ownerId = input("Enter owner ID: ")

	sql1 = "DELETE FROM Owns WHERE ownerId = %s"
	cursor.execute(sql1, (ownerId,))

	sql2 = "DELETE FROM Owner WHERE ownerId = %s"
	cursor.execute(sql2, (ownerId,))

	# db.commit() # I commented this so it does not change the database (so it can only be changed temporarily)
	print("Owner deleted successfully!")

# Run the program
main_menu()


#	sql = ""
#	values = ""

#	cursor.execute(sql, values)
#	# db.commit()
#	print("Race added successfully!")
