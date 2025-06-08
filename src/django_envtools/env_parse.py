# Define a visitor class to find Env class usage
import ast
from typing import Any


class EnvVisitor(ast.NodeVisitor):
    def __init__(self):  # noqa: D107
        self.env_calls: dict[str, dict[str, Any]] = {}
        self.env_var_names: list[str] = []
        self.variable_assignments: dict[str, Any] = {}

    def visit_Assign(self, node):
        # Look for assignments like 'env = Env()'
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Env"
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            self.env_var_names.append(node.targets[0].id)

        # Track variable assignments for complex cases
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

            # Track assignments of env method calls (e.g., email = env.dj_email_url(...))
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id in self.env_var_names
            ):
                # Process the env method call and store the variable name
                self._process_env_call(node.value)
                self.variable_assignments[var_name] = {
                    "type": "env_method_call",
                    "method": node.value.func.attr,
                    "args": [self._get_string_value(arg) for arg in node.value.args if self._get_string_value(arg)],
                }

        self.generic_visit(node)

    def visit_Call(self, node):
        # Look for calls like 'env("VAR_NAME")' or 'env.str("VAR_NAME")'
        if self._is_env_call(node) or self._is_env_method_call(node):
            self._process_env_call(node)
        self.generic_visit(node)

    def _is_env_call(self, node):
        # Check if this is a direct call to an Env instance (e.g., env("VAR_NAME"))
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.env_var_names
            and len(node.args) > 0
            and self._get_string_value(node.args[0]) is not None
        )

    def _is_env_method_call(self, node):
        # Check if this is a method call on an Env instance (e.g., env.str("VAR_NAME"))
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.env_var_names
            and len(node.args) > 0
            and self._get_string_value(node.args[0]) is not None
        )

    def _get_string_value(self, node):
        """Extract string value from a node, handling different node types."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        # For Python < 3.8 compatibility
        elif hasattr(ast, "Str") and isinstance(node, ast.Str):
            return node.s
        # Handle string concatenation
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._get_string_value(node.left)
            right = self._get_string_value(node.right)
            if left is not None and right is not None:
                return left + right
        # Handle JoinedStr (f-strings)
        elif isinstance(node, ast.JoinedStr):
            # Try to extract the format string, but this is a simplification
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    parts.append(str(value.value))
                elif hasattr(ast, "Str") and isinstance(value, ast.Str):
                    parts.append(value.s)
            if parts:
                return "".join(parts)
        # Handle Attribute access (e.g., module.function)
        elif isinstance(node, ast.Attribute):
            value = self._get_attribute_name(node)
            if value:
                return value
        return None

    def _get_attribute_name(self, node):
        """Get the full dotted name of an attribute (e.g., 'django.core.management.utils.get_random_secret_key')."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_attribute_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None

    def _process_env_call(self, node):
        # Extract variable name
        var_name = self._get_string_value(node.args[0])
        if not var_name:
            return  # Skip if we couldn't extract a valid variable name

        # Determine variable type
        var_type = "str"  # Default type
        if isinstance(node.func, ast.Attribute):
            var_type = node.func.attr

        # Extract keyword arguments
        kwargs = {"default": None}  # Initialize default to None

        for kw in node.keywords:
            if kw.arg == "default":
                if isinstance(kw.value, ast.Constant):
                    kwargs["default"] = kw.value.value
                # Handle list literals (e.g., default=[])
                elif isinstance(kw.value, ast.List):
                    # Convert ast.List to Python list
                    kwargs["default"] = []
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant):
                            kwargs["default"].append(elt.value)
                # Handle older Python versions
                elif hasattr(ast, "Num") and isinstance(kw.value, ast.Num):
                    kwargs["default"] = kw.value.n
                elif hasattr(ast, "NameConstant") and isinstance(kw.value, ast.NameConstant):
                    kwargs["default"] = kw.value.value
            elif kw.arg == "help_text":
                kwargs["help_text"] = self._get_string_value(kw.value)
            elif kw.arg == "initial":
                if isinstance(kw.value, ast.Constant):
                    kwargs["initial"] = kw.value.value
                # Try to get string value for string expressions
                else:
                    initial_str = self._get_string_value(kw.value)
                    if initial_str:
                        kwargs["initial"] = initial_str
            elif kw.arg == "initial_func":
                # For initial_func, we're primarily interested in string values
                kwargs["initial_func"] = self._get_string_value(kw.value)
            else:
                # Store any other keyword arguments
                if isinstance(kw.value, ast.Constant):
                    kwargs[kw.arg] = kw.value.value
                else:
                    str_value = self._get_string_value(kw.value)
                    if str_value is not None:
                        kwargs[kw.arg] = str_value

        # Store in env_calls dictionary with variable name as key
        self.env_calls[var_name] = {"type": var_type, **kwargs}


def get_env_calls(env_content: str) -> dict[str, dict[str, Any]]:
    tree = ast.parse(env_content)
    visitor = EnvVisitor()
    visitor.visit(tree)
    return visitor.env_calls
