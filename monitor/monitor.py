
import argparse
import os
import sched
import signal
import sys
import time
import psutil
import socket


class CreateSystemDataset:

    def __init__(self, outfile_name=None, flush=False):
        print('Creating process started', file=sys.stderr)
        ncores = self.ncores = psutil.cpu_count()
        if outfile_name is None:
            self.outfile = sys.stdout
        else:
            self.outfile = open(outfile_name, 'w')
        self.flush = flush
        self.outfile.write(
            'Timestamp,  Uptime, NCPU, %CPU, ' + ', '.join(['%CPU' + str(i) for i in range(ncores)]) +
            ', %MEM, mem.total.KB, mem.used.KB, mem.avail.KB, mem.free.KB' +
            ', %SWAP, swap.total.KB, swap.used.KB, swap.free.KB' +
            ', io.read, io.write, io.read.KB, io.write.KB, io.read.ms, io.write.ms, disk.total.GB, disk.used.GB, '
            'disk.free.GB, hostname \n')
        self.prev_disk_stat = psutil.disk_io_counters()
        self.starttime = int(time.time())
        self.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'closed'):
            self.close()

    def close(self):
        if self.outfile is not sys.stdout:
            self.outfile.close()
        self.closed = True
        print('System monitor closed.', file=sys.stderr)

    def start(self):
        timestamp = int(time.time())
        uptime = timestamp - self.starttime
        total_cpu_percent = psutil.cpu_percent(percpu=False)
        percpu_percent = psutil.cpu_percent(percpu=True)
        mem_stat = psutil.virtual_memory()
        swap_stat = psutil.swap_memory()
        disk_stat = psutil.disk_io_counters()
        hdd = psutil.disk_usage('/')

        line = str(timestamp) + ', ' + str(uptime) + ', ' + \
            str(self.ncores) + ', ' + str(total_cpu_percent*self.ncores) + ', '
        line += ', '.join([str(i) for i in percpu_percent])
        line += ', ' + str(mem_stat.percent) + ', ' + str(mem_stat.total >> 10) + ', ' + str(
            mem_stat.used >> 10) + ', ' + str(mem_stat.available >> 10) + ', ' + str(mem_stat.free >> 10)
        line += ', ' + str(swap_stat.percent) + ', ' + str(swap_stat.total >> 10) + \
            ', ' + str(swap_stat.used >> 10) + ', ' + str(swap_stat.free >> 10)
        line += ', ' + str(disk_stat.read_count - self.prev_disk_stat.read_count) + ', ' + str(disk_stat.write_count - self.prev_disk_stat.write_count) + \
                ', ' + str((disk_stat.read_bytes - self.prev_disk_stat.read_bytes) >> 10) + ', ' + str((disk_stat.write_bytes - self.prev_disk_stat.write_bytes) >> 10) + \
                ', ' + str(disk_stat.read_time - self.prev_disk_stat.read_time) + \
                ', ' + str(disk_stat.write_time - self.prev_disk_stat.write_time) + \
                ', ' + str(hdd.total / (2**30)) + \
                ', ' + str(hdd.used / (2**30)) + \
                ', ' + str(hdd.free / (2**30)) + \
                ', ' + str(socket.gethostname())

        self.outfile.write(line + '\n')
        if self.flush:
            self.outfile.flush()
        self.prev_disk_stat = disk_stat





class ProcessSetMonitor:

    BASE_STAT = {
        'io.read': 0,
        'io.write': 0,
        'io.read.KB': 0,
        'io.write.KB': 0,
        'mem.rss.KB': 0,
        '%MEM': 0,
        '%CPU': 0,
        'nctxsw': 0,
        'nthreads': 0
    }

    KEYS = sorted(BASE_STAT.keys())

    def __init__(self, keywords, pids, outfile_name, flush=False):
        print('ProcessSet monitor started.', file=sys.stderr)
        if outfile_name is None:
            self.outfile = sys.stdout
        else:
            self.outfile = open(outfile_name, 'w')
        self.pids = pids
        self.keywords = keywords
        self.flush = flush
        self.outfile.write('Timestamp, Uptime, ' + ', '.join(self.KEYS) + '\n')
        self.starttime = int(time.time())
        self.poll_stat()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'closed'):
            self.close()

    def close(self):
        if self.outfile is not sys.stdout:
            self.outfile.close()
        self.closed = True
        print('ProcessSet monitor closed.', file=sys.stderr)

    def _stat_proc(self, proc, stat, visited):
        """ Recursively stat a process and its child processes. """
        if proc.pid in visited:
            return
        visited.add(proc.pid)
        io = proc.io_counters()
        mem_rss = proc.memory_info().rss
        mem_percent = proc.memory_percent('rss')
        nctxsw = proc.num_ctx_switches()
        nctxsw = nctxsw.voluntary + nctxsw.involuntary
        nthreads = proc.num_threads()
        cpu_percent = proc.cpu_percent()
        stat['io.read'] += io.read_count
        stat['io.write'] += io.write_count
        stat['io.read.KB'] += io.read_bytes
        stat['io.write.KB'] += io.write_bytes
        stat['mem.rss.KB'] += mem_rss
        stat['%MEM'] += mem_percent
        stat['nctxsw'] += nctxsw
        stat['nthreads'] += nthreads
        stat['%CPU'] += cpu_percent
        for c in proc.children():
            self._stat_proc(c, stat, visited)

    def poll_stat(self):
        visited = set()
        curr_stat = dict(self.BASE_STAT)
        timestamp = int(time.time())
        uptime = timestamp - self.starttime
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name'])
            except psutil.NoSuchProcess:
                pass
            else:
                if pinfo['pid'] not in visited:
                    if pinfo['pid'] in self.pids:
                        self._stat_proc(proc, curr_stat, visited)
                    else:
                        for k in self.keywords:
                            if k in pinfo['name'].lower():
                                self._stat_proc(proc, curr_stat, visited)
                                break  # for keyword
        curr_stat['%CPU'] = round(curr_stat['%CPU'], 3)
        curr_stat['%MEM'] = round(curr_stat['%MEM'], 3)
        curr_stat['io.read.KB'] >>= 10
        curr_stat['io.write.KB'] >>= 10
        curr_stat['mem.rss.KB'] >>= 10
        line = str(timestamp) + ', ' + str(uptime) + ', ' + \
            ', '.join([str(curr_stat[k]) for k in self.KEYS]) + '\n'
        self.outfile.write(line)
        if self.flush:
            self.outfile.flush()


def chprio(prio):
    try:
        psutil.Process(os.getpid()).nice(prio)
    except:
        print('Warning: failed to elevate priority!', file=sys.stderr)


def sigterm(signum, frame):
    raise KeyboardInterrupt()


def main():
    parser = argparse.ArgumentParser(
        description='')
    parser.add_argument('--interval', '-i', type=int, default=1, help='Interval')
    parser.add_argument('--flush', '-f', default=False, action='store_true',
                        help='writing on ram after each line is written.')
    parser.add_argument('--output', '-o', type=str, nargs='?', default=None,
                        required=False, help='Output file')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, sigterm)
    chprio(-20)
    scheduler = sched.scheduler(time.time, time.sleep)
    csd = CreateSystemDataset(args.output, args.flush)
    i = 1
    starttime = time.time()
    try:

        while True:
            scheduler.enterabs(
                time=starttime + i*args.interval, priority=2, action=CreateSystemDataset.start, argument=(csd,))

            scheduler.run()
            i += 1

    except KeyboardInterrupt:
        csd.close()

        sys.exit(0)


if __name__ == '__main__':
    main()
