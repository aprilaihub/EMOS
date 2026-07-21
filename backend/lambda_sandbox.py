"""Restricted subprocess execution for node-editor lambda transformations."""

from __future__ import annotations

import ast
import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


MAX_CODE_BYTES = 16 * 1024
MAX_OUTPUT_BYTES = 5 * 1024 * 1024
WALL_TIMEOUT_SECONDS = 5

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

SAFE_METHODS = {
    "append",
    "clear",
    "copy",
    "count",
    "endswith",
    "extend",
    "get",
    "index",
    "insert",
    "items",
    "join",
    "keys",
    "lower",
    "lstrip",
    "pop",
    "remove",
    "replace",
    "reverse",
    "rstrip",
    "setdefault",
    "sort",
    "split",
    "startswith",
    "strip",
    "upper",
    "update",
    "values",
}

FORBIDDEN_NODES = (
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.ClassDef,
    ast.FunctionDef,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


class LambdaSandboxError(RuntimeError):
    """Raised when lambda code is invalid or the sandbox cannot complete."""


class _SandboxValidator(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, FORBIDDEN_NODES):
            raise LambdaSandboxError(f"{type(node).__name__} is not allowed in pipeline lambdas")
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("_"):
            raise LambdaSandboxError("Private and internal names are not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr not in SAFE_METHODS:
            raise LambdaSandboxError(f"Attribute access '{node.attr}' is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in SAFE_BUILTINS:
                raise LambdaSandboxError(f"Calling '{node.func.id}' is not allowed")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr not in SAFE_METHODS:
                raise LambdaSandboxError(f"Calling method '{node.func.attr}' is not allowed")
        else:
            raise LambdaSandboxError("Indirect function calls are not allowed")
        self.generic_visit(node)


def validate_lambda_code(code: str) -> ast.Module:
    if not isinstance(code, str) or not code.strip():
        raise LambdaSandboxError("Lambda code is empty")
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        raise LambdaSandboxError("Lambda code exceeds the 16 KiB limit")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise LambdaSandboxError(f"Invalid lambda syntax: {exc.msg}") from exc
    _SandboxValidator().visit(tree)
    return tree


def run_sandboxed_lambda(code: str, cif_list: list[str], results: dict[str, Any]) -> dict[str, Any]:
    """Execute a pipeline transform in an isolated child with no environment."""
    validate_lambda_code(code)
    payload = json.dumps({"code": code, "cif_list": cif_list, "results": results})
    worker_path = Path(__file__).resolve()

    try:
        with tempfile.TemporaryDirectory(prefix="emos_lambda_") as work_dir:
            completed = subprocess.run(
                [sys.executable, "-I", str(worker_path), "--worker"],
                input=payload,
                text=True,
                capture_output=True,
                cwd=work_dir,
                env={},
                timeout=WALL_TIMEOUT_SECONDS,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise LambdaSandboxError("Lambda exceeded the execution time limit") from exc

    if completed.returncode != 0:
        raise LambdaSandboxError("Lambda sandbox process failed")
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LambdaSandboxError("Lambda sandbox returned an invalid response") from exc
    if not response.get("ok"):
        raise LambdaSandboxError(response.get("error", "Lambda execution failed"))
    return response["result"]


def _apply_resource_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _worker() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        code = payload["code"]
        tree = validate_lambda_code(code)
        _apply_resource_limits()

        namespace = {
            "__builtins__": SAFE_BUILTINS,
            "cif_list": list(payload.get("cif_list", [])),
            "results": dict(payload.get("results", {})),
            "output_cifs": None,
            "output_results": None,
        }
        exec(compile(tree, "<pipeline_lambda>", "exec"), namespace, namespace)

        output_cifs = namespace.get("output_cifs")
        if output_cifs is None:
            output_cifs = namespace["cif_list"]
        output_results = namespace.get("output_results")
        if output_results is None:
            output_results = namespace["results"]

        if not isinstance(output_cifs, list):
            raise LambdaSandboxError("output_cifs must be a list")
        if not all(isinstance(item, str) for item in output_cifs):
            raise LambdaSandboxError("output_cifs must contain only strings")
        if not isinstance(output_results, dict):
            raise LambdaSandboxError("output_results must be a dictionary")

        response = {
            "ok": True,
            "result": {
                "cif_out": output_cifs,
                "result_out": output_results,
            },
        }
        encoded = json.dumps(response)
        if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise LambdaSandboxError("Lambda output exceeds the 5 MiB limit")
    except Exception as exc:
        encoded = json.dumps({"ok": False, "error": str(exc)})

    sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        raise SystemExit(_worker())
    raise SystemExit("This module is only an internal EMOS sandbox worker")