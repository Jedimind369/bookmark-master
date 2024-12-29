# Test Development Journey

## Current Challenges

### 1. Bottleneck Mock Implementation (In Progress)
- **Started**: January 2024
- **Status**: Attempting solution #5
- **Debug Log**: [debug_log.bottleneck_mock.md](./debug_log.bottleneck_mock.md)
- **Key Files**:
  - `setup.ts`: Test setup and mock implementations
  - `zyte-service.test.ts`: Service tests using the mock

## Debug Logs
We maintain debug logs to track our problem-solving journey. Each log captures:
- What we tried
- Why it failed
- What we learned
- Next steps

### Current Logs
- `debug_log.bottleneck_mock.md`: Tracking our attempts to properly mock the Bottleneck rate limiter

## Directory Structure
```
server/tests/
├── README.md                # This file - our journey log
├── setup.ts                 # Test setup and mocks
├── zyte-service.test.ts     # Service tests
└── debug_log.*.md          # Debug logs for specific issues
```

---
This documentation will grow as we encounter and solve more challenges. 