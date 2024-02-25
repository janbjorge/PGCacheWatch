# Setup and CLI Usage

Setting up PGCacheWatch involves installing the package, configuring your PostgreSQL database for NOTIFY/LISTEN, and utilizing the provided Command Line Interface (CLI) for managing database triggers and functions. This section outlines the steps to get started and explains the functionalities of the CLI tool.

### Installation

Begin by installing PGCacheWatch using pip:

```bash
pip install pgcachewatch
```

This command installs PGCacheWatch along with its dependencies, including `asyncpg` for asynchronous database communication.

### Configuring PostgreSQL for NOTIFY/LISTEN

PGCacheWatch leverages PostgreSQL's NOTIFY/LISTEN mechanism to receive real-time notifications about database changes. To use this feature, you must set up triggers and functions in your database that emit NOTIFY signals on data changes. 

### Using the PGCacheWatch CLI

The PGCacheWatch CLI simplifies the process of setting up and managing the necessary database objects for NOTIFY/LISTEN. Here's an overview of the CLI commands and their purposes:

#### Install Command
Sets up triggers and functions on specified tables to emit NOTIFY signals. This is crucial for initializing PGCacheWatch's event listening capabilities.

```bash
pgcachewatch install <table_name(s)>
```
`<table_name(s)>`: Specify one or more table names to set up NOTIFY triggers. The CLI will generate and execute the SQL necessary to create these database objects.

#### Uninstall Command
Removes the triggers and functions created by the install command, cleaning up the database objects associated with PGCacheWatch.

```bash
pgcachewatch uninstall
```

### Best Practices

- **Testing**: Before applying changes in a production environment, test the CLI commands in a development or staging database to ensure they work as expected.
- **Backup**: Always back up your database before making schema changes, including installing or uninstalling triggers and functions.
- **Documentation**: Keep documentation of the custom options used (channel names, function names, etc.) for future reference or maintenance tasks.

The PGCacheWatch CLI tool is designed to facilitate the initial setup process, making it easier to integrate real-time PostgreSQL notifications into your applications. By following the above steps and utilizing the CLI, you can streamline the management of database triggers and functions necessary for effective cache invalidation.
