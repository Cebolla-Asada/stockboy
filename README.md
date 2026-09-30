# stockboy
Collaborative space for the IFT401 Capstone :)


# Stockboy Setup
## 1. cloning the repo

```bash
git clone https://github.com/Cebolla-Asada/stockboy.git
cd stockboy/backend
```

## 2. creating the enviorment
```bash
python3 -m venv venv
```

Activate it:

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

## 3. Install the python requirments from the file

```bash
pip install -r requirements.txt
```

## 4. Set up MySQL

Install:

- MySQL Community Server
- MySQL Workbench

remember your root password when installing!!!

Create a database named:

```text
stockboy
```

Then run the SQL file located at:

```text
database/schema.sql
```

## 5. Create your `.env` file

Inside the `backend` folder, create a file named:

```text
.env
```

Add:

```text
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=stockboy
```

Replace `YOUR_MYSQL_PASSWORD` with your own local MySQL password.

## 6. Start the backend

```bash
python app.py
```

The Flask server should run at:

```text
http://127.0.0.1:5000
```

## 7. Test the setup

API status:

```text
http://127.0.0.1:5000/api/status
```

Database connection:

```text
http://127.0.0.1:5000/api/db-test
```

Frontend:

```text
http://127.0.0.1:5000/frontend/
```


done for now!!! 