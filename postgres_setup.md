# Local Postgres Setup (macOS)

# Install PostgreSQL locally (macOS) if not already completed
brew install postgresql
brew services start postgresql

# To stop postgresql if running
brew services stop postgresql

# Create database locally, does not need to be executed in project directory
createdb db_name

# Test connection
psql -d db_name -c 'SELECT version();'

# DBeaver login as root
Use db_name and $whoami as user, with no password.

# Create dev user for db
## Connect as super user
psql -d postgres

## Create user
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE db_name TO dev_user;
ALTER USER dev_user CREATEDB;
exit

## Test the user 
psql -d db_name -U dev_user -h localhost
Enter the dev_user password