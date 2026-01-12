run:

python3 task_runner.py --meta-path
python3 task_runner.py --where json

python3 task_runner.py --list
python3 task_runner.py run hello -- --name Marcel
python3 task_runner.py run path:./plugins/hello.py -- --name Marcel
python3 task_runner.py run hello --reload -- --name Marcel