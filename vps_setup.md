# Linode VPS set-up checklist

## Starting the server
https://www.linode.com/

Create Linode

Select Region, OS Ubuntu 24.04 LTS, label name, root password

## SSH Keys
Add SSH key; To list SSH keys locally run
ls -al ~/.ssh

To view public key run
cat ~/.ssh/id_ed25519.pub

If needed generate a new SSH key
ssh-keygen -t ed25519 -C 'email@address.com'

Add entire public key to SSH keys

## Assign Firewall and Create Linode
Create label 
Default Inbound: DROP/DENY
Default Outbound: ACCEPT

Create Linode and click into firewall rules

Add inbound rule 
Preset SSH
Add label
TCP protocol
Port 22 (SSH)
Sources IP/netmask + list IPs 
To get IP run
curl ifconfig.me

Accept, add rule

## Connect and Config Via Terminal
run ssh root@your-server-ip
type yes to remember IP of server
enter password

apt update && apt upgrade -y
timedatectl list-timezones | grep America
timedatectl set-timezone America/New_York
timedatectl

# Python environment
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y libpq-dev python3-dev build-essential

# Database tools (choose what you need)
sudo apt install -y postgresql postgresql-contrib  # PostgreSQL
# OR
sudo apt install -y mysql-server mysql-client      # MySQL
# OR
sudo apt install -y sqlite3                        # SQLite

# Security Configuration
## Create Non-Root User run
adduser your-username

# Add to sudo group
usermod -aG sudo your-username

# Test sudo access
su - your-username
sudo whoami

# Project-Specific Setup
Create Project structure, directories
mkdir -p ~/projects/sectors

## Cloning a repo
git clone https://github.com/username/reponame.git
cd reponame

# Or to get local files, create tar.gz, from local project folder
tar -czf sector_performance.tar.gz .

# scp to upload the archive to your vps
scp sector_performance.tar.gz username@your.vps.ip:~/projects/sectors/

# Unarchive files and remove archive file
tar -xzf sector_performance.tar.gz
rm sector_performance.tar.gz

# Clean up hidden files if needed
ls -a
rm .filename

# Python Environment on vps, from within projectname folder
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
## Do other installs as needed

## To deactivate venv just run
deactivate

# Migrate local db to vps
##Dump the local database to a .sql file
pg_dump -h localhost sector_db > sector_db_dump.sql
PGPASSWORD=yourpassword pg_dump -h localhost -U postgres -d sector_db -f sector_db_dump.sql -v

# Copy to vps
scp sector_db_dump.sql username@your.vps.ip:~/projects/sectors/

# Start and verify postgres
sudo service postgresql start
sudo service postgresql status

# Access postgres
sudo -i -u postgres psql

# Create db and user
CREATE DATABASE sector_db;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE sector_db TO dev_user;
\c sector_db
GRANT ALL ON SCHEMA public TO dev_user;

-- Optional but recommended
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dev_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dev_user;

\q

# May need to allow read perms to dump
# chmod 644 /root/projects/sectors/sector_db_dump.sql

# Restore the dump into the new DB (from project folder in terminal, not postgres user)
psql -U dev_user -h localhost -d sector_db -f /root/projects/sectors/sector_db_dump.sql

# Remove dump file
rm sector_db_dump.sql

# Create or confirm .env file contents
nano .env

# Test the script manually from inside the venv
python3 sector_performance.py

# Set up cron
## Get python path (python from the venv) and project path
which python3
realpath .

# Open editor
crontab -e

# Make cron entry 
schedule python_location script_location
*/5 * * * * /root/projects/sectors/venv/bin/python3 /root/projects/sectors/sector_performance.py >> /root/projects/sectors/cron_output.log 2>&1
30 16 * * 1-5
cat cron_output.log

# Git Deployment Workflow
Push your local folder to GitHub
SSHing into the VPS and run
git clone https://github.com/username/repo.git ~/projects/sectors
Or git pull for updates.

# Configure SSH Security (directly on server)
## Edit SSH config run
sudo nano ../etc/ssh/sshd_config

# Key changes to make:
Port 2222                   # Change from default 22
PermitRootLogin no          # Disable root login
PasswordAuthentication no   # Disable password login (use keys only)
PubkeyAuthentication yes    # Enable key authentication
AllowUsers your-username    # Only allow specific users, not in file by default

# Set Up SSH Keys (from your local machine if not done in Linode dashboard)
Generate key pair (if you don't have one)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy public key to server
ssh-copy-id -p 2222 your-username@your-server-ip

# Configure Firewall (UFW)
## Enable UFW
sudo ufw enable

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH on custom port
sudo ufw allow 2222/tcp

# Allow HTTP/HTTPS (if needed)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status

# Restart SSH Service
sudo systemctl restart sshd

# System Maintenance & Monitoring
## Configure Automatic Updates
## Install unattended-upgrades
sudo apt install unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades

# Edit configuration
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades

# Key settings:
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "your-email@example.com";



# Install Fail2Ban (Intrusion Prevention)
sudo apt install fail2ban

# Create local config
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit configuration
sudo nano /etc/fail2ban/jail.local

# Key settings:
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 2222


#
# See Below!!
#

echo 'installing fail2ban'
sudo apt install -y fail2ban

echo 'configuring fail2ban'
# Create local config, this preserves your settings during updates
cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Configure DEFAULT settings, these lines exist in [DEFAULT] section
sed -i '/^\[DEFAULT\]/,/^\[/ {
    s/^bantime *= .*/bantime = 3600/
    s/^findtime *= .*/findtime = 600/
    s/^maxretry *= .*/maxretry = 3/
}' /etc/fail2ban/jail.local

