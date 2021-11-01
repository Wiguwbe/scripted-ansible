
import os

from scripted import ansible

# return values instead of `register`
ret = ansible.shell('ls')

# assignments instead of set_fact

tmpdir = '/tmp/' + host + '-dir'

ansible.file(path=tmpdir, state='directory', mode=0o755)

# conventional python loops
for item in ["file1.txt", "dred.bin", "vinho.grn"]:
    path = os.path.join(tmpdir + item)

    ansible.file(path=path, state='touch', mode=0o644)


# currently no imports :(

# `ansible` and `host` are globals passed through `locals` in `exec()`
