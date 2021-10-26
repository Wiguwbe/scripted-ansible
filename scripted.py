import importlib.util
import importlib.machinery
import os
import sys
import threading
from typing import Union
import traceback

from ansible.playbook.play_context import PlayContext
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from ansible.playbook.task import Task
from ansible.plugins.connection import ConnectionBase
from ansible.plugins.action import ActionBase
from ansible.plugins import loader

class AnsibleDynamicCommand:

    def __init__(self, parts: list = None, extra = None):
        if parts is None:
            parts = []
        self._parts = parts
        self._extra = extra
    
    def __getattr__(self, name):
        return AnsibleDynamicCommand([name] + self._parts, self._extra)
    
    def __call__(self, arg=None, **kwargs):
        if len(self._parts) == 0:
            raise TypeError('Not callable')
        key = str.join('.', self._parts)
        if arg is not None:
            params = {'_raw_params': arg}
        elif len(kwargs) > 0:
            params = {k:v for k,v in kwargs.items()}
        else:
            raise TypeError("Need at least one argument")
        return self._extra.run_cmd(key, params)

class DefaultDict:

    def __init__(self, extra):
        self._extra = extra
    
    def __getitem__(self, key):
        return AnsibleDynamicCommand([key], self._extra)

class AnsibleContext:
    
    def __init__(self, host: str):
        self.loader = DataLoader()
        self.play_context = PlayContext()
        self.play_context.remote_addr = host
        self.templar = Templar(self.loader)
        self.connection: ConnectionBase = loader.connection_loader.get(
            'ssh',
            self.play_context,
            '/dev/null'
        )
    
    def run_cmd(self, module: str, data: dict):
        task_vars = {
            'ansible_facts': {}
        }
        task = Task.load(data={
            module: data
        })

        if loader.action_loader.has_plugin(module):
            action_name = module
        else:
            action_name = 'normal'

        action: ActionBase = loader.action_loader.get(
            action_name,
            task,
            self.connection,
            self.play_context,
            self.loader,
            self.templar,
            loader
        )

        return action.run(task_vars=task_vars)



class AnsibleThread(threading.Thread):

    success = None
    error = None
    host = property(lambda s : s._host)

    def __init__(self, code, host):
        self._code = code
        self._host = host
        super().__init__()
    
    def run(self):
        # TODO prepare ansible related variables
        a_ctx = AnsibleContext(self._host)
        a_cmd = AnsibleDynamicCommand([], extra = a_ctx)
        try:
            exec(self._code, None, {'ansible': a_cmd, 'host': self._host})
            self.success = True
        except Exception as e:
            self.error = e
            self.success = False

def main(files: Union[list,str], hosts: list):
    if isinstance(files, str):
        files = [files]

    for file in files:
        with open(file) as fd:
            text = fd.read()
        code = compile(text, file, 'exec')

        # TODO start threads and run file
        threads = []
        for host in hosts:
            thread = AnsibleThread(code, host)
            thread.start()
            threads.append(thread)
        for t in threads:
            t.join()
        # and print results
        print(file)
        for t in threads:
            if t.success:
                print(t.host + '\tSuccess')
            else:
                print(t.host + '\tFailed')
                if t.error is not None:
                    e: Exception = t.error
                    traceback.print_tb(e.__traceback__)
                    print(type(e).__qualname__+ ': ' + str(e))

    
if __name__ == '__main__':
    files = sys.argv[1:]
    hosts = ['test.local', 'dred.local', 'fake.local']
    main(files, hosts)
