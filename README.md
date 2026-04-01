# NetReach-LAN-Management-Tool
Full-featured LAN management app built in Python with custom GUI and audio feedback. Supports SSH network discovery, Wake-on-LAN, remote shutdown, AnyDesk auto-ID retrieval, one-click access, LAN chat, RDP, and multi-threaded scanning with OS and port detection. Cross-platform with no dependencies.

LAN Manager – Python Network Control Tool
Overview

LAN Manager is a full-featured desktop application built in Python for managing and controlling local networks. It provides automation, remote access, and real-time communication through a custom GUI with audio feedback.

Features
SSH-based network discovery
Wake-on-LAN (remote power on)
Remote shutdown via SSH
AnyDesk ID auto-retrieval with one-click connection
LAN chat and messaging system
Multi-threaded host scanning (OS and open ports detection)
RDP (Remote Desktop Protocol) integration
Persistent device database
Synthesized audio feedback
Cross-platform (Windows, Linux, macOS)
Zero external dependencies
Installation
Install Python 3.10+
Clone the repository:
cd lan-manager
Run the application:
python main.py
Usage
Launch the application
Scan the network
Select a device
Execute actions (Wake, Shutdown, Connect, Chat)
Requirements
Python 3.10+
SSH enabled on target devices
Devices must be on the same LAN
Security Notes
Uses SSH for secure communication
Store credentials securely
Do not expose the application outside trusted networks
Future Improvements
Web dashboard
Mobile companion application
Plugin system
Advanced monitoring and alerts
License

MIT License
