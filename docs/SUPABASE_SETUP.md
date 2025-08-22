# Supabase Setup Guide for Project Archangel

## 1. Create Supabase Account & Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up for free account
3. Create new project:
   - **Project Name**: `project-archangel`
   - **Database Password**: Save this securely!
   - **Region**: Choose closest to your Render region
   - **Plan**: Free tier (500MB storage, 2GB bandwidth)

## 2. Get Your Database Connection String

Once project is created:

1. Go to **Settings** → **Database**
2. Find **Connection string** → **URI**
3. Copy the connection string (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

## 3. Configure Render Environment Variables

In your Render dashboard:

1. Go to your `project-archangel-api` service
2. Click **Environment** tab
3. Update/Add these variables:

```bash
# Replace with your Supabase connection string
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Add connection pool settings for reliability
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
```

## 4. Initialize Database Tables

After updating environment variables, SSH into Render or run locally:

```bash
# Using the DATABASE_URL from Supabase
python scripts/init_db.py
```

## 5. Benefits of This Setup

- ✅ **Persistent Data**: Database survives all restarts
- ✅ **Professional PostgreSQL**: Better than SQLite
- ✅ **Automatic Backups**: Supabase handles backups
- ✅ **Scalable**: Can grow with your needs
- ✅ **Connection Pooling**: Better performance
- ✅ **SQL Editor**: Supabase has built-in SQL editor

## 6. Optional: Enable Row Level Security

For production, consider enabling RLS in Supabase:

```sql
-- In Supabase SQL Editor
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Create policies as needed
CREATE POLICY "Enable all for service" ON tasks
  FOR ALL USING (true);
```

## 7. Monitor Your Usage

- Supabase Dashboard shows:
  - Database size
  - Bandwidth usage
  - Query performance
  - Active connections

## Free Tier Limits

- **Database**: 500MB
- **Bandwidth**: 2GB/month  
- **API Requests**: 500K/month
- **File Storage**: 1GB

These limits are very generous for your use case!
