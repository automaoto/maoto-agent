<h1 align="center">Maoto Agent API Python Package 🚀</h1>

<p align="center">
  <a href="https://docs.maoto.world">
    <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/MAOTO_logo.png" alt="MAOTO framework">
  </a>
</p>
<p align="center">
  <em>MAOTO framework, high performance, easy to learn, fast to code, ready for production</em>
</p>
<p align="center">
  <a href="https://github.com/automaoto/maoto-agent/actions?query=workflow%3ATest+event%3Apush+branch%3Amain" target="_blank">
    <img src="https://github.com/automaoto/maoto-agent/actions/workflows/test.yml/badge.svg?event=push&branch=main" alt="Test">
  </a>
  <a href="https://github.com/automaoto/maoto-agent" target="_blank">
    <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/coverage.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/maoto-agent" target="_blank">
    <img src="https://img.shields.io/pypi/v/maoto-agent?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://anaconda.org/conda-forge/maoto-agent" target="_blank">
    <img src="https://img.shields.io/conda/vn/conda-forge/maoto-agent.svg" alt="Conda-Forge">
  </a>
  <a href="https://pypi.org/project/maoto-agent" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/maoto-agent.svg?color=%2334D058" alt="Supported Python versions">
  </a>
  <a href="https://docs.maoto.world" target="_blank">
    <img src="https://img.shields.io/badge/docs-docs.maoto.world-blue" alt="Documentation">
  </a>
  <a href="https://www.gnu.org/licenses/lgpl-3.0" target="_blank">
    <img src="https://img.shields.io/badge/License-LGPL%20v3-blue.svg" alt="License: LGPL v3">
  </a>
  <a href="https://github.com/automaoto/maoto-agent/blob/main/SECURITY.md" target="_blank">
    <img src="https://img.shields.io/badge/Security-Policy-blue" alt="Security Policy">
  </a>
</p>

The package provides convenient access to the [MAOTO](https://maoto.world) agents ecosystem from Python applications. The library includes type definitions for all request params and response fields and offers to easily create asynchronous agents that communicate with the [MAOTO](https://maoto.world) API.

## Key Features ✅ 

- 🚀 **FastAPI Integration:** Built directly on FastAPI to streamline web service creation and endpoint management.
- 💻 **Optional MCP Support:** Easily add MCP support to your application by installing the `maoto-agent[mcp]` package.
- 🔄 **Async Operations:** Fully supports asynchronous requests with httpx for non-blocking I/O.
- 🔒 **Secure Communication:** Leverages API keys and Pydantic for robust type safety and secure data validation.
- 🛠️ **Flexible Handler Registration:** Easy-to-use decorator for registering custom event handlers.
- ⚙️ **Extensible Configuration:** Utilizes Pydantic-based settings for flexible and environment-aware customization.
- 🌐 **Marketplace & Assistant Connectivity:** Seamlessly interacts with external services via dedicated endpoints.

## Installation 📦

### From PyPI (pip)
```bash
pip install maoto-agent
```

### With MCP Support
```bash
pip install "maoto-agent[mcp]"
```

### Using MCP Inspector
After installing with MCP support, you can use the MCP inspector to view and test your MCP tools:

1. Start your FastAPI application with MCP enabled:
```python
from maoto_agent.maoto_agent import Maoto
from maoto_agent.mcp import MCPServer
from pydantic import SecretStr

# Create the FastAPI app with required API key
app = Maoto(apikey=SecretStr("your-api-key-here"))  # Replace with your actual API key
mcp = MCPServer(app)
```

2. Run your application using the correct module path and class name:
```bash
# Set the API key as an environment variable, the below is just an example
export MAOTO_APIKEY="your-api-key-here"
uvicorn src.maoto_agent.maoto_agent:Maoto --reload
```

3. Open the MCP inspector in your browser:
```bash
# use the correct path based on the app created
npx @modelcontextprotocol/inspector python -m src.maoto_agent.mcp.server
```

This will open a web interface where you can:
- View all available MCP tools
- Test tools with different parameters
- View tool documentation and schemas
- Monitor tool execution

### Using conda (conda-forge)
```bash
conda install -c conda-forge maoto-agent
```
## Quick Start & Docs 👨🏼‍💻

- [🚀 Quick Start](https://docs.maoto.world/quickstart)
- [📑 Documentation](https://docs.maoto.world)
- [📋 Release Notes](https://github.com/automaoto/maoto-agent/releases)

## Support & Community 👥

- [⚠️ GitHub Issues](https://github.com/automaoto/maoto-agent/issues)
- [💬 GitHub Discussions](https://github.com/automaoto/maoto-agent/discussions)
- [🗞️ Subscribe](https://www.maoto.world/subscribe)
- [👨🏼‍💻 Discord](https://discord.gg/hNuqjnGjNw)

## Partners & Supporters 🌟

<a href="https://www.ntu.edu.sg/" target="_blank" title="NTU Singapore">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/ntu_singapore.jpg">
</a>
<a href="https://www.ntuitive.sg/" target="_blank" title="NTUitive">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/ntuitive.jpg">
</a>
<a href="https://pollinate.edu.sg/" target="_blank" title="Pollinate">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/pollinate.png">
</a>
<a href="https://www.salesforce.com/" target="_blank" title="Salesforce">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/Salesforce-Logo.png">
</a>
<a href="https://ace.sg/" target="_blank" title="ACE SG">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/ace-logo.jpg">
</a>
<a href="https://www.nusentre.com/" target="_blank" title="NUS Enterprise">
  <img src="https://raw.githubusercontent.com/automaoto/maoto-agent/main/assets/partners_and_supporters/nes_society.png">
</a>

[Others](https://maoto.world)

## License 📝

This project is licensed under the GNU Lesser General Public License - see the [LICENSE](https://github.com/automaoto/maoto-agent/blob/main/LICENSE) file for details.

## Credits ✨

Developed by [MAOTO PTE. LTD.](https://maoto.world) - We create innovative AI-powered solutions for business.