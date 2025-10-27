from database.database_manager import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM strategies WHERE id = 4675')
    row = cursor.fetchone()
    if row:
        print('Strategy ID 4675:')
        print(f'Name: {row[1]}')
        print(f'Description: {row[2]}')
        print(f'Strategy Type: {row[3]}')
        print(f'Asset Class: {row[4]}')
        print(f'Timeframe: {row[5]}')
        print(f'Parameters: {row[6]}')
    else:
        print('Strategy ID 4675 not found')