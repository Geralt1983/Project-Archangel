#!/usr/bin/env python3
"""
Script to check for tasks in the database
"""

import sqlite3
import os
from pathlib import Path

def check_tasks():
    """Check for tasks in the database"""
    
    # Check for SQLite database
    db_path = Path("orchestrator.db")
    if db_path.exists():
        print(f"Found database: {db_path}")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check task_scores table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Tables found: {[t[0] for t in tables]}")
            
            # Check for tasks
            if ('task_scores',) in tables:
                cursor.execute("SELECT task_id, score, timestamp FROM task_scores ORDER BY timestamp DESC LIMIT 5")
                tasks = cursor.fetchall()
                print(f"\nRecent tasks in task_scores:")
                for task in tasks:
                    print(f"  Task ID: {task[0]}, Score: {task[1]}, Time: {task[2]}")
            
            # Check decision_trace table
            if ('decision_trace',) in tables:
                cursor.execute("SELECT task_id, decision_type, reasoning, timestamp FROM decision_trace ORDER BY timestamp DESC LIMIT 5")
                decisions = cursor.fetchall()
                print(f"\nRecent decisions in decision_trace:")
                for decision in decisions:
                    print(f"  Task ID: {decision[0]}, Type: {decision[1]}, Time: {decision[3]}")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading database: {e}")
    else:
        print("Database file not found")
    
    # Check for main database
    main_db_path = Path("project_archangel.db")
    if main_db_path.exists():
        print(f"\nFound main database: {main_db_path}")
        
        try:
            conn = sqlite3.connect(main_db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Tables found: {[t[0] for t in tables]}")
            
            # Check for tasks
            if ('tasks',) in tables:
                cursor.execute("SELECT id, title, client, score, created_at FROM tasks ORDER BY created_at DESC LIMIT 5")
                tasks = cursor.fetchall()
                print(f"\nRecent tasks in main database:")
                for task in tasks:
                    print(f"  ID: {task[0]}, Title: {task[1]}, Client: {task[2]}, Score: {task[3]}, Created: {task[4]}")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading main database: {e}")

if __name__ == "__main__":
    check_tasks()
