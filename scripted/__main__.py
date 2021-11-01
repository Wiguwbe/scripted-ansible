#
# run scripted ansible
#
# pass on the hosts and the scripts to run
#
#

import sys
import os
import threading
import traceback
import select
import fcntl

import _xxsubinterpreters as interpreters

hosts = []
scripts = []

_INIT_CODE = """
__builtins__.host = '{host}'
import sys
sys.path.insert(0, '{path}')
sys.stdout = open({fd}, 'w', 1)
""".format(
    # fake format
    host='{host}',
    fd='{fd}',
    path=os.getcwd()
)

class Worker(threading.Thread):

    success: bool = None
    error: Exception = None
    host: str = None

    def __init__(self, code, interp):
        super().__init__()
        self._code = code
        self._interp = interp

    def run(self):
        try:
            interpreters.run_string(self._interp, self._code)
            self.success = True
        except Exception as e:
            self.success = False
            self.error = e

class Logger(threading.Thread):

    _err_mask = select.POLLERR|select.POLLHUP|select.POLLNVAL

    def __init__(self, pipe_map: dict):
        super().__init__()
        self._count = len(pipe_map)
        self._pipe_map = pipe_map
        self._poll = select.poll()
        self._host_map = {}
        self._buffers = {}
        self._stdout = sys.stdout.fileno()
        self._host_pre = {}
        for host, (rp, _) in pipe_map.items():
            self._host_map[rp] = host
            self._poll.register(rp, select.POLLIN)
            self._buffers[host] = b''
            self._host_pre[host] = b'[' + str.encode(host) + b'] '


    def run(self):
        # poll for data
        while self._count > 0:
            items = self._poll.poll()
            for fd, evt in items:
                host = self._host_map[fd]
                buffer: bytes = self._buffers[host]
                if evt & self._err_mask:
                    # error or hangup, remove from queue
                    self._poll.unregister(fd)
                    self._count -= 1
                    continue
                buffer += os.read(fd, 1024)
                last_nl = buffer.rfind(b'\n') + 1
                if last_nl == 0:
                    # nothing new to write
                    continue
                to_write = buffer[:last_nl]
                buffer = buffer[last_nl:]
                pre = self._host_pre[host]
                for line in to_write.split(b'\n'):
                    if len(line) == 0:
                        continue
                    # prepend 'host' to output
                    os.write(self._stdout, pre + line + b'\n')


# quick trick to split hosts from scripts
for item in sys.argv[1:]:
    if item.endswith('.py'):
        scripts.append(item)
    else:
        hosts.append(item)

if len(hosts) == 0:
    print('No hosts passed')
    sys.exit(1)

if len(scripts) == 0:
    print('No scripts passed')
    sys.exit(1)

# start interpreters
interps = {}
pipes = {}
max_len = 0
for host in hosts:
    interp = interpreters.create(isolated=0)
    # for IPC
    r_fd, w_fd = os.pipe()
    pipes[host] = (r_fd, w_fd)
    # run init
    interpreters.run_string(interp, _INIT_CODE.format(host=host, fd=w_fd))
    interps[host] = interp
    # for printing purposes
    max_len = max(max_len, len(host))

max_len += 1

host_pad = {
    host: ' ' * (max_len - len(host))
    for host in hosts
}

logger_gatherer = Logger(pipes)
logger_gatherer.start()

# now for each script
for script in scripts:
    with open(script, encoding='utf-8') as fd:
        data = fd.read()

    # run threads
    threads = []
    for host in hosts:
        thread = Worker(data, interps[host])
        thread.host = host
        thread.start()
        threads.append(thread)

    # let them run, and join them
    for t in threads:
        t.join()

    error = False
    print('==', script)
    for t in threads:
        if t.success:
            print(t.host + host_pad[t.host] + 'Success')
        else:
            error = True
            print(t.host + host_pad[t.host] + 'Failed')
            e = t.error
            traceback.print_tb(e.__traceback__)
            print(type(e).__qualname__ + ': ' + str(e))

    if error:
        # don't continue
        print('Exiting due to prior errors')
        break

# cleanup pipes
for r,w in pipes.values():
    os.close(w)
    os.close(r)

# join thread
logger_gatherer.join()

# and remove interpreters
for i in interps.values():
    interpreters.destroy(i)

# and exit
