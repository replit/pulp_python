User Setup
==========

All workflow examples use the Pulp CLI. Install and setup from PyPI:

.. code-block:: bash

    pip install pulp-cli[pygments] # For color output
    pulp config create -e
    pulp status # Check that CLI can talk to Pulp

If you configured the ``admin`` user with a different password, adjust the configuration
accordingly. If you prefer to specify the username and password with each request, please see
``Pulp CLI`` documentation on how to do that.


Install ``pulpcore``
--------------------

Follow the `installation
instructions <https://docs.pulpproject.org/pulpcore/installation/index.html>`__
provided with pulpcore.

Install plugin
--------------

This document assumes that you have
`installed pulpcore <https://docs.pulpproject.org/pulpcore/installation/index.html>`_
into a the virtual environment ``pulpvenv``.

Users should install from **either** PyPI or source.

From Source
***********

.. code-block:: bash

   sudo -u pulp -i
   source ~/pulpvenv/bin/activate
   cd pulp_python
   pip install -e .
   django-admin runserver 24817

Make and Run Migrations
-----------------------

.. code-block:: bash

   pulpcore-manager makemigrations python
   pulpcore-manager migrate python

(Optional) Configure the google pub/sub service
-----------------------------------------------

Create a service account in the google cloud console and make sure to give it the pubsub role.
Once created, download the JSON key file and save it somewhere on disk. Type
``sudo systemctl edit pulpcore-content`` in your shell to create a configuration file for the
pulp-content service and copy this content into it.

.. code-block:: bash

    [Service]
    Environment="GOOGLE_APPLICATION_CREDENTIALS=<path to the JSON key file>"

Go back to the google cloud console and create a new topic for your application. Open the django
configuration file (Should live under ``/etc/pulp/settings.py``) for pulp and add the values for
``GOOGLE_PUBSUB_PROJECT_ID`` and ``GOOGLE_PUBSUB_TOPIC_ID``, which should be the label for the project
in which you created your pub/sub topic and the topic label itself respectively.

Run Services
------------

.. code-block:: bash

   pulpcore-manager runserver
   gunicorn pulpcore.content:server --bind 'localhost:24816' --worker-class 'aiohttp.GunicornWebWorker' -w 2
   sudo systemctl restart pulpcore-resource-manager
   sudo systemctl restart pulpcore-worker@1
   sudo systemctl restart pulpcore-worker@2
