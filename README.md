Automate the booking of classes and schedule it via github actions.

The python script will be run via a dockerfile and should take like 2/3 mins in total to build the image and run it, per deployment.

Whenever we change the config file with the classes to schedule in "config.ini", we should run the "scheduler_update.py" and, it will change automatically the "scheduler.yml" file with the updated schedules.

A webapp was created in PythonAnywhere so that we have a very simple HTML site that can update the YAML in github in the backend: https://miguel6176.pythonanywhere.com/
