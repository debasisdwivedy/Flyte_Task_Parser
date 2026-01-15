import ast
from task_splitter import main as split_task
def has_decorator(fn, name: str) -> bool:
    if not isinstance(fn, ast.FunctionDef):
        return False
    for d in fn.decorator_list:
        # print(d)
        if isinstance(d, ast.Name) and d.id == name:
            return True
        if isinstance(d, ast.Attribute) and d.attr == name:
            return True
    return False

def step_has_decorated_function(step, decorator_name: str) -> bool:
    for node in step:
        if isinstance(node, ast.FunctionDef):
            if has_decorator(node, decorator_name):
                return True
    return False

def has_call(stmt):
    return any(isinstance(n, ast.Call) for n in ast.walk(stmt))

def split_statements(statements):
    steps = []
    current = []

    for stmt in statements:
        if has_call(stmt) and current:
            steps.append(current)
            current = [stmt]
        else:
            current.append(stmt)

    if current:
        steps.append(current)

    return steps

with open("examples/code_test.py","r") as f:
    data = f.read()

tree = ast.parse(data)
fn = tree.body[0]

steps = split_statements(tree.body)

for i, step in enumerate(steps, 1):
    print(f"\n# ---- A_step{i} ----")
    if step_has_decorated_function(step,"task"):
        #print(True)
        #print(ast.unparse(step))
        modified_step = split_task(ast.unparse(step),True)
    else:
        #print(False)
        #print(ast.unparse(step))
        modified_step = split_task(ast.unparse(step),False)
    
    if modified_step:
        print(modified_step)
    else:
        print(ast.unparse(step))