### Project : Item Catalog

This project sets up a **PostgreSQL** database for **item catalog** website
The provided python script **project.py** uses **Flask**

## Requirements
- Python
- PostgreSQL
- psycopg2 library
- Vagrant
- VirtualBox
- Vagrant file as provided by Udacity
- Catalog database with schema that is provided by Udacity

## About Project

- Created a Database which has Categories and Menu for each category
- Included CRUD (Create, Read, Update, Delete) operations for both of them
- Added JSON end points to view the database
- To do privileged operation that is Create, Update and Delete on Data
    - User should be logged in using either Google or Facebook


## Run the project

1. Run **vagrant up**
2. Run **vagrant ssh**
3. Login into Virtual box using **username** vagrant **password** vagrant
4. Change the directory and go the folder **Catalog**
5. run python file using "python project.py" command
