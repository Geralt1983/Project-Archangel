#!/bin/bash

echo "🧪 Testing Project Archangel Production Setup"
echo "============================================"
echo

echo "1️⃣ Testing health endpoint..."
curl -s https://project-archangel-api.onrender.com/health | python3 -m json.tool
echo

echo "2️⃣ Testing database connection..."
curl -s https://project-archangel-api.onrender.com/health/detailed | python3 -m json.tool | grep -A 3 "components"
echo

echo "3️⃣ Creating test task..."
curl -X POST https://project-archangel-api.onrender.com/tasks/intake/simple \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Production Test Task",
    "description": "Testing Supabase PostgreSQL integration",
    "client": "test"
  }' -s | python3 -m json.tool
echo

echo "4️⃣ Listing tasks..."
curl -s https://project-archangel-api.onrender.com/api/v1/tasks/list | python3 -m json.tool | head -20
echo

echo "✅ If all tests passed, your production setup is complete!"
