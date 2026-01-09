# 🚀 AI Platform - Quick Start Scripts

Easy-to-use scripts for starting and stopping the entire platform with one click.

## 📋 Files

### Start Platform
- **`START-PLATFORM.bat`** - Double-click to start (Windows)
- **`start-platform.ps1`** - PowerShell version

### Stop Platform
- **`STOP-PLATFORM.bat`** - Double-click to stop all services
- **`stop-platform.ps1`** - PowerShell version

## 🎯 Quick Start

### Option 1: Double-Click (Easiest)
1. Double-click **`START-PLATFORM.bat`**
2. Wait for all services to start (~15 seconds)
3. Browser opens automatically at http://localhost:3001

### Option 2: PowerShell
```powershell
.\start-platform.ps1
```

## 🛑 Stop Platform

### Option 1: Double-Click
Double-click **`STOP-PLATFORM.bat`**

### Option 2: PowerShell
```powershell
.\stop-platform.ps1
```

### Option 3: Manual
Close all PowerShell windows that were opened

## 📡 What Gets Started

The script starts 5 services in separate windows:

| Service | Port | Window Title | Purpose |
|---------|------|--------------|---------|
| **Redis Server** | 6379 | Redis Server | Caching & task queue |
| **Celery Worker** | - | Celery Worker | Background tasks |
| **FastAPI Backend** | 8000 | FastAPI Backend | API server |
| **Next.js Frontend** | 3001 | Next.js Frontend | Web interface |

## 🌐 URLs After Startup

### Frontend
- **Main App**: http://localhost:3001
- **Document Intelligence**: http://localhost:3001/documents
- **AI Agents**: http://localhost:3001/agents
- **Admin Dashboard**: http://localhost:3001/admin

### Backend
- **API Base**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Admin Login
- **Username**: `admin`
- **Password**: `SecureAdmin123!`

## ⚙️ Prerequisites

### Backend
- Python 3.11+ installed
- Virtual environment created: `python -m venv .venv`
- Dependencies installed: `pip install -r requirements.txt`

### Frontend
- Node.js 18+ installed
- Dependencies installed: `npm install`

## 🔧 Troubleshooting

### Script Won't Run
If you get "script execution disabled" error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Services Not Starting
Check each window for error messages:
- **Redis**: Check if Redis folder exists in Backend_AIPROJ/Redis
- **Backend**: Ensure virtual environment exists (`.venv` folder)
- **Frontend**: Ensure `node_modules` exists (run `npm install`)

### Port Already in Use
Stop the platform first:
```powershell
.\stop-platform.ps1
```

Or manually kill processes:
```powershell
# Kill specific ports
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
Get-Process -Id (Get-NetTCPConnection -LocalPort 3001).OwningProcess | Stop-Process
```

## 📝 Testing Checklist

After starting the platform:

### ✅ Backend Health
- [ ] Visit http://localhost:8000/docs - Should show Swagger UI
- [ ] Visit http://localhost:8000/health - Should return `{"status":"ok"}`

### ✅ Frontend Pages
- [ ] Home page loads (http://localhost:3001)
- [ ] 3D animation displays
- [ ] Sidebar navigation works
- [ ] No console errors (F12 → Console)

### ✅ Document Intelligence
- [ ] Can upload documents
- [ ] RAG Search tab works
- [ ] Q&A tab shows LLM warning if not configured
- [ ] Summarize tab displays
- [ ] Analytics tab displays

### ✅ AI Agents
- [ ] Chat interface loads
- [ ] Can send messages
- [ ] Agent cards are clickable

### ✅ Admin Dashboard
- [ ] Login works (admin / SecureAdmin123!)
- [ ] System stats display
- [ ] LLM status shows
- [ ] Auto-refresh works

## 🐛 Report Issues

If you find issues:
1. Check the terminal windows for error messages
2. Note which service failed
3. Copy error messages
4. Report to developer with:
   - Which service failed
   - Error message
   - What you were trying to do

## 💡 Tips

- **First Time Setup**: Services may take 15-20 seconds to fully start
- **Browser Auto-Open**: The script automatically opens your browser
- **Keep Windows Open**: Don't close the PowerShell windows while testing
- **Check Logs**: Each service window shows real-time logs
- **Quick Restart**: Stop → Wait 5 seconds → Start

---

Made with ❤️ for seamless development and testing
