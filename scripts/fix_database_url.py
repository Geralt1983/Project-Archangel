#!/usr/bin/env python3
"""
Fix DATABASE_URL for Render deployment
Helps encode the password correctly for Supabase connection
"""

import urllib.parse
import sys

def generate_database_url():
    print("\n🔧 DATABASE_URL Generator for Supabase Pooler Connection")
    print("=" * 60)
    
    # Your Supabase project reference
    project_ref = "uceotsolnrelyghgtqgc"
    
    print(f"\nYour Supabase project reference: {project_ref}")
    print("\nEnter your Supabase database password")
    print("(The one you see as 'kybVax-6nesce-vovfoq' or similar)")
    
    password = input("Password: ").strip()
    
    if not password:
        print("❌ Password cannot be empty!")
        sys.exit(1)
    
    # URL encode the password to handle special characters
    encoded_password = urllib.parse.quote(password, safe='')
    
    # Generate both connection strings
    pooler_url = f"postgresql://postgres.{project_ref}:{encoded_password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
    
    # Alternative pooler endpoints (Supabase has multiple regions)
    alt_pooler_urls = [
        f"postgresql://postgres.{project_ref}:{encoded_password}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
        f"postgresql://postgres.{project_ref}:{encoded_password}@aws-1-us-east-2.pooler.supabase.com:6543/postgres"
    ]
    
    print("\n✅ Generated DATABASE_URL for Render:")
    print("=" * 60)
    print("\nPrimary (US-West-1):")
    print(pooler_url)
    
    print("\n📋 Alternative pooler endpoints (if primary doesn't work):")
    for i, url in enumerate(alt_pooler_urls, 1):
        print(f"\nOption {i} (US-East):")
        print(url)
    
    print("\n📝 Instructions:")
    print("1. Copy one of the URLs above")
    print("2. Go to https://dashboard.render.com")
    print("3. Click on your 'project-archangel-api' service")
    print("4. Go to 'Environment' tab")
    print("5. Update DATABASE_URL with the copied value")
    print("6. Save and wait for redeploy")
    
    print("\n⚠️  Important notes:")
    print("- The password has been URL-encoded to handle special characters")
    print("- Use the pooler connection (port 6543) for better stability")
    print("- If one region fails, try an alternative endpoint")
    
    # Show what was encoded
    if password != encoded_password:
        print(f"\n🔐 Password encoding: '{password}' → '{encoded_password}'")

if __name__ == "__main__":
    generate_database_url()
