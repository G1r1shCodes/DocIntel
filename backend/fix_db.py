import sqlite3

def main():
    conn = sqlite3.connect('docintel.db')
    cursor = conn.cursor()
    
    commands = [
        "ALTER TABLE citations ADD COLUMN bbox JSON",
        "ALTER TABLE citations ADD COLUMN page_width FLOAT",
        "ALTER TABLE citations ADD COLUMN page_height FLOAT",
    ]
    
    for cmd in commands:
        try:
            cursor.execute(cmd)
            print(f"Success: {cmd}")
        except sqlite3.OperationalError as e:
            print(f"Skipped (already exists or error): {cmd} - {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
