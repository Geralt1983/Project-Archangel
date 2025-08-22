# Fix Database Connection Issue

## Problem
Your Render service is failing to connect to Supabase with this error:
```
connection to server at "db.uceotsolnrelyghgtqgc.supabase.co" (IPv6 address), port 5432 failed: Network is unreachable
```

## Solution: Use Supabase Connection Pooler

### Step 1: Get Your Pooler Connection String

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Settings** → **Database**
4. Look for **Connection string** section
5. Select **Transaction** mode
6. Copy the connection string that uses port `6543`

The pooler connection string format:
```
postgresql://postgres.uceotsolnrelyghgtqgc:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

### Step 2: Update Render Environment Variable

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on your **project-archangel-api** service
3. Go to **Environment** tab
4. Find the **DATABASE_URL** variable
5. Click **Edit**
6. Replace with the pooler connection string from Step 1
7. Click **Save Changes**

### Step 3: Wait for Redeploy

Render will automatically redeploy your service. This takes 2-3 minutes.

## Why Use the Pooler?

- **IPv4 Only**: Avoids IPv6 connectivity issues
- **Connection Pooling**: Better for serverless/PaaS environments
- **Stability**: Handles connection management automatically
- **Performance**: Reduces connection overhead

## Verify the Fix

After the service redeploys, test with:

```bash
curl https://project-archangel-api.onrender.com/health
curl https://project-archangel-api.onrender.com/test-db
```

Both should return successful responses.

## Alternative: Direct Connection with IPv4

If you prefer direct connection, you can also try:
```
postgresql://postgres.uceotsolnrelyghgtqgc:[YOUR-PASSWORD]@db.uceotsolnrelyghgtqgc.supabase.co:5432/postgres?sslmode=require&connect_timeout=10
```

But the pooler connection is recommended for production use.
