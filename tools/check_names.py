# -*- coding: utf-8 -*-
"""
Checagem estatica leve, no lugar do pyflakes (que nao esta instalado):

  1. todo `self.X` LIDO numa classe tem um `self.X = ...` em algum
     metodo dessa classe (pega typo e atributo esquecido no invoke);
  2. todo nome global usado num modulo esta definido, importado, ou e
     builtin (pega funcao renomeada e import esquecido);
  3. nao existe ciclo de import entre os modulos do addon.

Nao substitui rodar dentro do Blender, mas pega barato o que so
apareceria como AttributeError/NameError no meio de um arraste.
"""

import ast
import builtins
import io
import os
import sys

PROJECT = sys.argv[1]

BUILTINS = set(dir(builtins))

problems = []


def walk_python_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "tools"}]
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(base, name)


def check_self_attributes(tree, rel):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        assigned = set()
        read = {}

        # anotacoes de classe (bl_idname etc) e properties do Blender
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                assigned.add(item.target.id)
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)

        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                if sub.value.id != "self":
                    continue
                if isinstance(sub.ctx, (ast.Store, ast.Del)):
                    assigned.add(sub.attr)
                else:
                    read.setdefault(sub.attr, sub.lineno)

        for attr, lineno in sorted(read.items(), key=lambda kv: kv[1]):
            if attr in assigned:
                continue
            # metodos da propria classe / herdados do bpy.types.Operator
            if any(
                isinstance(item, ast.FunctionDef) and item.name == attr
                for item in node.body
            ):
                continue
            if attr in {
                "report", "layout", "bl_idname", "bl_label", "bl_options",
                "as_keywords", "poll", "id_data", "bl_rna",
            }:
                continue
            problems.append(
                f"{rel}:{lineno} {node.name}.self.{attr} lido mas nunca atribuido"
            )


def check_global_names(tree, rel):
    defined = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])

    # nomes ligados dentro de escopos (parametros, locais, comprehensions)
    local = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # def/class aninhado liga o nome no escopo de fora
            local.add(node.name)

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            for group in (args.posonlyargs, args.args, args.kwonlyargs):
                for arg in group:
                    local.add(arg.arg)
            if args.vararg:
                local.add(args.vararg.arg)
            if args.kwarg:
                local.add(args.kwarg.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                local.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            local.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            local.add(node.name)
        elif isinstance(node, ast.Global):
            local.update(node.names)

    known = defined | local | BUILTINS | {"self", "cls", "__file__", "__name__"}

    seen = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in known:
                seen.setdefault(node.id, node.lineno)

    for name, lineno in sorted(seen.items(), key=lambda kv: kv[1]):
        problems.append(f"{rel}:{lineno} nome global '{name}' nao definido")


def check_import_cycles(root):
    """Ciclo entre modulos do addon.

    Um import circular so estoura quando o Blender carrega o addon,
    e a mensagem que ele da (ImportError no meio de um import
    parcial) nao aponta pro par culpado. Barato de detectar aqui.
    """
    separator = os.sep
    edges = {}

    for path in walk_python_files(root):
        rel = os.path.relpath(path, root).replace(separator, "/")
        module = rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]

        package = module.rsplit(".", 1)[0] if "." in module else ""

        dependencies = set()
        tree = ast.parse(io.open(path, encoding="utf-8").read(), rel)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            parts = package.split(".") if package else []
            up = node.level - 1
            target = parts[: len(parts) - up] if up else parts
            if node.module:
                target = target + [node.module]
            dependencies.add(".".join(target))

        edges[module] = dependencies

    seen = set()
    stack = []

    def visit(module):
        if module in stack:
            cycle = stack[stack.index(module):] + [module]
            problems.append("ciclo de import: " + " -> ".join(cycle))
            return
        if module in seen:
            return
        seen.add(module)
        stack.append(module)
        for dependency in sorted(edges.get(module, ())):
            if dependency in edges:
                visit(dependency)
        stack.pop()

    for module in sorted(edges):
        visit(module)


for path in walk_python_files(PROJECT):
    rel = os.path.relpath(path, PROJECT).replace("\\", "/")
    tree = ast.parse(io.open(path, encoding="utf-8").read(), rel)
    check_self_attributes(tree, rel)
    check_global_names(tree, rel)

check_import_cycles(PROJECT)

if problems:
    print(f"{len(problems)} problema(s):")
    for problem in problems:
        print("  -", problem)
    sys.exit(1)

print("nenhum atributo/nome/ciclo suspeito encontrado")
