#!/bin/bash
# Startup script for Render deployment
# This ensures the database is initialized on every start

echo "🚀 Starting Project Archangel..."

# Initialize database tables on startup
echo "📊 Initializing database..."
python3 -c "
from scripts.init_db import init_database
try:
    init_database()
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'⚠️ Database initialization warning: {e}')
"

# Start the application
echo "🌐 Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
