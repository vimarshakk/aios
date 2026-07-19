# AIOS Plugins Package

The plugins package provides a dynamic plugin system with marketplace, sandboxing, and dependency resolution.

## Features

- **PluginRuntime** - Install, load, and manage plugins
- **PluginMarketplace** - Browse and discover plugins
- **PluginSandbox** - Sandboxed plugin execution
- **DependencyResolver** - Resolve plugin dependencies
- **Version Management** - Semantic versioning support

## Quick Start

```python
from aios.plugins import PluginRuntime

# Create a runtime
runtime = PluginRuntime()

# Install a plugin
await runtime.install("aios-plugin-web-search", version="^1.0.0")

# Use the plugin
plugin = runtime.get_plugin("aios-plugin-web-search")
results = await plugin.search("AIOS documentation")
```

## Plugin Marketplace

```python
from aios.plugins import PluginMarketplace

marketplace = PluginMarketplace()

# Search for plugins
plugins = await marketplace.search("web search")

# Get plugin details
details = await marketplace.get("aios-plugin-web-search")
print(details)
```

## Sandboxed Execution

```python
from aios.plugins import PluginSandbox, SandboxConfig

# Create a sandbox
sandbox = PluginSandbox(
    config=SandboxConfig(
        max_memory="1GB",
        max_cpu=0.5,
        allowed_network=False,
    )
)

# Execute plugin in sandbox
result = await sandbox.execute(plugin, "search", query="test")
```

## Documentation

See the main [README](../../README.md) for more information.
