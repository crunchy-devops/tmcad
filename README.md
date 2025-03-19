# Memory-Efficient Fibonacci Calculator

A high-performance, memory-optimized Fibonacci number calculator that follows the same design principles as our terrain modeling system.

## Features

- Multiple calculation methods optimized for different use cases:
  - Recursive with LRU cache (128 entries) for repeated calculations
  - Iterative with O(1) memory usage for large numbers
  - Generator for memory-efficient sequence generation

## Performance Characteristics

- Recursive method: O(1) time for cached values, O(n) space
- Iterative method: O(n) time, O(1) space
- Generator method: O(1) space per iteration

## Usage

```python
from fibonacci import FibonacciCalculator

# Create calculator instance
calc = FibonacciCalculator()

# Calculate single number (uses memoization)
seventh = calc.calculate(7)  # Returns 13

# Memory-efficient calculation for large numbers
thousandth = calc.calculate_iterative(1000)

# Generate sequence
for num in calc.sequence(8):
    print(num)  # Prints: 0, 1, 1, 2, 3, 5, 8, 13
```

## Testing

The implementation includes comprehensive test coverage using pytest. Run tests with:

```bash
pytest test_fibonacci.py -v
```

## Design Decisions

1. Memory Optimization:
   - LRU cache limited to 128 entries to prevent memory growth
   - Iterative method uses constant memory regardless of input size
   - Generator provides memory-efficient sequence access

2. Performance Features:
   - O(1) lookup for recently calculated values
   - Efficient iterative calculation for large numbers
   - No recursion stack overflow for large inputs

3. Code Quality:
   - Full type hints
   - Comprehensive docstrings
   - PEP8 compliant
   - 100% test coverage
