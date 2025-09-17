"""
Mathematical reasoning and computation using SymPy.

This module provides a comprehensive mathematical solver that can handle
algebraic operations, calculus, statistics, matrix operations, and more.
"""

import re
from typing import Optional

# SymPy will be imported locally in methods that need it


class MathSolver:
    """Handles mathematical computations and symbolic reasoning using SymPy."""

    def __init__(self) -> None:
        """Initialize the math solver."""
        self._check_sympy_availability()

    def _check_sympy_availability(self) -> None:
        """Check if SymPy is available and raise an error if not."""
        try:
            import sympy as sp  # noqa: F401
        except ImportError:
            raise ImportError(
                "SymPy is required for mathematical operations. "
                "Please install it with: pip install sympy>=1.12"
            )

    def solve_math(self, expression: str, operation: Optional[str] = None) -> str:
        """
        Perform mathematical calculations and symbolic reasoning using SymPy.

        Args:
            expression: The mathematical expression to evaluate or manipulate
            operation: Optional operation type (auto-detected if not specified)

        Returns:
            The result of the mathematical operation as a string
        """
        try:
            # Clean and normalize the expression
            expr_str = expression.strip()
            expr_str = self._normalize_expression(expr_str)

            # Auto-detect operation if not specified
            if not operation:
                operation = self._detect_operation(expr_str)

            # Route to appropriate handler
            return self._handle_operation(expr_str, operation)

        except Exception as e:
            return f"Mathematical error: {e!s}"

    def _normalize_expression(self, expr_str: str) -> str:
        """Normalize mathematical notation in the expression."""
        # Handle common mathematical notation conversions
        expr_str = expr_str.replace("^", "**")  # Convert ^ to ** for exponentiation
        expr_str = expr_str.replace("x", "*")  # Convert x to *
        expr_str = expr_str.replace("÷", "/")  # Convert ÷ to /
        return expr_str

    def _detect_operation(self, expr_str: str) -> str:
        """Auto-detect the type of mathematical operation needed."""
        # Check for JavaScript Date functions first
        if any(
            func in expr_str
            for func in ["Date.UTC", "Date.parse", "Date.now", "new Date"]
        ):
            return "date_error"
        elif "=" in expr_str and (
            "x" in expr_str or "y" in expr_str or "z" in expr_str
        ):
            return "solve"
        elif any(
            word in expr_str.lower() for word in ["derivative", "differentiate", "d/dx"]
        ):
            return "differentiate"
        elif any(word in expr_str.lower() for word in ["integral", "integrate", "∫"]):
            return "integrate"
        elif any(word in expr_str.lower() for word in ["limit", "lim"]):
            return "limit"
        elif "[" in expr_str and "]" in expr_str:
            return "matrix"
        elif any(
            word in expr_str.lower()
            for word in ["mean", "average", "std", "variance", "normal", "distribution"]
        ):
            return "stats"
        else:
            return "evaluate"

    def _handle_operation(self, expr_str: str, operation: str) -> str:
        """Route the expression to the appropriate operation handler."""
        handlers = {
            "date_error": self._handle_date_error,
            "solve": self._handle_solve,
            "differentiate": self._handle_differentiate,
            "integrate": self._handle_integrate,
            "limit": self._handle_limit,
            "matrix": self._handle_matrix,
            "stats": self._handle_stats,
            "simplify": self._handle_simplify,
            "evaluate": self._handle_evaluate,
        }

        handler = handlers.get(operation, self._handle_evaluate)
        if operation not in handlers:
            return f"Unsupported operation: '{operation}'. Available operations: {', '.join(handlers.keys())}"
        return handler(expr_str)

    def _handle_solve(self, expr_str: str) -> str:
        """Handle equation solving."""
        import sympy as sp
        from sympy import solve

        # Extract equation parts
        if "=" in expr_str:
            left, right = expr_str.split("=", 1)
            left = left.strip()
            right = right.strip()
            # Create equation: left - right = 0
            equation = sp.sympify(left) - sp.sympify(right)
        else:
            equation = sp.sympify(expr_str)

        # Find variables
        variables = list(equation.free_symbols)
        if not variables:
            return "No variables found in equation"

        # Solve the equation
        solutions = solve(equation, variables)

        if isinstance(solutions, list):
            if len(solutions) == 0:
                return "No solutions found"
            elif len(solutions) == 1:
                return f"Solution: {variables[0]} = {solutions[0]}"
            else:
                result = f"Solutions for {variables[0]}:\n"
                for i, sol in enumerate(solutions):
                    result += f"  {i + 1}. {variables[0]} = {sol}\n"
                return result.strip()
        else:
            return f"Solution: {variables[0]} = {solutions}"

    def _handle_differentiate(self, expr_str: str) -> str:
        """Handle differentiation."""
        import sympy as sp
        from sympy import diff

        # Extract variable and expression
        if "derivative of" in expr_str.lower():
            expr_part = expr_str.lower().replace("derivative of", "").strip()
        elif "d/dx" in expr_str.lower():
            expr_part = expr_str.lower().replace("d/dx", "").strip()
        else:
            expr_part = expr_str

        expr = sp.sympify(expr_part)
        # Find the variable to differentiate with respect to
        variables = list(expr.free_symbols)
        if not variables:
            return "No variables found for differentiation"

        var = variables[0]  # Use first variable found
        derivative = diff(expr, var)
        return f"d/d{var} ({expr}) = {derivative}"

    def _handle_integrate(self, expr_str: str) -> str:
        """Handle integration."""
        import sympy as sp
        from sympy import integrate

        # Extract expression and limits
        if "integral of" in expr_str.lower():
            expr_part = expr_str.lower().replace("integral of", "").strip()
        else:
            expr_part = expr_str

        expr = sp.sympify(expr_part)
        variables = list(expr.free_symbols)
        if not variables:
            return "No variables found for integration"

        var = variables[0]
        integral = integrate(expr, var)
        return f"∫ {expr} d{var} = {integral}"

    def _handle_limit(self, expr_str: str) -> str:
        """Handle limit calculations."""
        import sympy as sp
        from sympy import limit, symbols

        # Parse limit expression
        if "limit of" in expr_str.lower():
            expr_part = expr_str.lower().replace("limit of", "").strip()
        else:
            expr_part = expr_str

        # Look for "as x approaches" pattern
        match = re.search(r"as\s+(\w+)\s+approaches\s+([^,]+)", expr_part)
        if match:
            var_name = match.group(1)
            limit_point = match.group(2).strip()
            expr_part = expr_part[: match.start()].strip()
        else:
            # Default to x approaching 0
            var_name = "x"
            limit_point = "0"

        expr = sp.sympify(expr_part)
        var = symbols(var_name)
        limit_result = limit(expr, var, sp.sympify(limit_point))
        return f"lim({expr}) as {var} → {limit_point} = {limit_result}"

    def _handle_matrix(self, expr_str: str) -> str:
        """Handle matrix operations."""
        import sympy as sp
        from sympy import Matrix

        # Handle matrix operations
        if "inverse of" in expr_str.lower():
            matrix_str = expr_str.lower().replace("inverse of", "").strip()
        else:
            matrix_str = expr_str

        # Parse matrix from string like "[[1,2],[3,4]]"
        matrix_str = matrix_str.strip()
        if matrix_str.startswith("[[") and matrix_str.endswith("]]"):
            matrix_str = matrix_str[2:-2]  # Remove outer [[ and ]]
        elif matrix_str.startswith("[") and matrix_str.endswith("]"):
            matrix_str = matrix_str[1:-1]  # Remove outer [ and ]
        else:
            return "Invalid matrix format. Use format like [[1,2],[3,4]]"

        # Split by ],[ to get individual rows
        rows = matrix_str.split("],[")

        if not rows:
            return "Invalid matrix format. Use format like [[1,2],[3,4]]"

        matrix_data = []
        for row in rows:
            # Split by comma and convert to numbers
            elements = [sp.sympify(x.strip()) for x in row.split(",")]
            matrix_data.append(elements)

        M = Matrix(matrix_data)
        try:
            inverse = M.inv()
            return f"Inverse of {M} = {inverse}"
        except Exception as e:
            return f"Matrix is not invertible: {e!s}"

    def _handle_stats(self, expr_str: str) -> str:
        """Handle statistical operations."""
        if "mean of" in expr_str.lower():
            data_str = expr_str.lower().replace("mean of", "").strip()
            # Parse list like [1,2,3,4,5]
            data_str = data_str.replace("[", "").replace("]", "")
            data = [float(x.strip()) for x in data_str.split(",")]
            mean_val = sum(data) / len(data)
            return f"Mean of {data} = {mean_val}"
        elif "normal distribution" in expr_str.lower():
            # Handle normal distribution queries
            return "Normal distribution: Use P(X > value) for probability calculations"
        elif expr_str.startswith("[") and expr_str.endswith("]"):
            # Auto-detect mean calculation for list format
            data_str = expr_str.replace("[", "").replace("]", "")
            data = [float(x.strip()) for x in data_str.split(",")]
            mean_val = sum(data) / len(data)
            return f"Mean of {data} = {mean_val}"
        else:
            return "Statistical operation not recognized"

    def _handle_simplify(self, expr_str: str) -> str:
        """Simplify expression."""
        import sympy as sp
        from sympy import simplify

        expr = sp.sympify(expr_str)
        simplified = simplify(expr)
        return f"Simplified: {simplified}"

    def _handle_evaluate(self, expr_str: str) -> str:
        """Evaluate the expression."""
        import sympy as sp

        expr = sp.sympify(expr_str)

        # If expression has variables, return symbolic form
        if expr.free_symbols:
            return f"Expression: {expr}"
        else:
            # Evaluate numerically
            result = float(expr.evalf())
            return f"Result: {result}"

    def _handle_date_error(self, expr_str: str) -> str:
        """Handle JavaScript Date function errors."""
        return (
            "ERROR: JavaScript Date functions (Date.UTC, Date.parse, etc.) are not supported in mathematical expressions. "
            "For date calculations and parsing, use the parse_date() function instead. "
            "The math solver is designed for mathematical operations using SymPy, not JavaScript date functions."
        )
