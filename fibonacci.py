"""Memory-efficient Fibonacci number calculator.

This module provides a Fibonacci calculator implementation optimized for memory usage
and performance, using techniques similar to our terrain modeling system.
"""
from functools import lru_cache
from typing import Dict, Generator


class FibonacciCalculator:
    """A memory-efficient Fibonacci number calculator.

    This class provides multiple methods for calculating Fibonacci numbers,
    optimized for different use cases:
    - Recursive with memoization for one-off calculations
    - Iterative for memory-constrained environments
    - Generator for sequential access
    """

    def __init__(self):
        """Initialize the calculator with an empty cache."""
        self._cache: Dict[int, int] = {}

    @lru_cache(maxsize=128)
    def calculate(self, n: int) -> int:
        """Calculate the nth Fibonacci number using recursion with memoization.

        Args:
            n: The position in the Fibonacci sequence (0-based)

        Returns:
            The nth Fibonacci number

        Raises:
            ValueError: If n is negative
        """
        if n < 0:
            raise ValueError("Position must be non-negative")
        if n <= 1:
            return n
        return self.calculate(n - 1) + self.calculate(n - 2)

    def calculate_iterative(self, n: int) -> int:
        """Calculate the nth Fibonacci number iteratively.

        This method uses O(1) memory regardless of input size.

        Args:
            n: The position in the Fibonacci sequence (0-based)

        Returns:
            The nth Fibonacci number

        Raises:
            ValueError: If n is negative
        """
        if n < 0:
            raise ValueError("Position must be non-negative")
        if n <= 1:
            return n

        prev, curr = 0, 1
        for _ in range(2, n + 1):
            prev, curr = curr, prev + curr
        return curr

    def sequence(self, limit: int) -> Generator[int, None, None]:
        """Generate Fibonacci numbers up to the specified limit.

        Args:
            limit: The number of Fibonacci numbers to generate

        Yields:
            Sequential Fibonacci numbers

        Raises:
            ValueError: If limit is negative
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")

        a, b = 0, 1
        for _ in range(limit):
            yield a
            a, b = b, a + b
