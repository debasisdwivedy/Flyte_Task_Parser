import flyte
from functools import lru_cache

task_env = flyte.TaskEnvironment(name="hello_world")

@lru_cache
def B(l) -> str:
  print(f"The list is {l}")
  return "hello"

@task_env.task
@lru_cache
def C(s)->int:
  print(f"The string is {s}")
  return 20

@task_env.task
def A(lst:list[int])->int:
    x = call_fn("hello")
    s1 = B(lst)
    s2 = C(x)
    val = C(s1)
    print("Expensive operation 1")
    print("Expensive operation 2")
    s3 = B(s2)
    print("Hello Dev")
    return val