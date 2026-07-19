import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_z2yECkZdx0PN@ep-square-mud-aon0jj5s-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def migrate():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Add is_blocked to trainers if not exists
        cursor.execute("""
            ALTER TABLE trainers ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;
        """)

        # Add is_blocked to students if not exists
        cursor.execute("""
            ALTER TABLE students ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;
        """)

        conn.commit()
        print("Migration successful: Added is_blocked to trainers and students.")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
