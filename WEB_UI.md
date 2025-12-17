# Job Monitor - Web UI Guide

Simple Flask-based web interface for CV management and job viewing.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This includes Flask and Werkzeug for the web UI.

### 2. Set Up Environment

Make sure your `.env` file has:
```
ANTHROPIC_API_KEY=your_api_key_here
USER_EMAIL=your@email.com  # Optional - default email for web UI
FLASK_SECRET_KEY=your-secret-key-here  # Optional - for session management
```

### 3. Run the Web Server

```bash
python app.py
```

Or:
```bash
flask run
```

The server will start at **http://localhost:5000**

## 📱 Features

### Home Page (`/`)
- Dashboard with statistics
- Quick links to upload CV and browse jobs
- User account overview

### Upload CV (`/upload`)
- **Drag & drop interface** for easy file upload
- Supports PDF, DOCX, and TXT (max 10MB)
- Real-time file validation
- AI-powered CV parsing (~$0.02 per upload)
- Automatic profile extraction

### My Profile (`/profile`)
- View extracted CV data
- See expertise summary
- Browse skills (technical & soft)
- View work experience with achievements
- Education and certifications
- Languages with proficiency levels
- Career highlights

### Jobs Dashboard (`/jobs`)
- View all matched jobs
- Filter by priority (High/Medium/Low)
- Filter by minimum match score
- Sort by relevance
- See match scores and reasoning

### Job Detail (`/jobs/<id>`)
- Full job description
- Detailed match analysis
- Key alignments with your profile
- Potential gaps
- Direct link to apply
- Mark as reviewed

## 🎨 Design

- **Modern UI** with gradient colors
- **Responsive design** works on desktop and mobile
- **Clean cards** for organized information
- **Color-coded priorities**: Green (High), Yellow (Medium), Red (Low)
- **Smooth transitions** and hover effects

## 🔐 Security

- Session-based user management
- Secure file upload handling
- File type and size validation
- Temporary file cleanup
- No sensitive data in URLs

## 📊 How It Works

1. **Upload CV**: File is saved, text extracted, and analyzed by Claude AI
2. **Profile Storage**: Structured data saved to database
3. **Job Matching**: Main.py runs job searches using your CV profile
4. **View Results**: Browse and filter matched jobs in the web UI

## 🔧 Configuration

### Custom Port

```bash
# Run on different port
flask run --port 8000
```

### Production Mode

For production deployment:

1. Set strong secret key in `.env`:
   ```
   FLASK_SECRET_KEY=generate-a-strong-random-key
   ```

2. Use production WSGI server (gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. Set up nginx as reverse proxy
4. Enable HTTPS with SSL certificate

## 📝 Notes

- **Job Search**: Still runs via `main.py` - web UI displays results
- **First Use**: Upload your CV first for best experience
- **Email**: Set via environment variable or enter on upload page
- **Sessions**: Uses Flask sessions to remember your email

## 🆚 Web UI vs CLI

**Web UI:**
- ✅ User-friendly interface
- ✅ Drag & drop file upload
- ✅ Visual job browsing
- ✅ Better for exploring data
- ❌ Can't run job searches (yet)

**CLI (`scripts/cv_cli.py`):**
- ✅ All features available
- ✅ Scriptable and automatable
- ✅ Better for power users
- ❌ Less visual

**Best of both:**
1. Use Web UI for CV upload and job viewing
2. Run `python main.py` for job searches
3. View results in Web UI

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill
```

### Can't Upload CV
- Check `ANTHROPIC_API_KEY` is set in `.env`
- Verify file is PDF, DOCX, or TXT
- Ensure file is under 10MB

### No Jobs Showing
- Run `python main.py` first to collect jobs
- Check filters aren't too restrictive

### Styling Issues
- Clear browser cache
- Check `web/templates/base.html` exists

## 🚧 Future Enhancements

- [ ] Run job searches from web UI
- [ ] Real-time job notifications
- [ ] Job application tracking
- [ ] Cover letter generation
- [ ] Multi-user authentication
- [ ] API endpoints for mobile app
- [ ] Advanced search filters
- [ ] Email digest configuration
- [ ] Dark mode toggle

## 💡 Tips

1. **Upload CV first** for accurate job matching
2. **Set primary CV** if you have multiple versions
3. **Use filters** to find relevant jobs quickly
4. **Check job details** for full match analysis
5. **Mark jobs as reviewed** to track your applications

Enjoy the new web interface! 🎉
