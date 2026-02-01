<div align="center">

# 🤖 AMFbot Suite

### The Ultimate Open Source AI That Owns the Keys to Your Computer

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com/)

**AMFbot is a sovereign AI assistant that runs entirely on your machine, with full system control, multimedia generation, and infinite extensibility via MCP.**

[Quick Start](#-quick-start) • [Guide d'Installation (FR)](INSTALL_FR.md) • [Features](#-features) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/amfbot/amfbot-suite.git
cd amfbot-suite

# Run the installation script
bash scripts/setup_amf.sh

# Start the wizard
amfbot wizard

# Launch AMFbot
amfbot start
```

**Or with Docker:**

```bash
docker compose up -d
```

---

## ✨ Features

### 🧠 The Mind - Local LLM Engine
- **100% Local & Private**: Powered by Ollama with Llama 3.2, Mistral, and more
- **Zero Data Leakage**: Your conversations never leave your machine
- **Streaming Responses**: Real-time chat with context awareness

### 🎬 The Eyes - Video Generation
- **LTX-Video Integration**: Generate up to 60-second videos from text
- **Image-to-Video**: Animate your images with AI
- **Local or Cloud**: Automatic fallback to APIs if GPU is insufficient

### 🎨 The Artist - Image Generation
- **Flux.1 Models**: Ultra-fast (Schnell) or high-quality (Dev) generation
- **1024x1024+ Resolution**: Professional-grade image output
- **Batch Variations**: Generate multiple versions instantly

### 🔌 The Bridge - MCP Connectivity
- **Auto-Discovery**: Scans your system for potential connections
- **Pre-configured Servers**: Filesystem, Git, Memory, GitHub, Slack, Google Drive
- **Self-Extending**: AMFbot can install new MCP servers on demand
- **Custom Servers**: Create your own tools and AMFbot will learn to use them

### ⚡ The Body - Full System Control
- **Superuser Mode**: Execute privileged commands with user confirmation
- **Audit Logging**: Every action is logged for security
- **Cross-Platform**: macOS, Linux (Windows coming soon)

---

## 🏗️ Architecture

```
AMFbot-Suite/
├── src/                    # Core TypeScript Agent
│   ├── core/              # Agent runtime, root-access, hardware detection
│   ├── cli/               # Command-line interface
│   └── llm/               # Ollama client & model management
│
├── modules/media-gen/      # Python Media Generation (Docker)
│   ├── video/             # LTX-Video wrapper
│   ├── image/             # Flux.1 wrapper
│   └── api/               # FastAPI server
│
├── mcp-hub/               # MCP Server Management
│   ├── scanner.ts         # Auto-discovery
│   ├── installer.ts       # Self-install capability
│   └── servers/           # Pre-configured servers
│
└── scripts/               # Setup & deployment scripts
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Core | TypeScript, Node.js 22+ |
| LLM Engine | Ollama (Llama 3.2, Mistral) |
| Video Gen | LTX-Video, PyTorch |
| Image Gen | Flux.1, Diffusers |
| API Server | FastAPI |
| Containerization | Docker Compose |
| Connectivity | Model Context Protocol (MCP) |

---

## 🖥️ System Requirements

### Minimum
- **CPU**: 4 cores
- **RAM**: 16GB
- **Storage**: 50GB free space
- **OS**: macOS 13+, Ubuntu 22.04+, Debian 12+

### Recommended (for local AI generation)
- **GPU**: NVIDIA RTX 3080+ (12GB VRAM) or Apple M2 Pro+
- **RAM**: 32GB+
- **Storage**: 100GB+ SSD

### Without GPU
AMFbot automatically detects your hardware and falls back to cloud APIs (Replicate, Hugging Face) when local generation isn't possible.

---

## 📋 CLI Commands

```bash
# Core commands
amfbot start              # Start interactive session
amfbot wizard             # Run setup wizard
amfbot doctor             # Diagnose issues

# MCP management
amfbot mcp scan           # Discover available connections
amfbot mcp install <id>   # Install an MCP server
amfbot mcp list           # List installed servers

# Media generation
amfbot media generate-image "prompt"  # Generate an image
amfbot media generate-video "prompt"  # Generate a video
```

---

## 🔐 Security Model

### Superuser Mode
AMFbot can execute privileged commands, but **only with explicit user confirmation**:

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  ROOT ACCESS CONFIRMATION REQUIRED                      │
├─────────────────────────────────────────────────────────────┤
│  Execute: sudo apt-get install nginx                        │
├─────────────────────────────────────────────────────────────┤
│  Type 'yes' to confirm, 'session' for 5-min session,       │
│  or 'no' to cancel.                                         │
└─────────────────────────────────────────────────────────────┘
```

### Audit Logging
All privileged actions are logged to `~/.amfbot/audit.log`:

```json
{"timestamp":"2026-01-28T02:15:00Z","command":"sudo apt-get install nginx","approved":true,"user":"john"}
```

### Network Isolation
Docker containers run in an isolated network. External API access is only enabled when explicitly configured.

---

## 🔧 Configuration

Configuration is stored in `~/.amfbot/config.json`:

```json
{
  "model": "llama3.2",
  "ollamaHost": "http://localhost:11434",
  "mediaGen": {
    "videoBackend": "auto",
    "imageBackend": "auto"
  },
  "mcp": {
    "enabled": true
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AMFBOT_MODELS_DIR` | Directory for AI models | `./models` |
| `AMFBOT_OUTPUT_DIR` | Output directory for generated media | `./outputs` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |

---

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [MCP Server Guide](docs/mcp-servers.md)
- [API Reference](docs/api.md)
- [Security Policy](SECURITY.md)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install dependencies
npm install
cd modules/media-gen && pip install -e ".[dev]"

# Run in development mode
npm run dev

# Run tests
npm test
```

---

## 📜 License

AMFbot Suite is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

**Trademark Notice**: "AMFbot" is a trademark. While the software is open source, use of the name requires approval for commercial purposes. See LICENSE for details.

---

## 🙏 Acknowledgments

AMFbot is built on the shoulders of giants:

- [Moltbot](https://github.com/moltbot/moltbot) - Inspiration for system control architecture
- [LTX-Video](https://github.com/Lightricks/LTX-Video) - Video generation
- [Flux](https://github.com/black-forest-labs/flux) - Image generation
- [Ollama](https://ollama.com/) - Local LLM engine
- [Model Context Protocol](https://github.com/modelcontextprotocol/servers) - MCP servers

---

<div align="center">

**Made with ❤️ by the AMFbot community**

[⭐ Star us on GitHub](https://github.com/amfbot/amfbot-suite)

</div>