# First, add enabled = true right after [sshd] section
sed -i '/^\[sshd\]/a\
enabled = true' /etc/fail2ban/jail.local

# Then change port from ssh to 2222
sed -i '/^\[sshd\]/,/^\[.*\]/ {
    s/^port[[:space:]]*=[[:space:]]*ssh$/port = 2222/
}' /etc/fail2ban/jail.local

systemctl enable fail2ban
systemctl start fail2ban




# Set Up Log Rotation
Verify logrotate is installed
sudo apt install logrotate

# Check configuration
sudo nano /etc/logrotate.conf

# Development Environment Setup
## Install Essential Tools
## Development essentials
sudo apt install -y curl wget git vim htop tree unzip

# Install Docker (Optional but Recommended)
Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker your-username

# Install Docker Compose
sudo apt install docker-compose

# Set up Python virtual environment
cd ~/projects/stock-monitor
python3 -m venv venv
source venv/bin/activate

# Install Python Dependencies
Create requirements.txt
cat > requirements.txt << EOF
pandas
numpy
yfinance
psycopg2-binary
python-dotenv
requests
sqlalchemy
EOF

# Install dependencies
pip install -r requirements.txt

# Database Setup (PostgreSQL Example)
## Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE stock_monitor;
CREATE USER stock_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE stock_monitor TO stock_user;

# Environment Variables
# Create .env file
cat > ~/projects/stock-monitor/.env << EOF
DB_HOST=localhost
DB_NAME=stock_monitor
DB_USER=stock_user
DB_PASSWORD=your-secure-password
DB_PORT=5432
EOF

# Secure the file
chmod 600 ~/projects/stock-monitor/.env

# Cron Job Setup
## Set Up Cron for Daily Execution
## Edit crontab
crontab -e

# Add job (example: run daily at 6 PM EST after market close)
0 18 * * 1-5 /home/your-username/projects/stock-monitor/venv/bin/python /home/your-username/projects/stock-monitor/scripts/daily_monitor.py >> /home/your-username/projects/stock-monitor/logs/cron.log 2>&1

# Log Rotation for Cron Logs
# Create logrotate config for your project
sudo nano /etc/logrotate.d/stock-monitor

# Content:
/home/your-username/projects/stock-monitor/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 your-username your-username
}

# Monitoring & Alerts
# Install and Configure Postfix (for email alerts)
bash# Install postfix
sudo apt install postfix

# Configure as satellite system
sudo dpkg-reconfigure postfix

# Basic System Monitoring Script
# Create monitoring script

cat > ~/scripts/system_monitor.sh << 'EOF'

#!/bin/bash
# Simple system monitoring

DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.2f%%", $3*100/$2}')
CPU_LOAD=$(uptime | awk '{print $10}' | sed 's/,//')

echo "$(date): Disk: ${DISK_USAGE}%, Memory: ${MEMORY_USAGE}, Load: ${CPU_LOAD}" >> ~/logs/system_monitor.log

# Alert if disk usage > 80%
if [ $DISK_USAGE -gt 80 ]; then
    echo "High disk usage: ${DISK_USAGE}%" | mail -s "Server Alert" your-email@example.com
fi
EOF

chmod +x ~/scripts/system_monitor.sh

# Backup Strategy
## Set Up Automated Database Backups
## Create backup script
cat > ~/scripts/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/your-username/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -h localhost -U stock_user stock_monitor > $BACKUP_DIR/stock_monitor_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
EOF

chmod +x ~/scripts/backup_db.sh

# Add to cron (daily at 2 AM)
# 0 2 * * * /home/your-username/scripts/backup_db.sh

# Final Security Checks
# Check Open Ports
sudo netstat -tuln

# Verify Services
sudo systemctl status sshd
sudo systemctl status ufw
sudo systemctl status fail2ban

# Test SSH Connection
From local machine, test new SSH setup
ssh -p 2222 your-username@your-server-ip

# Documentation
Create README for Your Project
Document server details, setup, and maintenance procedures
# Include:
# - Server specifications
# - Installed software versions
# - Database schema
# - Cron job schedules
# - Backup procedures
# - Troubleshooting steps

# Quick Reference Commands
# Check system status
sudo systemctl status
htop
df -h
free -h

# Check logs
sudo journalctl -f
tail -f /var/log/auth.log

# Firewall status
sudo ufw status

# Active connections
sudo netstat -tuln

# Check fail2ban
sudo fail2ban-client status

Remember to:

Change all default passwords
Keep your local SSH keys secure
Regular security updates
Monitor logs periodically
Test backups regularly
Document any custom configurations