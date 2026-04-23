import os
import ast
import json
from collections import defaultdict

def get_module_name(base_path, file_path):
    relative_path = os.path.relpath(file_path, base_path)
    module_name = relative_path.replace(os.sep, '.')
    if module_name.endswith('.__init__.py'):
        return module_name[:-len('.__init__.py')]
    elif module_name.endswith('.py'):
        return module_name[:-len('.py')]
    return module_name

def collect_dependencies(base_path):
    module_files = {} # module_name -> file_path
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', 'dist', 'build', 'venv', '.venv'}]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                module_name = get_module_name(base_path, file_path)
                module_files[module_name] = file_path

    dependencies = defaultdict(set) # module -> set of modules it imports
    reverse_dependencies = defaultdict(set) # module -> set of modules that import it
    all_internal_modules = set(module_files.keys())

    for module_name, file_path in module_files.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_module = alias.name
                        # Check if it's an internal import
                        if imported_module in all_internal_modules:
                            dependencies[module_name].add(imported_module)
                            reverse_dependencies[imported_module].add(module_name)
                        else:
                            # Handle package imports like 'flask'
                            parts = imported_module.split('.')
                            if parts[0] in all_internal_modules:
                                dependencies[module_name].add(parts[0])
                                reverse_dependencies[parts[0]].add(module_name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_module_base = node.module
                        if node.level > 0: # Relative import
                            current_module_parts = module_name.split('.')
                            # Adjust for __init__.py files
                            if current_module_parts[-1] == '__init__':
                                current_module_parts.pop()
                            
                            resolved_module_parts = current_module_parts[:len(current_module_parts) - node.level] + imported_module_base.split('.')
                            resolved_module = '.'.join(resolved_module_parts)
                        else: # Absolute import
                            resolved_module = imported_module_base

                        # Check if the resolved module or its parent package is internal
                        potential_imports = set()
                        # Add the exact resolved module
                        potential_imports.add(resolved_module)
                        # Add potential __init__ modules for packages
                        potential_imports.add(resolved_module + '.__init__')
                        # Add parent packages if the import is for a submodule
                        parts = resolved_module.split('.')
                        for i in range(1, len(parts)):
                            potential_imports.add('.'.join(parts[:i]) + '.__init__')
                            potential_imports.add('.'.join(parts[:i])) # Also consider package itself

                        for imp_mod in potential_imports:
                            if imp_mod in all_internal_modules:
                                dependencies[module_name].add(imp_mod)
                                reverse_dependencies[imp_mod].add(module_name)
                                break # Found a match, no need to check further for this import statement

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    return all_internal_modules, dependencies, reverse_dependencies

def find_circular_dependencies(graph):
    cycles = []
    path = []
    visited = set()
    recursion_stack = set()

    def dfs(node):
        visited.add(node)
        recursion_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in recursion_stack:
                cycle_start_index = path.index(neighbor)
                cycles.append(path[cycle_start_index:] + [neighbor])
        
        path.pop()
        recursion_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node)
    return cycles

def main():
    backend_path = "C:\\Veritas_Lab\\gravity-omega-v2\\backend"
    
    all_modules, dependencies, reverse_dependencies = collect_dependencies(backend_path)

    total_modules = len(all_modules)
    total_internal_edges = sum(len(deps) for deps in dependencies.values())

    # In-degree (most imported)
    in_degree = {module: len(reverse_dependencies[module]) for module in all_modules}
    top_in_degree = sorted(in_degree.items(), key=lambda item: item[1], reverse=True)[:5]

    # Out-degree (imports the most)
    out_degree = {module: len(dependencies[module]) for module in all_modules}
    top_out_degree = sorted(out_degree.items(), key=lambda item: item[1], reverse=True)[:5]

    # Circular dependencies
    # Convert dependencies to a format suitable for cycle detection (dict of lists)
    graph_for_cycles = {k: list(v) for k, v in dependencies.items()}
    circular_deps = find_circular_dependencies(graph_for_cycles)

    # Orphan modules (in-degree of 0)
    orphan_modules = [module for module, degree in in_degree.items() if degree == 0 and module not in dependencies] # Ensure it's not just a module that imports nothing, but is also not imported

    results = {
        "total_modules": total_modules,
        "total_internal_edges": total_internal_edges,
        "top_in_degree": top_in_degree,
        "top_out_degree": top_out_degree,
        "circular_dependencies": circular_deps,
        "orphan_modules": orphan_modules
    }

    output_path = "C:\\Users\\rlope\\.veritas\\python_dependency_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

    print(f"Dependency data saved to {output_path}")

if __name__ == "__main__":
    main()
