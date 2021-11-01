
from ansible.playbook.play_context import PlayContext as _PlayContext
from ansible.parsing.dataloader import DataLoader as _DataLoader
from ansible.template import Templar as _Templar
from ansible.playbook.task import Task as _Task
from ansible.plugins.connection import ConnectionBase as _ConnectionBase
from ansible.plugins.action import ActionBase as _ActionBase
from ansible.plugins import loader as _loader

class _AnsibleDynamicCommand:

    def __init__(self, parts: list = None):
        if parts is None:
            parts = []
        self._parts = parts

    def __getattr__(self, name):
        return _AnsibleDynamicCommand(self._parts + [name])

    def __call__(self, arg=None, **kwargs):
        if len(self._parts) == 0:
            raise TypeError('Not callable')
        key = str.join('.', self._parts)
        if arg is not None:
            params = {'_raw_params': arg}
        elif len(kwargs) > 0:
            # or simply pass by reference?
            params = {k:v for k,v in kwargs.items()}
        else:
            raise TypeError("Need at least one argument")
        return ansible_context.run_cmd(key, params)

class _AnsibleContext:
    def __init__(self, host: str):
        self.loader = _DataLoader()
        self.play_context = _PlayContext()
        self.play_context.remote_addr = host
        self.templar = _Templar(self.loader)
        self.connection: _ConnectionBase = _loader.connection_loader.get(
            'ssh', self.play_context, '/dev/null'
        )

    def run_cmd(self, module: str, data: dict):
        task_vars = {
            'ansible_facts': {}
        }
        task = _Task.load(data={
            module: data
        })
        if _loader.action_loader.has_plugin(module):
            action_name = module
        else:
            action_name = 'normal'

        action: _ActionBase = _loader.action_loader.get(
            action_name,
            task,
            self.connection,
            self.play_context,
            self.loader,
            self.templar,
            _loader
        )

        ret = action.run(task_vars=task_vars)
        try:
            # when doesn't fail, ret doesn't have key (at least sometimes)
            if ret['failed']:
                # invocation
                invoc = f'{module}(' + str.join(', ', (f"{k}={repr(v)}" for k,v in data.items())) + ')'
                raise RuntimeError(invoc + ': ' + ret['msg'])
        except KeyError:
            # doesn't matter
            pass

        return ret

# only init if `host` is in builtins
try:
    ansible_context = _AnsibleContext(host)
except NameError:
    pass

def __getattr__(name):
    return _AnsibleDynamicCommand([name])
