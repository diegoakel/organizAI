#!/usr/bin/env python3
"""
Database setup script for the AI File Organizer.
This script creates the necessary database and installs the pgvector extension.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create the database if it doesn't exist."""
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432))
    }
    
    db_name = os.getenv('DB_NAME', 'file_organizer')
    
    try:
        # Connect to PostgreSQL server (without specifying a database)
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute("""
                SELECT 1 FROM pg_database WHERE datname = %s
            """, (db_name,))
            
            if cursor.fetchone():
                print(f"Database '{db_name}' already exists.")
            else:
                # Create database
                cursor.execute(f"CREATE DATABASE {db_name}")
                print(f"Database '{db_name}' created successfully.")
        
        conn.close()
        
        # Now connect to the newly created database and install pgvector
        db_config['database'] = db_name
        conn = psycopg2.connect(**db_config)
        
        with conn.cursor() as cursor:
            # Install pgvector extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("pgvector extension installed successfully.")
        
        conn.commit()
        conn.close()
        
        print("Database setup completed successfully!")
        print(f"You can now run the application with: python app.py")
        
    except psycopg2.Error as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def check_requirements():
    """Check if all required packages are installed."""
    try:
        import psycopg2
        import pgvector
        import sentence_transformers
        print("All required packages are installed.")
        return True
    except ImportError as e:
        print(f"Missing package: {e}")
        print("Please install requirements with: pip install -r requirements.txt")
        return False

def main():
    """Main function to run the database setup."""
    print("AI File Organizer - Database Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Warning: .env file not found.")
        print("Please create a .env file based on .env.example")
        print("You can continue with default values for now.")
        print()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Create database
    create_database()

if __name__ == "__main__":
    main()