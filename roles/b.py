b = 666

from scripted import ansible

ansible.file(path='/tmp/' + host + '.txt', state='touch')
