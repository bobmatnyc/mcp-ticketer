.. MCP Ticketer documentation master file

MCP Ticketer Documentation
===========================

.. image:: https://img.shields.io/pypi/v/mcp-ticketer.svg
   :target: https://pypi.org/project/mcp-ticketer
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/mcp-ticketer.svg
   :target: https://pypi.org/project/mcp-ticketer
   :alt: Python versions

.. image:: https://readthedocs.org/projects/mcp-ticketer/badge/?version=latest
   :target: https://mcp-ticketer.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Universal ticket management interface for AI agents with MCP (Model Context Protocol) support.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   USER_GUIDE
   examples

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   cli
   adapters
   MCP_INTEGRATION
   CONFIGURATION

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation

   development
   api
   DEVELOPER_GUIDE
   API_REFERENCE
   ADAPTERS
   MIGRATION_GUIDE

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   changelog
   license
   support

Features
--------

* **Universal Ticket Model**: Simplified to Epic, Task, and Comment types
* **Multiple Adapters**: Support for JIRA, Linear, GitHub Issues, and AI-Trackdown
* **MCP Integration**: Native support for AI agent interactions
* **High Performance**: Smart caching and async operations
* **Rich CLI**: Beautiful terminal interface with colors and tables
* **State Machine**: Built-in state transitions with validation
* **Advanced Search**: Full-text search with multiple filters

Quick Installation
------------------

.. code-block:: bash

   # From PyPI
   pip install mcp-ticketer

   # With specific adapters
   pip install mcp-ticketer[jira]
   pip install mcp-ticketer[linear]
   pip install mcp-ticketer[github]
   pip install mcp-ticketer[all]

Quick Example
-------------

.. code-block:: bash

   # Initialize configuration
   mcp-ticket init --adapter jira

   # Create a ticket
   mcp-ticket create "Fix login bug" --priority high

   # List tickets
   mcp-ticket list --state open

   # Run MCP server
   mcp-ticket-server

Supported Adapters
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Adapter
     - Status
     - Description
   * - JIRA
     - ✅ Stable
     - Full support for JIRA Cloud and Server
   * - Linear
     - ✅ Stable
     - Complete Linear API integration
   * - GitHub
     - ✅ Stable
     - GitHub Issues and Projects support
   * - AI-Trackdown
     - ✅ Stable
     - Local file-based ticket storage
   * - GitLab
     - 🚧 Planned
     - GitLab Issues integration (coming soon)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`