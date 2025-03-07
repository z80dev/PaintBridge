# PaintBridge Development Guide

## Build & Test Commands
- `forge build` - Build Solidity contracts
- `forge test` - Run all Solidity tests
- `forge test --match-contract SCCNFTBridgeTest` - Run specific test contract
- `forge test --match-test testBridge` - Run specific test function
- `forge fmt` - Format Solidity code
- `python -m pytest tests/` - Run Python tests
- `make deploy_bridge` - Run deployment script

## Code Style Guidelines
- **Python**: Use snake_case for variables/functions, PascalCase for classes
- **Imports**: Standard library first, third-party next, relative imports last
- **Solidity**: Follow Forge conventions with setUp() for test initialization
- **Error Handling**: Use specific exception types in try/except blocks
- **Types**: Use type hints in Python, explicit types in Solidity
- **Docstrings**: Use Google style format with parameter/return descriptions
- **Logging**: Include context (file, line) and appropriate log levels

## Testing Patterns
- Name test files with `test_*.py` or `*.t.sol` convention
- Use descriptive test function names that explain what's being tested
- In Solidity tests, use forge's built-in assertions
- Python tests should use pytest fixtures for test setup