# Scripted Ansible

_currently a POC_

An interface to ansible from a python script(s)


### Usage

_again, just a POC_

`python3 scripted.py <files to run>`

From examples:

`python3 scripted.py roles/{a,b}.py`

`python3 scripted.py roles/big.py`

### Why

As a programmer, it felt weird to code in YAML.
The roles and playbooks _programming_ requires a (although small) learning curve.

As a programmer with a _fairly_ good background in Python, and especially with
Ansible being implemented in Python, it would've been simpler to drop the YAML
(the Ansible-YAML) learning curve and just program in Python.
Or simply put, do actual code instead of _Code as Config_.

### Advantages

- It _should be_ simpler to start, at least with a background in programming in
general;
- _Conventional/Actual_ programming language, the usual _loops_ and _ifs_;
- It's a _POC_, a.k.a. it can change and adapt;

### Drawbacks

- It's a _POC_, a.k.a. it doesn't have much yet


## Internals

_Some details on the current internal implementation_

Given a list of files to execute and a list of hosts to target, each file
is `read`, `compile`d and then, a thread is created for each host and the
code `exec`uted on the thread context.

Ather each file is executed, the threads are joined the result printed: _Success_
in case everything when as expected, _Failed_ and the traceback in case an
exception is thrown.

The _ansible scripts_ have 2 `local` variables accessible:

- `ansible`: a dynamic object to call an ansible module;
- `host`: the host name string, as passed;

**NOTE**: in the future, more variables may be passed.
