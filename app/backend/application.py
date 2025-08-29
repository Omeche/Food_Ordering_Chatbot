# Import Flask app from main.py
from main import app

# Expose the Flask app as "application" for Elastic Beanstalk
application = app

if __name__ == "__main__":
    application.run()