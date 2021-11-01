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

import _xxsubinterpreters as interpreters

hosts = []
scripts = []

_INIT_CODE = """
__builtins__.host = '{host}'
import sys
sys.path.insert(0, '{path}')
""".format(
    # fake format
    host='{host}',
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
max_len = 0
for host in hosts:
    interp = interpreters.create(isolated=0)
    # run init
    interpreters.run_string(interp, _INIT_CODE.format(host=host))
    interps[host] = interp
    # for printing purposes
    max_len = max(max_len, len(host))

max_len += 1

host_pad = {
    host: ' ' * (max_len - len(host))
    for host in hosts
}

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
        sys.exit(2)
