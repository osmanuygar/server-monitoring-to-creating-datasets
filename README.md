# server-monitoring-to-creating-datasets

You can create a csv file which is system usage resources(i.e. ram usage, cpu usage ...). We used it for creating example datasets on our local PC or server. 

### Installation

```bash
# Install from repository
$ git clone https://github.com/osmanuygar/server-monitoring-to-creating-datasets.git
$ cd cd server-monitoring-to-creating-datasets/

# Install dependencies.
$ pip install -r requirements.txt

# example usage
$ python3 monitor.py -i 10 -o test.txt
```

### Usage

```bash
$python3 monitor.py --help
usage: monitor.py [-h] [--interval INTERVAL] [--flush] [--output [OUTPUT]]

optional arguments:
  -h, --help            show this help message and exit
  --interval INTERVAL, -i INTERVAL
                        Interval
  --flush, -f           writing on ram after each line is written.
  --output [OUTPUT], -o [OUTPUT]
                        Output file

```