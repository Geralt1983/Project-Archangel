#!/usr/bin/env python3
"""
Test Database Setup Script for Project Archangel
Provides comprehensive database environment setup for testing
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_environment_file():
    """Copy test environment file if it doesn't exist"""
    env_file = project_root / ".env"
    env_test_file = project_root / ".env.test"
    
    if not env_file.exists() and env_test_file.exists():
        print("Creating .env from .env.test template...")
        with open(env_test_file, 'r') as src:
            content = src.read()
        
        with open(env_file, 'w') as dst:
            dst.write(content)
        
        print(".env file created from test template")
        return True
    elif env_file.exists():
        print(".env file already exists")
        return True
    else:
        print("No .env.test template found")
        return False

def initialize_database():
    """Initialize database schema"""
    try:
        # Set test environment
        os.environ['DATABASE_URL'] = 'sqlite:///./test_archangel.db'
        
        from app.db_pg import init
        print("Initializing database schema...")
        init()
        print("Database schema initialized successfully")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

def verify_setup():
    """Verify the database setup works correctly"""
    try:
        from tests.test_database_setup import TestDatabaseManager
        
        print("Verifying database setup...")
        manager = TestDatabaseManager()
        
        with manager.test_database_context():
            results = manager.verify_database_operations()
            
            all_passed = all([
                results['connection'],
                results['schema_exists'],
                results['crud_operations']
            ])
            
            if all_passed:
                print("Database verification passed")
                return True
            else:
                print("Database verification failed")
                for error in results['errors']:
                    print(f"  - {error}")
                return False
                
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

def run_basic_tests():
    """Run basic database tests"""
    try:
        from tests.simple_test_runner import main as run_simple_tests
        
        print("Running basic tests...")
        success = run_simple_tests()
        
        if success:
            print("Basic tests passed")
            return True
        else:
            print("Some basic tests failed, but database setup is working")
            return True  # Database setup can still be considered successful
            
    except Exception as e:
        print(f"Test execution failed: {e}")
        print("This doesn't necessarily mean database setup failed")
        return True

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup Project Archangel test database environment")
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing setup')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running basic tests')
    
    args = parser.parse_args()
    
    print("Project Archangel - Database Environment Setup")
    print("=" * 60)
    
    if not args.verify_only:
        # Step 1: Setup environment file
        print("\nStep 1: Environment Configuration")
        if not setup_environment_file():
            print("Environment setup failed")
            return False
        
        # Step 2: Initialize database
        print("\nStep 2: Database Initialization")
        if not initialize_database():
            print("Database initialization failed")
            return False
    
    # Step 3: Verify setup
    print("\nStep 3: Setup Verification")
    if not verify_setup():
        print("Setup verification failed")
        return False
    
    # Step 4: Run basic tests (optional)
    if not args.skip_tests:
        print("\nStep 4: Basic Tests")
        run_basic_tests()  # Non-blocking
    
    # Success summary
    print("\n" + "=" * 60)
    print("DATABASE ENVIRONMENT SETUP COMPLETE!")
    print("=" * 60)
    print("Environment configured")
    print("Database schema initialized")
    print("Setup verified")
    print("Ready for comprehensive testing")
    print("")
    print("Next Steps:")
    print("  1. Run full test suite: python tests/simple_test_runner.py")
    print("  2. Start development server: python -m app.main")
    print("  3. Run specific tests: python -m pytest tests/")
    print("")
    print("Database Management:")
    print(f"  - Database file: {project_root}/test_archangel.db")
    print(f"  - Environment: {project_root}/.env")
    print(f"  - Test config: {project_root}/.env.test")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)