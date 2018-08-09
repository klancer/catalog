# Udacity Item Catalog


## About
This is the fourth project for the Udacity Full Stack Nanodegree. The Item Catalog project consists of developing an application that provides a list of items within a variety of categories, as well as provide a user registration and authentication system. This project uses persistent data storage to create a RESTful web application that allows users to perform Create, Read, Update, and Delete operations.

A user does not need to be logged in in order to read the categories or items uploaded. However, users who created an item are the only users allowed to update or delete the item that they created.

This program uses third-party auth with Google. Some of the technologies used to build this application include Flask, Bootsrap, Jinja2, and SQLite.


## Skills used for this project
- Python
- HTML
- CSS
- Bootstrap
- Flask
- Jinja2
- SQLAchemy
- OAuth2
- Google Login


## Some things you might need
- Ensure that Python, the python package psycopg2, Vagrant, and VirtualBox are installed. [Vagrantfile link](https://github.com/udacity/fullstack-nanodegree-vm/blob/master/vagrant/Vagrantfile) is here.
- Download or clone the [fullstack-nanodegree-vm](https://github.com/udacity/fullstack-nanodegree-vm) repository.
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)


## Getting Started
- Install Vagrant and VirtualBox
- Clone the Vagrantfile from the Udacity Repo
- Clone this repo into the `catalog/` directory found in the Vagrant directory
- Run `vagrant up` to run the virtual machine, then `vagrant ssh` to login to the VM
- run application with `python project.py` from within its directory
- To add some sample data to the project db
  run application with `python lotsofmenus.py` for sample data to the db
- go to `http://localhost:8000` to access the application
- *if first time running, you must add a category before adding an item

## Known issues
- No validation on forms

## Possible improvements
- Add an additional data model so that users can add Stores
- Image Upload, possible future addition with file upload
- Styling and layout could improve
- Implement CSRF protection on CRUD operations.



