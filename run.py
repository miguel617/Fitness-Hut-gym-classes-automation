from multiprocessing import Process
from app import app
import scheduler_update

def run_flask():
    app.run(debug=False)

def run_yml_update():
    scheduler_update.main()

if __name__ == '__main__':
    flask_process = Process(target=run_flask)
    script_process = Process(target=run_yml_update)

    flask_process.start()
    script_process.start()

    flask_process.join()
    script_process.join()
