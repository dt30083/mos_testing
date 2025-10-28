# Docker Deployment Guide

## Quick Start

### Server Only
```bash
# Start the VoIP probe server
docker-compose up server
```

### Full Testing Setup
```bash
# Start both server and client for internal testing
docker-compose --profile testing up
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Server Variables:**
- `VOIP_SERVER_PORT` - Host port to bind (default: 5005)

**Client Variables:**
- `VOIP_HOST` - Target server IP/hostname
- `VOIP_PORT` - Target server port (default: 5005)
- `VOIP_PPS` - Packets per second (default: 50)
- `VOIP_CODEC` - Codec profile: g711, g729, opus (default: g711)
- `VOIP_DURATION` - Test duration in seconds (0 = unlimited)

## Usage Examples

### 1. Server Deployment
```bash
# Production server deployment
docker-compose up -d server

# Custom port binding
VOIP_SERVER_PORT=6000 docker-compose up -d server
```

### 2. Client Testing

**Against Docker Server:**
```bash
# Internal testing (server + client)
docker-compose --profile testing up
```

**Against External Server:**
```bash
# Build client image
docker-compose build client

# Run against external server
docker run --rm \
  -e VOIP_HOST=192.168.1.100 \
  -e VOIP_DURATION=120 \
  -v $(pwd)/results:/app/results \
  voip-probe-client --csv /app/results/test.csv
```

### 3. Advanced Scenarios

**High-Rate Testing:**
```bash
docker run --rm \
  -e VOIP_HOST=10.1.1.1 \
  -e VOIP_PPS=100 \
  -e VOIP_CODEC=g729 \
  -e VOIP_DURATION=300 \
  -v $(pwd)/results:/app/results \
  voip-probe-client --csv /app/results/stress-test.csv
```

**Continuous Monitoring:**
```bash
docker run -d --name voip-monitor \
  -e VOIP_HOST=vpn.company.com \
  -e VOIP_PPS=20 \
  -v $(pwd)/results:/app/results \
  voip-probe-client --csv /app/results/monitor.csv
```

## Health Checks

The server includes health checks that verify UDP connectivity:

```bash
# Check server health
docker-compose ps
docker inspect voip-probe-server --format='{{.State.Health.Status}}'
```

## Networking

### Firewall Requirements
- **Server**: UDP inbound on configured port (default 5005)
- **Client**: UDP outbound to server port

### Docker Networks
The compose file creates an isolated `voip-test` network for internal testing.

### Host Networking
For production deployments, consider host networking for better performance:

```yaml
services:
  server:
    network_mode: host
    # Remove ports section when using host networking
```

## Troubleshooting

### Common Issues

**Server not responding:**
```bash
# Check server logs
docker-compose logs server

# Test UDP connectivity
docker exec voip-probe-server netstat -ulnp
```

**Client connection failures:**
```bash
# Check client logs
docker-compose logs client

# Verify network connectivity
docker run --rm --network voip-test alpine ping server
```

**Permission issues with results:**
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./results
```

### Performance Tuning

**For high packet rates (>100 pps):**
- Use host networking mode
- Increase container memory limits
- Consider dedicated network interfaces

**For production monitoring:**
- Use restart policies
- Implement log rotation
- Monitor container resource usage

## Security Considerations

- Containers run as non-root user
- No sensitive data in environment variables
- Isolated Docker network for testing
- Health checks prevent zombie containers

## Building Custom Images

```bash
# Build specific service
docker-compose build server
docker-compose build client

# Build with custom tags
docker build -f dockerfile.server -t my-voip-server .
docker build -f dockerfile.client -t my-voip-client .
```