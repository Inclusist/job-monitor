#!/usr/bin/env python3
"""
Test LinkedIn OAuth Configuration

This script helps diagnose LinkedIn OAuth issues by checking:
1. Environment variables are set
2. LinkedIn OpenID Connect metadata is accessible
3. OAuth redirect URIs are properly configured

Usage:
    python scripts/test_linkedin_oauth.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import requests
import json

def test_linkedin_oauth():
    """Test LinkedIn OAuth configuration"""
    print("=" * 70)
    print("🔍 LINKEDIN OAUTH DIAGNOSTIC TEST")
    print("=" * 70)
    print()

    # Step 1: Check environment variables
    print("📋 Step 1: Checking Environment Variables")
    print("-" * 70)

    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')

    if client_id:
        print(f"   ✓ LINKEDIN_CLIENT_ID is set: {client_id[:10]}...")
    else:
        print("   ❌ LINKEDIN_CLIENT_ID is NOT set!")
        return

    if client_secret:
        print(f"   ✓ LINKEDIN_CLIENT_SECRET is set: {client_secret[:10]}...")
    else:
        print("   ❌ LINKEDIN_CLIENT_SECRET is NOT set!")
        return

    print()

    # Step 2: Test OpenID Connect metadata
    print("🌐 Step 2: Testing OpenID Connect Metadata URL")
    print("-" * 70)

    metadata_url = "https://www.linkedin.com/oauth/.well-known/openid-configuration"
    try:
        response = requests.get(metadata_url, timeout=10)
        if response.status_code == 200:
            print(f"   ✓ Metadata URL is accessible: {metadata_url}")
            metadata = response.json()

            print()
            print("   📄 LinkedIn OAuth Endpoints:")
            print(f"      - Issuer: {metadata.get('issuer')}")
            print(f"      - Authorization: {metadata.get('authorization_endpoint')}")
            print(f"      - Token: {metadata.get('token_endpoint')}")
            print(f"      - UserInfo: {metadata.get('userinfo_endpoint')}")
            print(f"      - Scopes: {', '.join(metadata.get('scopes_supported', []))}")
        else:
            print(f"   ❌ Failed to fetch metadata (HTTP {response.status_code})")
            return
    except Exception as e:
        print(f"   ❌ Error fetching metadata: {e}")
        return

    print()

    # Step 3: Check redirect URIs
    print("🔗 Step 3: Expected Redirect URIs")
    print("-" * 70)
    print("   Your LinkedIn app must have these redirect URIs configured:")
    print()
    print("   📍 Local Development:")
    print("      http://localhost:8080/authorize/linkedin")
    print()
    print("   📍 Production (inclusist.com):")
    print("      https://inclusist.com/authorize/linkedin")
    print()
    print("   📍 Railway App (if different):")
    print("      https://[your-app].up.railway.app/authorize/linkedin")
    print()

    # Step 4: Required LinkedIn Product
    print("🔐 Step 4: Required LinkedIn Product Access")
    print("-" * 70)
    print("   Your LinkedIn app MUST have this product approved:")
    print()
    print("   📦 'Sign In with LinkedIn using OpenID Connect'")
    print()
    print("   To request access:")
    print("   1. Go to https://www.linkedin.com/developers/apps")
    print("   2. Select your app")
    print("   3. Go to 'Products' tab")
    print("   4. Request access to 'Sign In with LinkedIn using OpenID Connect'")
    print("   5. Wait for approval (usually instant)")
    print()

    # Step 5: Common Issues
    print("⚠️  Step 5: Common Issues & Solutions")
    print("-" * 70)
    print()
    print("   Issue 1: 'redirect_uri_mismatch' error")
    print("   → Check that redirect URIs in LinkedIn app EXACTLY match")
    print("   → No trailing slashes!")
    print("   → Use https:// for production, http:// for localhost")
    print()
    print("   Issue 2: 'invalid_client' error")
    print("   → Client ID or Secret is incorrect")
    print("   → Double-check credentials in .env file")
    print("   → Ensure no extra spaces or quotes")
    print()
    print("   Issue 3: 'Email not provided by LinkedIn' error")
    print("   → LinkedIn OpenID Connect product not approved")
    print("   → User's email is private or not verified")
    print("   → Email scope not granted by user")
    print()
    print("   Issue 4: 'Failed to authenticate' error")
    print("   → Check Flask application logs for detailed error")
    print("   → Verify FLASK_SECRET_KEY is set")
    print("   → Check that authlib is installed: pip install authlib")
    print()

    # Step 6: Next Steps
    print("🎯 Step 6: Next Steps")
    print("-" * 70)
    print()
    print("   1. ✅ Verify all environment variables are set correctly")
    print("   2. ✅ Add redirect URIs to LinkedIn app (see Step 3)")
    print("   3. ✅ Request 'Sign In with LinkedIn using OpenID Connect' product")
    print("   4. ✅ Test login and check Flask logs for errors")
    print("   5. ✅ Share error message if issue persists")
    print()

    print("=" * 70)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print()
    print("💡 To test the OAuth flow:")
    print("   1. Start the app: python app.py")
    print("   2. Go to: http://localhost:8080/login")
    print("   3. Click 'Continue with LinkedIn'")
    print("   4. Check the browser URL and Flask logs for errors")
    print()

if __name__ == "__main__":
    test_linkedin_oauth()
