import os
import re

# Path to the source code directory
source_code_path = '.'

# List of standard Java packages
standard_java_packages = [
    'java.',
    'javax.',
    'org.w3c.dom.',
    'org.xml.sax.',
    'org.xmlpull.v1.',
    'org.junit'
]

def identify_current_project_packages(source_code_path):
    packages = set()
    file_count = 0
    for root, _, files in os.walk(source_code_path):
        for file in files:
            if file.endswith('.java'):
                file_count += 1
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    package_match = re.match(r'package\s+([\w.]+);', line)
                    if package_match:
                        packages.add(package_match.group(1))
    package_count = len(packages)
    print("Found", file_count, "Java files across", package_count, "package(s).")
    return packages

def identify_third_party_packages(source_code_path, current_project_packages):
    third_party_packages = set()
    class_package_map = {}

    for root, _, files in os.walk(source_code_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    import_match = re.match(r'import\s+([\w.]+);', line)
                    if import_match:
                        full_package = import_match.group(1)
                        short_class = full_package.split('.')[-1]
                        class_package_map[short_class] = full_package
                        if not any(full_package.startswith(std) for std in standard_java_packages):
                            if not any (full_package.startswith(pkg) for pkg in current_project_packages):
                                third_party_packages.add(full_package)
    
    print(third_party_packages)
    return third_party_packages, class_package_map


def parse_callgraph(callgraph_file):
    call_graph = []
    with open(callgraph_file, 'r') as f:
        for line in f:
            if line.startswith("M:"):
                caller, callee = line.strip().split()
                caller_method = caller.split(':')[1] + ":" +\
                    caller.split(':')[2].split('(')[0]
                callee_method = callee.split(')')[1]\
                    .split('(')[0]
                call_graph.append((caller_method, callee_method))
    return call_graph


def identify_third_party_dependencies(call_graph, third_party_packages, class_package_map):
    classes_to_remove = set()
    dependent_class_methods = {}
    to_examine = []
    examined = set()

    for caller_method, callee_method in call_graph:
        caller_class = caller_method.split(":")[0]
        callee_class = callee_method.split(":")[0]
        if any(callee_class.startswith(pkg) for pkg in third_party_packages)\
            and (("<init>" in caller_method) or ("<clinit>" in caller_method) or ("setUp" in caller_method) or ("tearDown" in caller_method)):
            classes_to_remove.add(caller_class)
    
    for caller_method, callee_method in call_graph:
        caller_class = caller_method.split(":")[0]
        callee_class = callee_method.split(":")[0]
        if any(callee_class.startswith(pkg) for pkg in third_party_packages)\
            or (caller_class in classes_to_remove):
            if caller_class in dependent_class_methods:
                dependent_class_methods[caller_class].add(caller_method)
            else:
                methods = set()
                methods.add(caller_method)
                dependent_class_methods[caller_class] = methods
            to_examine.append(caller_method)

    
    while to_examine:
        method = to_examine.pop(0)
        examined.add(method)

        for caller_method, callee_method in call_graph:
            caller_class = caller_method.split(":")[0]
            if (callee_method == method)\
                and (("<init>" in caller_method) or ("<clinit>" in caller_method) or ("setUp" in caller_method) or ("tearDown" in caller_method)):
                classes_to_remove.add(caller_class)

        for caller_method, callee_method in call_graph:
            callee_class = callee_method.split(":")[0]
            caller_class = caller_method.split(":")[0]
            if (callee_method == method) or (caller_class in classes_to_remove):
                if caller_class in dependent_class_methods:
                    dependent_class_methods[caller_class].add(caller_method)
                else:
                    methods = set()
                    methods.add(caller_method)
                    dependent_class_methods[caller_class] = methods
                if (not caller_method in examined) and (not caller_method in to_examine):
                    to_examine.append(caller_method)
                

    
    for dependent_class in dependent_class_methods:
        for method in dependent_class_methods[dependent_class]:
            if (("<init>" in method) or ("<clinit>" in method) or ("setUp" in method) or ("tearDown" in method)):
                classes_to_remove.add(caller_class)
    return classes_to_remove, dependent_class_methods


def refactor_code(source_code_path, dependent_class_methods, third_party_packages, classes_to_remove):
    method_regex = (
        r'\s*'
        r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
        r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
        r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
        r'(<[\w\s,?<>]+>\s*)?'
        r'[\w<>\[\]]+\s+'
        r'(\w+)\s*'
        r'\([^)]*\)\s*'
        r'(throws\s+[\w.<>,\s]+)?\s*'
        r'\{'
    )
    class_regex = (
        r'\s*'
        r'(public|private|protected|static|final|abstract)?\s*'
        r'(public|private|protected|static|final|abstract)?\s*'
        r'(public|private|protected|static|final|abstract)?\s*'
        r'class\s+'
        r'(\w+)\s*'
        r'(\s+extends\s+\w+)?'
        r'(\s+implements\s+[\w\s,<>]+)?'
        r'\s*\{'
    )
    for root, _, files in os.walk(source_code_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                if "/java/" not in file_path:
                    continue
                class_path = file_path.split("/java/")[1].split(".")[0].replace("/", ".")
                class_base_path = class_path.split("$")[0]

                methods_to_remove = set()
                # Find all keys in the format "{path}.Outer$xxxxxxx" and add to methods_to_remove
                for key, methods in dependent_class_methods.items():
                    if key.split("$")[0] == class_base_path:
                        methods_to_remove.update(methods)

                if not methods_to_remove:
                    continue
                
                print(f"Refactoring {class_path}")

                with open(file_path, 'r') as f:
                    lines = f.readlines()

                with open(file_path, 'w') as f:
                    skip_class = False
                    for class_to_remove in classes_to_remove:
                        if class_to_remove.split("$")[0] == class_base_path:
                            skip_class = True
                            f.write("public class " + file.split(".")[0] + " {}")
                            break
                    if skip_class:
                        continue
                    inside_method = False
                    skip_method = False
                    annotation_buffer = []
                    method_brace_level = 0
                    outer_class_brace_level = 0
                    inner_class_brace_level = 0
                    skip_lines = 0
                    inside_outer_class = False
                    inside_inner_class = False

                    for i, line in enumerate(lines):
                        if skip_lines > 0:
                            skip_lines -= 1
                            continue
                        # Skip third-party import statements
                        import_match = re.match(r'import\s+([\w.]+);', line)
                        if import_match:
                            full_package = import_match.group(1)
                            if any(full_package.startswith(pkg) for pkg in third_party_packages):
                                continue
                        
                        if re.match(class_regex, line) and inside_outer_class:
                            inner_class_match = re.match(class_regex, line)
                            if inner_class_match:
                                inside_inner_class = True
                                inner_class_name = inner_class_match.group(4)
                                class_path += ('$' + inner_class_name)
                        
                        if re.match(class_regex, line) and (not inside_outer_class):
                            inside_outer_class = True
                        
                        # Check if the line is an annotation or a method header
                        if re.match(r'\s*@\w+', line) and not inside_method:
                            annotation_buffer.append(line)
                            if i + 1 < len(lines):
                                next_line_num = i + 1
                                next_line = lines[next_line_num]
                                while re.match(r'^\s*(//.*|/\*(.|[\r\n])*?\*/)?\s*$', next_line) and annotation_buffer:
                                    annotation_buffer.append(next_line)
                                    skip_lines += 1
                                    next_line_num += 1
                                    next_line = lines[next_line_num]
                                method_match = re.match(
                                    method_regex,
                                    next_line
                                )
                                if method_match:
                                    method_signature = method_match.group(5)
                                    full_method_name = class_base_path +\
                                        (("$" + class_path.split('$')[1]) if ('$' in class_path) else '') +\
                                        ":" + method_signature
                                    if full_method_name in methods_to_remove:
                                        annotation_buffer = []
                            else:
                                f.write(line)
                            continue
                        else:
                            if annotation_buffer:
                                for annotation in annotation_buffer:
                                    f.write(annotation)
                                annotation_buffer = []
                        
                        # Check if the line is a method header
                        method_match = re.match(
                            method_regex,
                            line
                        )
                        if (not inside_method) and method_match:
                            method_signature = method_match.group(5)
                            full_method_name = class_base_path +\
                                (("$" + class_path.split('$')[1]) if ('$' in class_path) else '') +\
                                ":" + method_signature
                            inside_method = True
                            skip_method = full_method_name in methods_to_remove
                            method_brace_level = 0  # Start counting from the opening brace

                        if inside_method:
                            method_brace_level += line.count('{')
                            method_brace_level -= line.count('}')

                            if method_brace_level == 0:
                                inside_method = False
                                if skip_method:
                                    skip_method = False
                                    continue
                            if skip_method:
                                continue

                        if inside_outer_class:
                            outer_class_brace_level += line.count('{')
                            outer_class_brace_level -= line.count('}')
                            if outer_class_brace_level == 0:
                                inside_outer_class = False
                        
                        if inside_inner_class:
                            inner_class_brace_level += line.count('{')
                            inner_class_brace_level -= line.count('}')
                            if inner_class_brace_level == 0:
                                inside_inner_class = False
                                class_path = class_path.split('$')[0]
                        
                        f.write(line)


def main():
    current_project_packages = identify_current_project_packages(source_code_path)
    third_party_packages, class_package_map = identify_third_party_packages(source_code_path, current_project_packages)
    call_graph = parse_callgraph('callgraph.txt')
    classes_to_remove, dependent_methods = identify_third_party_dependencies(call_graph, third_party_packages, class_package_map)
    refactor_code(source_code_path, dependent_methods, third_party_packages, classes_to_remove)
    print("Refactored code to remove third-party dependencies and their dependents.")


if __name__ == "__main__":
    main()

