# LeadLock AI — Local Setup Guide

Welcome to the LeadLock AI setup guide! Since you are running this project locally on your Mac without Docker, you need to manually install the databases (PostgreSQL and Redis) that power the backend.

Follow these step-by-step instructions. They are designed for beginners.

---

## Step 1: Install Homebrew (If you don't have it)
Homebrew is a package manager for Mac that makes installing software incredibly easy. 
Open a new Terminal window and run this command. (If you already have Homebrew, skip to Step 2).
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## Step 2: Install & Start Redis
Redis is a fast memory database used for AI context and real-time WebSocket events.

1. **Install Redis:**
   ```bash
   brew install redis
   ```
2. **Start the Redis background service:**
   ```bash
   brew services start redis
   ```
3. **Verify it is running:** Type `redis-cli ping` and it should reply with `PONG`.

---

## Step 3: Install & Start PostgreSQL
PostgreSQL is the main relational database where we store Tenants, Customers, and Inventory.

1. **Install PostgreSQL (version 16):**
   ```bash
   brew install postgresql@16
   ```
2. **Start the PostgreSQL background service:**
   ```bash
   brew services start postgresql@16
   ```
3. **Add it to your PATH** (Run these two commands so your Mac knows where Postgres is):
   ```bash
   echo 'export PATH="/usr/local/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

---

## Step 4: Create the Database and User
Our backend expects a specific database (`leadlock`) and a specific user (`leadlock` with password `leadlock_secret`) to exist.

1. **Enter the PostgreSQL terminal:**
   ```bash
   psql postgres
   ```
   *(Your terminal prompt will change to `postgres=#`)*

2. **Run the following SQL commands one by one:**
   ```sql
   CREATE USER leadlock WITH PASSWORD 'leadlock_secret';
   CREATE DATABASE leadlock OWNER leadlock;
   ALTER ROLE leadlock SUPERUSER;
   ```
3. **Type `\q` and press Enter** to exit the PostgreSQL terminal.

---

## Step 5: Run Database Migrations
Now that the database exists, we need to create the actual tables inside of it.

1. **Navigate to the backend folder:**
   ```bash
   cd "/Users/LENOVO/Desktop/LeadLock AI/leadlock_BE"
   ```
2. **Run Alembic (the migration tool):**
   ```bash
   alembic upgrade head
   ```
   *(If successful, you will see it output several lines creating tables).*

---

## Step 6: Start Your Servers
Once your databases are running and migrated, you can start the application servers. **Open a separate terminal window for each of these three commands.**

### 1. Start the Backend (Core API)
```bash
cd "/Users/LENOVO/Desktop/LeadLock AI/leadlock_BE"
uvicorn core_service.main:app --reload --port 8000
```

### 2. Start the Backend (Edge Worker - For Webhooks & AI)
```bash
cd "/Users/LENOVO/Desktop/LeadLock AI/leadlock_BE"
uvicorn edge_worker.main:app --reload --port 8001
```

### 3. Start the Frontend (Next.js Dashboard)
```bash
cd "/Users/LENOVO/Desktop/LeadLock AI/leadlock_FE"
npm run dev
```

You can now open **http://localhost:3000** in your browser to see the beautiful frontend, and it will be successfully connected to a working backend!
# LeadLock-AI
