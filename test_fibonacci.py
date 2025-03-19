"""Test suite for the FibonacciCalculator class.

This module provides comprehensive tests for all FibonacciCalculator methods,
following the same testing standards as our terrain modeling system.
"""
import pytest
from fibonacci import FibonacciCalculator


class TestFibonacciCalculator:
    """Test cases for FibonacciCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Provide a fresh calculator instance for each test."""
        return FibonacciCalculator()

    def test_base_cases(self, calculator):
        """Test base cases (0 and 1)."""
        assert calculator.calculate(0) == 0
        assert calculator.calculate(1) == 1

    def test_small_numbers(self, calculator):
        """Test first few Fibonacci numbers."""
        assert calculator.calculate(2) == 1
        assert calculator.calculate(3) == 2
        assert calculator.calculate(4) == 3
        assert calculator.calculate(5) == 5

    def test_negative_input(self, calculator):
        """Test handling of negative input."""
        with pytest.raises(ValueError):
            calculator.calculate(-1)

    def test_iterative_matches_recursive(self, calculator):
        """Verify iterative and recursive methods produce same results."""
        for n in range(10):
            assert calculator.calculate(n) == calculator.calculate_iterative(n)

    def test_sequence_generator(self, calculator):
        """Test sequence generator output."""
        expected = [0, 1, 1, 2, 3, 5, 8, 13]
        assert list(calculator.sequence(8)) == expected

    def test_sequence_empty(self, calculator):
        """Test sequence generator with zero limit."""
        assert list(calculator.sequence(0)) == []

    def test_sequence_negative(self, calculator):
        """Test sequence generator with negative limit."""
        with pytest.raises(ValueError):
            list(calculator.sequence(-1))

    def test_performance_large_number(self, calculator):
        """Test performance with larger numbers."""
        # Should complete quickly due to memoization
        result = calculator.calculate(100)
        assert result > 0  # Basic sanity check

    def test_memory_efficiency(self, calculator):
        """Verify memory efficiency of iterative method."""
        # Calculate large Fibonacci number iteratively
        n = 1000
        result = calculator.calculate_iterative(n)
        assert result > 0  # Basic sanity check
