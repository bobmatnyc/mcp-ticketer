Installation
============

This guide covers the installation of MCP Ticketer on various platforms.

Requirements
------------

* Python 3.9 or higher
* pip package manager
* Virtual environment (recommended)

Installation Methods
--------------------

From PyPI (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^

The easiest way to install MCP Ticketer is from PyPI using pip:

.. code-block:: bash

   pip install mcp-ticketer

Installing with Specific Adapters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can install MCP Ticketer with support for specific ticket systems:

.. code-block:: bash

   # JIRA support
   pip install mcp-ticketer[jira]

   # Linear support
   pip install mcp-ticketer[linear]

   # GitHub Issues support
   pip install mcp-ticketer[github]

   # All adapters
   pip install mcp-ticketer[all]

   # Development dependencies
   pip install mcp-ticketer[dev]

From Source
^^^^^^^^^^^

To install from the latest source code:

.. code-block:: bash

   git clone https://github.com/mcp-ticketer/mcp-ticketer.git
   cd mcp-ticketer
   pip install -e .

Using Virtual Environment
-------------------------

We strongly recommend using a virtual environment to avoid conflicts with other packages:

.. code-block:: bash

   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   # On Linux/macOS:
   source .venv/bin/activate
   # On Windows:
   venv\Scripts\activate

   # Install MCP Ticketer
   pip install mcp-ticketer

Using pipx (Isolated Installation)
-----------------------------------

For an isolated installation that won't interfere with other Python packages:

.. code-block:: bash

   pipx install mcp-ticketer

Docker Installation
-------------------

A Docker image is available for containerized deployment:

.. code-block:: bash

   docker pull mcptickets/mcp-ticketer:latest
   docker run -it mcptickets/mcp-ticketer mcp-ticket --help

Verifying Installation
----------------------

After installation, verify that MCP Ticketer is installed correctly:

.. code-block:: bash

   # Check CLI version
   mcp-ticket --version

   # Check Python import
   python -c "import mcp_ticketer; print(mcp_ticketer.__version__)"

   # Run help command
   mcp-ticket --help

Platform-Specific Notes
------------------------

macOS
^^^^^

On macOS, you may need to install Xcode Command Line Tools:

.. code-block:: bash

   xcode-select --install

Windows
^^^^^^^

On Windows, ensure you have the latest Visual C++ redistributables installed.
Some adapters may require additional setup for Windows authentication.

Linux
^^^^^

Most Linux distributions include Python by default. Ensure you have Python 3.9+:

.. code-block:: bash

   python3 --version

Troubleshooting
---------------

Common Installation Issues
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Permission Denied**

If you encounter permission errors, use the ``--user`` flag:

.. code-block:: bash

   pip install --user mcp-ticketer

**SSL Certificate Error**

For SSL certificate issues, you can temporarily use:

.. code-block:: bash

   pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org mcp-ticketer

**Dependency Conflicts**

If you have dependency conflicts, try creating a fresh virtual environment:

.. code-block:: bash

   python -m venv fresh_env
   source fresh_env/bin/activate
   pip install mcp-ticketer

Uninstallation
--------------

To uninstall MCP Ticketer:

.. code-block:: bash

   pip uninstall mcp-ticketer

Next Steps
----------

After successful installation, proceed to:

* :doc:`quickstart` - Get started with basic usage
* :doc:`configuration` - Configure adapters and settings
* :doc:`cli-reference` - Explore CLI commands