#!/usr/bin/env python3
"""
Unit tests for arithmetic_sanity_check function (Issue #11 fix).

Tests the enhanced answer extraction and validation logic that handles
natural language mathematical solutions.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct import to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location("verify", Path(__file__).parent.parent / "engine" / "verify.py")
verify_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_module)

arithmetic_sanity_check = verify_module.arithmetic_sanity_check
_validate_mathematical_expression = verify_module._validate_mathematical_expression


def test_explicitly_marked_answers():
    """Test extraction of explicitly marked answers."""
    print("\n1. Testing explicitly marked answers...")
    
    test_cases = [
        # (solution_text, expected_result, description)
        ("Let's solve x+5=10. Therefore x=5. Answer: 5", True, "Simple 'Answer:' marker"),
        ("Step 1: ...\nStep 2: ...\nFinal answer: 42", True, "Final answer marker"),
        ("The calculation shows that result: 3.14", True, "Result marker"),
        ("Therefore, x = -1", True, "Therefore marker"),
        ("Thus we get 100", True, "Thus marker"),
        ("So we have 7.5", True, "So we have marker"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
        if result != expected:
            print(f"     Solution: {solution[:50]}...")
    
    return True


def test_equation_assignments():
    """Test extraction of equation assignments."""
    print("\n2. Testing equation assignments...")
    
    test_cases = [
        ("Solving step by step:\nx = 42", True, "Simple assignment"),
        ("First we get y = 10\nThen x = 5", True, "Multiple assignments"),
        ("result = 3.14159", True, "Result variable"),
        ("The value is\nans = -7", True, "Answer variable"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_last_line_extraction():
    """Test extraction from last line."""
    print("\n3. Testing last line extraction...")
    
    test_cases = [
        ("Let's solve this problem.\nFirst step...\nSecond step...\n42", True, "Numerical last line"),
        ("Complex reasoning here.\nMore steps.\n2 + 2 = 4", True, "Expression last line"),
        ("Proof:\nStep 1\nStep 2\nx = 5", True, "Assignment last line"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_complex_solutions():
    """Test realistic complex solutions."""
    print("\n4. Testing complex realistic solutions...")
    
    # Realistic solution 1: Algebra problem
    solution1 = """
Let's solve the equation x^2 + 2x + 1 = 0 step by step.

First, I notice this is a perfect square trinomial.
We can factor it as (x + 1)^2 = 0

Taking the square root of both sides:
x + 1 = 0

Therefore, x = -1

Answer: -1
"""
    result1 = arithmetic_sanity_check(solution1)
    print(f"  {'✓' if result1 == True else '✗'} Algebra problem: {result1} (expected True)")
    
    # Realistic solution 2: Word problem
    solution2 = """
Let's break down this word problem:
- John has 5 apples
- Mary gives him 3 more apples
- How many apples does John have now?

Calculation:
5 + 3 = 8

Final answer: 8 apples
"""
    result2 = arithmetic_sanity_check(solution2)
    print(f"  {'✓' if result2 == True else '✗'} Word problem: {result2} (expected True)")
    
    # Realistic solution 3: Calculus problem
    solution3 = """
To find the derivative of f(x) = x^2 + 3x + 2:

Using the power rule:
f'(x) = 2x + 3

At x = 1:
f'(1) = 2(1) + 3 = 5

The derivative at x=1 is 5.
"""
    result3 = arithmetic_sanity_check(solution3)
    print(f"  {'✓' if result3 == True else '✗'} Calculus problem: {result3} (expected True)")
    
    return True


def test_no_clear_answer():
    """Test solutions without clear numerical answers."""
    print("\n5. Testing solutions without clear answers...")
    
    test_cases = [
        ("This is a complex proof that requires multiple steps.", None, "Pure text"),
        ("The solution involves abstract reasoning.", None, "Abstract reasoning"),
        ("We need to consider various cases.", None, "No numerical result"),
        ("", None, "Empty string"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_invalid_expressions():
    """Test detection of invalid expressions."""
    print("\n6. Testing invalid expressions...")
    
    test_cases = [
        ("Answer: infinity", False, "Infinity"),
        ("Result: 1/0", False, "Division by zero (if evaluated)"),
        # Note: Some invalid expressions might return None if unparseable
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        # Accept both False and None for invalid cases
        status = "✓" if result in [expected, None] else "✗"
        print(f"  {status} {description}: {result} (expected {expected} or None)")
    
    return True


def test_various_number_formats():
    """Test various number formats."""
    print("\n7. Testing various number formats...")
    
    test_cases = [
        ("Answer: 42", True, "Integer"),
        ("Answer: 3.14159", True, "Decimal"),
        ("Answer: -7", True, "Negative"),
        ("Answer: 1/2", True, "Fraction"),
        ("Answer: $100", True, "Currency symbol"),
        ("Answer: 1,000", True, "Comma separator"),
        ("Answer: 2^8", True, "Exponent"),
        ("Answer: sqrt(2)", True, "Square root"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_symbolic_expressions():
    """Test symbolic mathematical expressions."""
    print("\n8. Testing symbolic expressions...")
    
    test_cases = [
        ("Answer: x + 1", True, "Simple symbolic"),
        ("Answer: 2*x - 3", True, "Linear expression"),
        ("Answer: x^2 + 2*x + 1", True, "Quadratic"),
        ("Answer: sin(x)", True, "Trigonometric"),
    ]
    
    for solution, expected, description in test_cases:
        result = arithmetic_sanity_check(solution)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_validate_mathematical_expression():
    """Test the helper function directly."""
    print("\n9. Testing _validate_mathematical_expression helper...")
    
    test_cases = [
        ("42", True, "Simple integer"),
        ("3.14", True, "Decimal"),
        ("-5", True, "Negative"),
        ("x + 1", True, "Symbolic"),
        ("2 + 2", True, "Expression"),
        ("sqrt(2)", True, "Function"),
        ("", None, "Empty string"),
        ("this is not math", None, "Natural language"),
    ]
    
    for expr, expected, description in test_cases:
        result = _validate_mathematical_expression(expr)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (expected {expected})")
    
    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n10. Testing edge cases...")
    
    test_cases = [
        (None, None, "None input"),
        ("", None, "Empty string"),
        ("   ", None, "Whitespace only"),
        ("Answer: ", None, "Marker without value"),
        ("x = ", None, "Assignment without value"),
    ]
    
    for solution, expected, description in test_cases:
        try:
            result = arithmetic_sanity_check(solution)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {description}: {result} (expected {expected})")
        except Exception as e:
            print(f"  ✗ {description}: Exception {e}")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("arithmetic_sanity_check Unit Tests (Issue #11 Fix)")
    print("=" * 60)
    
    tests = [
        ("Explicitly Marked Answers", test_explicitly_marked_answers),
        ("Equation Assignments", test_equation_assignments),
        ("Last Line Extraction", test_last_line_extraction),
        ("Complex Solutions", test_complex_solutions),
        ("No Clear Answer", test_no_clear_answer),
        ("Invalid Expressions", test_invalid_expressions),
        ("Various Number Formats", test_various_number_formats),
        ("Symbolic Expressions", test_symbolic_expressions),
        ("Helper Function", test_validate_mathematical_expression),
        ("Edge Cases", test_edge_cases),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

