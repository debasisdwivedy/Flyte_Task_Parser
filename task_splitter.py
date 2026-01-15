import ast
import astor
from typing import List


def split_into_parts(body: list[ast.stmt], annotated_func: bool):
    parts = []
    current = []
    current_kind = None

    for stmt in body:
        kind = stmt_kind(stmt, annotated_func)

        if kind == "terminal":
            current.append(stmt)
            parts.append((current_kind or "side_effect", current))
            current = []
            current_kind = None
            continue

        if current_kind is None or kind == current_kind:
            current.append(stmt)
            current_kind = kind
        else:
            parts.append((current_kind, current))
            current = [stmt]
            current_kind = kind

    if current:
        parts.append((current_kind, current))

    return parts

def is_annotated_call(stmt, annotated_func: set[str]) -> bool:
    if not (
        isinstance(stmt, ast.Assign)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name)
    ):
        return False

    return annotated_func

def stmt_kind(stmt, annotated_func: bool):
    # annotated compute
    if is_annotated_call(stmt, annotated_func):
        return "annotated_compute"

    # normal compute
    if isinstance(stmt, ast.Assign):
        return "compute"

    # side-effects
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return "side_effect"

    # terminal
    if isinstance(stmt, ast.Return):
        return "terminal"

    return "side_effect"

def extract_inputs_outputs(stmts):
    inputs = set()
    outputs = set()

    for stmt in stmts:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    outputs.add(t.id)

            for n in ast.walk(stmt.value):
                if isinstance(n, ast.Name):
                    inputs.add(n.id)

        elif isinstance(stmt, ast.Expr):
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name):
                    inputs.add(n.id)

    return inputs - outputs, outputs

def env_task_decorator():
    return ast.Attribute(
        value=ast.Name(id="env", ctx=ast.Load()),
        attr="task",
        ctx=ast.Load(),
    )

def build_function(name, args, body, returns, annotate=False):
    if returns:
        ret_node = (
            ast.Return(ast.Name(id=returns[0], ctx=ast.Load()))
            if len(returns) == 1
            else ast.Return(
                ast.Tuple(
                    elts=[ast.Name(id=v, ctx=ast.Load()) for v in returns],
                    ctx=ast.Load(),
                )
            )
        )
        body = body + [ret_node]

    decorators = [env_task_decorator()] if annotate else []

    return ast.FunctionDef(
        name=name,
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=a) for a in args],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=body,
        decorator_list=decorators,
    )

def find_function(tree: ast.Module, fn_name: str | None = None):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if fn_name is None or node.name == fn_name:
                return node
    # raise ValueError("No function definition found")
    return None

def split_function(source: str,annotated_task:bool):
    tree = ast.parse(source)
    fn = find_function(tree)
    if not fn:
        return
    parts = split_into_parts(fn.body,annotated_task)

    generated = []
    runner_body = []
    available_vars = set(a.arg for a in fn.args.args)

    for i, (kind, part) in enumerate(parts):
        inputs, outputs = extract_inputs_outputs(part)
        inputs = list(inputs & available_vars)
        returns = list(outputs)

        fname = f"{fn.name}{i}"

        generated.append(
            build_function(
                fname,
                inputs,
                part,
                returns,
                annotate=(kind == "side_effect"),
            )
        )

        call = ast.Call(
            func=ast.Name(id=fname, ctx=ast.Load()),
            args=[ast.Name(id=v, ctx=ast.Load()) for v in inputs],
            keywords=[],
        )

        if returns:
            targets = (
                [ast.Name(id=returns[0], ctx=ast.Store())]
                if len(returns) == 1
                else [ast.Name(id=v, ctx=ast.Store()) for v in returns]
            )

            runner_body.append(
                ast.Assign(
                    targets=[ast.Tuple(elts=targets, ctx=ast.Store())],
                    value=call,
                )
            )

            available_vars.update(returns)
        else:
            runner_body.append(ast.Expr(value=call))

    # preserve original return
    for stmt in reversed(fn.body):
        if isinstance(stmt, ast.Return):
            runner_body.append(stmt)
            break

    runner = ast.FunctionDef(
        name=f"{fn.name}_runner",
        args=fn.args,
        body=runner_body,
        decorator_list=[],
    )

    mod = ast.Module(body=generated + [runner], type_ignores=[])
    return astor.to_source(mod)


def main(data:str,flag:bool):
    return split_function(data,flag)