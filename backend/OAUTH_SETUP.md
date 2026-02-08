# OAuth Setup Guide for Job Monitor

This guide will help you set up Google and LinkedIn OAuth login for Job Monitor.

## Table of Contents
- [Google OAuth Setup](#google-oauth-setup)
- [LinkedIn OAuth Setup](#linkedin-oauth-setup)
- [Environment Configuration](#environment-configuration)
- [Testing OAuth](#testing-oauth)

---

## Google OAuth Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: "Job Monitor" (or your choice)
4. Click "Create"

### 2. Enable Google+ API

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Google+ API"
3. Click "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen first:
   - User Type: **External**
   - App name: **Job Monitor**
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `email`, `profile`, `openid`
   - Test users: Add your email (for testing)

4. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: **Job Monitor Web Client**
   - Authorized JavaScript origins:
     ```
     http://localhost:8080
     https://your-domain.com
     ```
   - Authorized redirect URIs:
     ```
     http://localhost:8080/authorize/google
     https://your-domain.com/authorize/google
     ```
   - Click "Create"

5. **Copy your credentials**:
   - Client ID: `xxxxxxxxx.apps.googleusercontent.com`
   - Client Secret: `xxxxxxxxx`

### 4. Add to Environment Variables

Add to your `.env` file:
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

---

## LinkedIn OAuth Setup

### 1. Create a LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Click "Create app"
3. Fill in the form:
   - App name: **Job Monitor**
   - LinkedIn Page: Select or create a page
   - Privacy policy URL: Your URL (or localhost for development)
   - App logo: Upload a logo (optional)
4. Click "Create app"

### 2. Configure OAuth Settings

1. Go to the "Auth" tab
2. Add **Authorized redirect URLs**:
   ```
   http://localhost:8080/authorize/linkedin
   https://your-domain.com/authorize/linkedin
   ```
3. Click "Update"

### 3. Request API Access

1. Go to the "Products" tab
2. Request access to:
   - **Sign In with LinkedIn using OpenID Connect**
   - Click "Request access" and wait for approval (usually instant)

### 4. Get Credentials

1. Go back to the "Auth" tab
2. Find your credentials:
   - Client ID: `xxxxxxxxx`
   - Client Secret: Click "Show" to reveal

### 5. Add to Environment Variables

Add to your `.env` file:
```env
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
```

---

## Environment Configuration

### Complete .env File

Copy `.env.example` to `.env` and fill in all values:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Flask
FLASK_SECRET_KEY=your-random-secret-key-here
FLASK_ENV=development

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# AI/ML
ANTHROPIC_API_KEY=your-anthropic-key

# Job Collectors
JSEARCH_API_KEY=your-jsearch-key
ACTIVEJOBS_API_KEY=your-activejobs-key
```

### Generate Flask Secret Key

Run in Python:
```python
import secrets
print(secrets.token_hex(32))
```

---

## Testing OAuth

### 1. Install Dependencies

```bash
pip install authlib
```

Or from requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Start the Application

```bash
python app.py
```

### 3. Test Google Login

1. Open browser: `http://localhost:8080/login`
2. Click "Continue with Google"
3. Select your Google account
4. Grant permissions
5. You should be redirected to the dashboard

### 4. Test LinkedIn Login

1. Open browser: `http://localhost:8080/login`
2. Click "Continue with LinkedIn"
3. Enter LinkedIn credentials
4. Grant permissions
5. You should be redirected to the dashboard

---

## Railway Deployment

### 1. Set Environment Variables

In Railway dashboard, add all environment variables from `.env`:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
FLASK_SECRET_KEY=...
DATABASE_URL=... (automatically set by Railway)
```

### 2. Update OAuth Redirect URIs

For each provider, add your Railway domain to authorized redirect URIs:

**Google**:
```
https://your-app.up.railway.app/authorize/google
```

**LinkedIn**:
```
https://your-app.up.railway.app/authorize/linkedin
```

### 3. Deploy

```bash
git add .
git commit -m "Add OAuth login"
git push origin main
```

Railway will automatically deploy.

---

## Troubleshooting

### "redirect_uri_mismatch" Error

**Problem**: OAuth redirect URI doesn't match configured URIs

**Solution**:
1. Check that the redirect URI in your OAuth provider settings exactly matches the URL in your application
2. Include both `http://localhost:8080/authorize/google` (for local) and `https://your-domain.com/authorize/google` (for production)
3. No trailing slashes!

### "invalid_client" Error

**Problem**: Client ID or Client Secret is incorrect

**Solution**:
1. Double-check credentials in `.env` file
2. Ensure no extra spaces or quotes
3. Regenerate credentials if needed

### "Failed to get user information"

**Problem**: OAuth provider didn't return user email

**Solution**:
1. Ensure you've requested the correct scopes (`email`, `profile`, `openid`)
2. For LinkedIn, ensure "Sign In with LinkedIn using OpenID Connect" is approved
3. Check that the user's email is verified with the provider

### "Email not provided by Google/LinkedIn"

**Problem**: User's email is private or not shared

**Solution**:
1. For Google: Email scope must be included
2. For LinkedIn: Ensure OpenID Connect product is approved
3. Ask user to make email public in their profile settings

---

## Security Best Practices

1. **Never commit `.env`** file to Git (it's in `.gitignore`)
2. **Use different credentials** for development and production
3. **Rotate secrets** regularly
4. **Enable HTTPS** in production (required by OAuth providers)
5. **Limit OAuth scopes** to only what's needed (`email`, `profile`)
6. **Monitor OAuth usage** in provider dashboards

---

## Additional Resources

- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [LinkedIn OAuth Documentation](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [Authlib Documentation](https://docs.authlib.org/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)

---

## Need Help?

If you encounter issues:
1. Check browser console for errors
2. Check Flask logs for error messages
3. Verify all environment variables are set correctly
4. Ensure OAuth redirect URIs match exactly
5. Test with a different browser or incognito mode

Good luck with your OAuth setup! 🚀
