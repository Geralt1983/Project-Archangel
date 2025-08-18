"""
Database Environment Setup for Testing
Provides comprehensive database testing utilities and setup
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from contextlib import contextmanager

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestDatabaseManager:
    """Manages test database lifecycle and operations"""
    
    def __init__(self, test_db_path: Optional[str] = None):
        self.test_db_path = test_db_path or "./test_archangel.db"
        self.temp_dir = None
        self.original_database_url = os.getenv('DATABASE_URL')
        
    def setup_test_environment(self) -> str:
        """Setup isolated test database environment"""
        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp(prefix='archangel_test_')
        test_db_file = os.path.join(self.temp_dir, 'test_db.sqlite')
        
        # Set environment variable for testing
        test_database_url = f"sqlite:///{test_db_file}"
        os.environ['DATABASE_URL'] = test_database_url
        
        return test_database_url
    
    def teardown_test_environment(self):
        """Clean up test environment"""
        # Restore original DATABASE_URL
        if self.original_database_url:
            os.environ['DATABASE_URL'] = self.original_database_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @contextmanager
    def test_database_context(self):
        """Context manager for test database lifecycle"""
        database_url = self.setup_test_environment()
        try:
            # Initialize database schema
            self.initialize_test_schema()
            yield database_url
        finally:
            self.teardown_test_environment()
    
    def initialize_test_schema(self):
        """Initialize database schema for testing"""
        try:
            from app.db_pg import init
            init()
            print("Test database schema initialized successfully")
        except Exception as e:
            print(f"Failed to initialize test database schema: {e}")
            raise
    
    def verify_database_operations(self) -> dict:
        """Verify basic database operations work correctly"""
        results = {
            "connection": False,
            "schema_exists": False,
            "crud_operations": False,
            "errors": []
        }
        
        try:
            from app.db_pg import get_conn, save_task, fetch_open_tasks
            
            # Test connection
            conn = get_conn()
            results["connection"] = True
            
            # Test schema exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['events', 'tasks', 'outbox', 'providers', 'task_routing_history']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if not missing_tables:
                results["schema_exists"] = True
            else:
                results["errors"].append(f"Missing tables: {missing_tables}")
            
            # Test CRUD operations
            from datetime import datetime, timezone
            
            test_task = {
                "id": "test-db-setup-001",
                "external_id": "setup-test-123",
                "provider": "test",
                "title": "Database Setup Test Task",
                "description": "Test task for database environment setup",
                "importance": 3.0,
                "effort_hours": 1.0,
                "deadline": datetime.now(timezone.utc).isoformat(),
                "client": "test-client",
                "status": "triaged",
                "score": 0.75,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Create task
            save_task(test_task)
            
            # Read tasks
            open_tasks = fetch_open_tasks()
            task_ids = [task.get("id") for task in open_tasks]
            
            if "test-db-setup-001" in task_ids:
                results["crud_operations"] = True
            else:
                results["errors"].append("CRUD operations failed - task not found after creation")
                
        except Exception as e:
            results["errors"].append(f"Database verification failed: {str(e)}")
        
        return results

def setup_testing_environment():
    """Main function to setup testing environment"""
    print("Setting up Project Archangel Database Testing Environment")
    print("=" * 60)
    
    manager = TestDatabaseManager()
    
    with manager.test_database_context() as database_url:
        print(f"Test Database URL: {database_url}")
        
        # Verify database operations
        print("\nVerifying database operations...")
        results = manager.verify_database_operations()
        
        print(f"\nDatabase Verification Results:")
        print(f"  Connection: {'PASS' if results['connection'] else 'FAIL'}")
        print(f"  Schema: {'PASS' if results['schema_exists'] else 'FAIL'}")
        print(f"  CRUD Operations: {'PASS' if results['crud_operations'] else 'FAIL'}")
        
        if results['errors']:
            print(f"\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        # Overall assessment
        all_passed = all([
            results['connection'],
            results['schema_exists'], 
            results['crud_operations']
        ])
        
        if all_passed:
            print(f"\nDatabase environment setup SUCCESSFUL!")
            print(f"   Test database is ready for comprehensive testing")
            return True
        else:
            print(f"\nDatabase environment setup has ISSUES")
            print(f"   Please review errors above")
            return False

def create_test_data():
    """Create sample test data for development and testing"""
    try:
        from app.db_pg import save_task
        from datetime import datetime, timezone, timedelta
        
        print("\nCreating test data...")
        
        now = datetime.now(timezone.utc)
        test_tasks = [
            {
                "id": "test-urgent-001",
                "external_id": "urgent-task-123",
                "provider": "clickup",
                "title": "Critical Bug Fix",
                "description": "Fix critical production issue affecting user login",
                "importance": 5.0,
                "effort_hours": 2.0,
                "deadline": (now + timedelta(hours=4)).isoformat(),
                "client": "enterprise-client",
                "status": "triaged",
                "score": 0.95,
                "created_at": now.isoformat()
            },
            {
                "id": "test-feature-001", 
                "external_id": "feature-task-456",
                "provider": "trello",
                "title": "Implement User Dashboard",
                "description": "Create responsive user dashboard with analytics",
                "importance": 3.0,
                "effort_hours": 8.0,
                "deadline": (now + timedelta(days=7)).isoformat(),
                "client": "startup-client",
                "status": "triaged",
                "score": 0.65,
                "created_at": (now - timedelta(hours=12)).isoformat()
            },
            {
                "id": "test-maintenance-001",
                "external_id": "maint-task-789", 
                "provider": "todoist",
                "title": "Update Dependencies",
                "description": "Update all npm dependencies to latest stable versions",
                "importance": 2.0,
                "effort_hours": 4.0,
                "deadline": (now + timedelta(weeks=2)).isoformat(),
                "client": "internal",
                "status": "triaged",
                "score": 0.35,
                "created_at": (now - timedelta(days=3)).isoformat()
            }
        ]
        
        for task in test_tasks:
            save_task(task)
            print(f"  Created: {task['title']}")
        
        print(f"  Created {len(test_tasks)} test tasks")
        return True
        
    except Exception as e:
        print(f"  Failed to create test data: {e}")
        return False

if __name__ == "__main__":
    # Setup environment variables for testing
    os.environ['DATABASE_URL'] = 'sqlite:///./test_archangel.db'
    
    success = setup_testing_environment()
    
    if success:
        create_test_data()
        print("\nDatabase environment ready for testing!")
        print("   You can now run the test suite with confidence")
    else:
        print("\nDatabase environment setup failed!")
        sys.exit(1)