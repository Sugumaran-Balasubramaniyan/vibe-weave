# GlassBox Sentinel - Nginx Deployment Guide

This guide will help you deploy the GlassBox Sentinel on your server using Nginx with your domain `glassbox.sugumaran-balasubramaniyan.com`.

---

## 🎯 **Deployment Options**

### **Option 1: Static Demo (Legacy — not suitable for the interactive hub)**
- Pure HTML/JS/CSS - No backend required
- Instant deployment
- Works perfectly for demonstrations
- Do not use for the live project hub: it cannot provide the API or SSE demo.

### **Option 2: Full Backend (required for the interactive hub)**
- FastAPI + Uvicorn backend
- Nginx as reverse proxy
- Full SSE streaming support
- Real API endpoints

---

## 🚀 **Option 1: Deploy Static Demo**

### **Step 1: Copy demo file to web directory**

```bash
# Create web directory
sudo mkdir -p /var/www/glassbox

# Copy the demo HTML file
sudo cp /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger/static/demo-index.html /var/www/glassbox/

# Set permissions
sudo chown -R www-data:www-data /var/www/glassbox
sudo chmod -R 755 /var/www/glassbox
```

### **Step 2: Copy nginx configuration**

```bash
# Copy nginx config
sudo cp /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger/deploy/nginx-glassbox-static.conf /etc/nginx/sites-available/glassbox

# Create symlink
sudo ln -sf /etc/nginx/sites-available/glassbox /etc/nginx/sites-enabled/glassbox
```

### **Step 3: Get SSL Certificate**

```bash
# Use certbot to get SSL certificate
sudo certbot --nginx -d glassbox.sugumaran-balasubramaniyan.com -d www.glassbox.sugumaran-balasubramaniyan.com

# Follow the prompts (agree to terms, provide email)
```

> **Note:** If certbot fails, try with `--standalone` first, then configure nginx:
> ```bash
> sudo certbot certonly --standalone -d glassbox.sugumaran-balasubramaniyan.com -d www.glassbox.sugumaran-balasubramaniyan.com
> ```

### **Step 4: Test and reload nginx**

```bash
# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### **Step 5: Verify**

Open in browser: **https://www.glassbox.sugumaran-balasubramaniyan.com/**

You should see the GlassBox Sentinel demo page! ✅

---

## 🚀 **Option 2: Deploy Full Backend**

### **Step 1: Install dependencies**

```bash
cd /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger

# Create virtual environment (if not already created)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **Step 2: Create systemd service for GlassBox Sentinel**

```bash
# Create service file
sudo nano /etc/systemd/system/glassbox.service
```

Add this content:
```ini
[Unit]
Description=GlassBox Sentinel
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger
Environment="PYTHONPATH=/home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger"
ExecStart=/home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save and exit (Ctrl+X, Y, Enter)

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable glassbox
sudo systemctl start glassbox

# Check status
sudo systemctl status glassbox
```

### **Step 3: Copy nginx configuration**

```bash
# Copy backend nginx config
sudo cp /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger/deploy/nginx-glassbox-backend.conf /etc/nginx/sites-available/glassbox

# Create symlink
sudo ln -sf /etc/nginx/sites-available/glassbox /etc/nginx/sites-enabled/glassbox
```

### **Step 4: Get SSL Certificate**

```bash
# Temporarily stop nginx to use standalone mode
sudo systemctl stop nginx

# Get certificate
sudo certbot certonly --standalone -d glassbox.sugumaran-balasubramaniyan.com -d www.glassbox.sugumaran-balasubramaniyan.com

# Restart nginx
sudo systemctl start nginx
```

### **Step 5: Test and reload nginx**

```bash
# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### **Step 6: Verify**

Check health endpoint:
```bash
curl https://glassbox.sugumaran-balasubramaniyan.com/health
# Should return: {"status": "ok"}
```

Open in browser: **https://www.glassbox.sugumaran-balasubramaniyan.com/**

---

## 🔧 **Troubleshooting**

### **Issue: Nginx config test fails**

```bash
sudo nginx -t
```

Common errors:
- **SSL certificate not found**: Run certbot first
- **Syntax error**: Check the nginx config file for typos
- **Port already in use**: Check what's using port 80/443

### **Issue: SSL certificate not working**

```bash
# Check certbot certificates
sudo certbot certificates

# Renew if needed
sudo certbot renew --force-renewal

# Check if certbot timer is active
sudo systemctl list-timers | grep certbot
```

### **Issue: GlassBox Sentinel service fails to start**

```bash
# Check logs
sudo journalctl -u glassbox -f

# Check if port 8000 is free
ss -tulnp | grep 8000

# Try running manually
cd /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **Issue: 502 Bad Gateway**

This means nginx can't reach your FastAPI app:

```bash
# Check if GlassBox Sentinel is running
curl http://127.0.0.1:8000/health

# Check GlassBox Sentinel logs
sudo journalctl -u glassbox -f

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## 📊 **Configuration Files**

| File | Location | Purpose |
|------|----------|---------|
| `demo-index.html` | Legacy static-only demo; not used by the interactive hub |
| `nginx-glassbox-static.conf` | Legacy static-only config; do not use for the hub |
| `nginx-glassbox-backend.conf` | `/etc/nginx/sites-available/glassbox` | Nginx config (backend) |
| `glassbox.service` | `/etc/systemd/system/glassbox.service` | Systemd service |

---

## 🎯 **Final Checklist**

### **Legacy Static Demo (do not use for the interactive hub):**
- [ ] Demo file copied to `/var/www/glassbox/`
- [ ] Nginx static config in place
- [ ] SSL certificate obtained
- [ ] Nginx reloaded
- [ ] Site accessible at https://www.glassbox.sugumaran-balasubramaniyan.com

### **For Full Backend:**
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Systemd service created and running
- [ ] Nginx backend config in place
- [ ] SSL certificate obtained
- [ ] Nginx reloaded
- [ ] Health endpoint works
- [ ] Site accessible at https://www.glassbox.sugumaran-balasubramaniyan.com

---

## 🔄 **Updating Your Deployment**

### **Legacy static deployment:**

Do not use `deploy-static.sh` for the interactive hub; it intentionally exits with guidance to use the backend deployment.
```bash
# Copy new version
sudo cp /path/to/new/demo-index.html /var/www/glassbox/

# No nginx reload needed for static files
```

### **Update Backend:**
```bash
# Stop service
sudo systemctl stop glassbox

# Update code
cd /home/ubuntu/mistral-vibe-hackathon/projects/glass-box-debugger
git pull  # or copy new files

# Install new dependencies (if any)
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start glassbox
sudo systemctl reload nginx
```

---

## 📞 **Need Help?**

### **Check these first:**
```bash
# Nginx status
sudo systemctl status nginx

# Nginx error logs
sudo tail -50 /var/log/nginx/error.log

# GlassBox Sentinel service status
sudo systemctl status glassbox

# GlassBox Sentinel logs
sudo journalctl -u glassbox -n 50

# Certbot status
sudo certbot certificates
```

### **Common Commands:**
```bash
# Restart everything
sudo systemctl restart nginx glassbox

# Check all services
sudo systemctl status nginx glassbox

# Renew SSL certificates
sudo certbot renew

# Reload nginx after config changes
sudo nginx -t && sudo systemctl reload nginx
```

---

## ✅ **You're Done!**

Your GlassBox Sentinel is now live at:

**https://glassbox.sugumaran-balasubramaniyan.com**

Enjoy your demo! 🎉
