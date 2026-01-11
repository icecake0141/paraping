# MultiPing

MultiPing is a Python-based tool designed to perform ICMP ping operations to multiple hosts concurrently. This utility is particularly useful for monitoring network connectivity and assessing the availability of multiple servers or devices. The program leverages asynchronous I/O principles to enhance its efficiency and minimize execution times.

## Features
- Concurrent pinging of multiple hosts.
- Asynchronous architecture for faster execution.
- Configurable ping parameters (e.g., timeout, count).
- Simple and intuitive command-line interface.

## Purpose
MultiPing is designed with network administrators and engineers in mind. It provides a fast and efficient way to monitor the connectivity status of multiple devices within a network. Whether you're troubleshooting outages, verifying network configuration, or ensuring uptime, MultiPing can be a valuable addition to your toolkit.

## Getting Started

### Prerequisites
- Python 3.6 or higher is required to run MultiPing.
- Ensure you have administrative or elevated privileges to enable ICMP packets on your system.

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/icecake0141/multiping.git
   ```
2. Navigate to the project directory:
   ```bash
   cd multiping
   ```

### Usage
Run the `main.py` script using Python:
```bash
python main.py [options] <host1> <host2> ...
```

#### Command-line Options
- `-t`, `--timeout`: Specify the timeout in seconds for each ping (default: 1 second).
- `-c`, `--count`: Number of ping attempts per host (default: 4).
- `-v`, `--verbose`: Enable verbose output, showing detailed ping results.

For example, to ping `example.com` and `google.com` with a timeout of 2 seconds:
```bash
python main.py -t 2 example.com google.com
```

## Notes
- MultiPing requires `root` or administrative permissions to send ICMP packets.
- Results may vary based on network conditions and privileges.

## License
This project is licensed under the MIT License. Feel free to use, modify, and distribute it as per your needs.