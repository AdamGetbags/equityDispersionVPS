#!/bin/bash

#Save it as vps_setup.sh
#Make it executable: chmod +x vps_setup.sh
#Run it: sh vps_setup.sh 

# Exit immediately if any command fails
set -e

echo '=== VPS Update Script ==='
echo ''

# Prompt for server details upfront
read -p 'Enter server IP address: ' SERVER_IP
USERNAME='root'
NEWUSERNAME='second_user'

echo ''
echo 'Connecting to $USERNAME@$SERVER_IP...'

# ssh in, run commands
ssh -i ~/.ssh/id_ed25519 -t $USERNAME@$SERVER_IP "
echo '=== Running system updates on VPS ==='

echo 'update and upgrade'
DEBIAN_FRONTEND=noninteractive apt-get update 
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::='--force-confnew'

echo 'set timezone'
timedatectl set-timezone America/New_York

echo 'python setup'
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y libpq-dev python3-dev build-essential

echo 'postgres install'
sudo apt install -y postgresql postgresql-contrib

echo 'create non-root user'
echo 'adding user $NEWUSERNAME'
adduser $NEWUSERNAME

echo 'add to sudo group'
usermod -aG sudo $NEWUSERNAME

# Create .ssh directory and set permissions
mkdir -p /home/$NEWUSERNAME/.ssh
chmod 700 /home/$NEWUSERNAME/.ssh

# Copy root's authorized_keys to user, assumes key is set in linode dashboard
cp /root/.ssh/authorized_keys /home/$NEWUSERNAME/.ssh/authorized_keys

# Set ownership and permissions
chown -R $NEWUSERNAME:$NEWUSERNAME /home/$NEWUSERNAME/.ssh
chmod 600 /home/$NEWUSERNAME/.ssh/authorized_keys

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

# Start and verify postgres
sudo service postgresql start
sudo service postgresql status

# Execute all PostgreSQL commands in a single psql session
sudo -u postgres psql << 'EOF'
CREATE DATABASE test_db;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE test_db TO dev_user;
\c test_db
GRANT ALL ON SCHEMA public TO dev_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dev_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dev_user;
\q
EOF

# Backup the original config first
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Change Port from default 22 to 2222
sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config

# Uncomment and disable root login
sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Uncomment public key authentication
sed -i 's/^#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Uncomment AuthorizedKeysFile line
sed -i 's/^#AuthorizedKeysFile/AuthorizedKeysFile/' /etc/ssh/sshd_config

# Add AllowUsers line
echo "AllowUsers $NEWUSERNAME" >> /etc/ssh/sshd_config

# Test the SSH config for syntax errors
sshd -t

# If test passes, restart SSH service
if [ $? -eq 0 ]; then
    echo 'SSH config is valid. Restarting SSH service...'
    systemctl daemon-reload
    systemctl restart ssh.socket
    systemctl restart ssh
    echo 'SSH service restarted successfully!'
else
    echo 'ERROR: SSH config has syntax errors. Check the config file.'
    exit 1
fi

echo ''
echo '=== Updates completed - Starting interactive session ==='
exec /bin/bash
"

# echo 'test sudo access'
# su - skynet1
# sudo whoami
# exit

# echo
# echo 'Update completed successfully!'

# echo "fail2ban status"
# systemctl status fail2ban --no-pager -l

# echo "checking fail2ban jails"
# fail2ban-client status

# echo "checking postgresql status"
# sudo service postgresql status

# echo "checking postgre user and db setup"
# sudo -u postgres psql -U dev_user -h localhost -d test_db << 'EOF'
# -- Show current user and database
# SELECT current_user, current_database();

# -- Test table creation
# CREATE TABLE test_table (
#     id SERIAL PRIMARY KEY,
#     name VARCHAR(50),
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );

# -- Test insert
# INSERT INTO test_table (name) VALUES ('test_entry');

# -- Test select
# SELECT * FROM test_table;

# -- Test update
# UPDATE test_table SET name = 'updated_entry' WHERE id = 1;

# -- Test select again
# SELECT * FROM test_table;

# -- Clean up
# DROP TABLE test_table;

# -- Verify cleanup
# \dt

# \q
# EOF

# Now process the reboot if needed, wait, then log back in
