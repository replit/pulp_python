# pulp_python

![Pulp CI](https://github.com/pulp/pulp_python/actions/workflows/ci.yml/badge.svg?branch=master)

![Pulp Nightly CI/CD](https://github.com/pulp/pulp_python/actions/workflows/nightly.yml/badge.svg)

A Pulp plugin to support hosting your own pip compatible Python packages.

For more information, please see the [documentation](https://pulp-python.readthedocs.io/en/latest/) or the 
[Pulp project page](https://pulpproject.org).

## Replit Fork
**For this fork in particular, the documentation should be accessed in the `docs` directory directly as we
have modified it.**

This plugin should never be installed manually and instead installed as part of the ansible playbook for
pulp in goval. It may happen, however, that you will need to make modifications or test things inside of a virtual
machine configured with ansible. In these cases, here are a few instructions on how to get going.

### Updating an ansible VM with pip
If you have uploaded you work, you can update the version of `pulp_python` installed on your VM by
installing wit pip and git. Type `/usr/local/lib/pulp/bin/pip install git+https://github.com/replit/pulp_python@your_branch`
in the console in your VM, and it should install the plugin. Always restart the workers and content
service by typing `sudo systemctl restart pulpcore-worker@* && sudo systemctl restart pulpcore-content`.

### Updating the code directly in the VM
If you need to update the code for pulp_python directly in the VM, you can do so by modifying the
plugin code stored in `/usr/local/lib/pulp/lib/python3.8/site-packages/pulp_python`. Always deleted all
the `__cache__` directories saved there, then restart the services to see your changes.
