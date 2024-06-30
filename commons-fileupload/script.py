import os
import re

# Path to the source code directory
source_code_path = '.'

# List of standard Java packages
# standard_java_packages = [
#     'java.',
#     'javax.',
#     'org.w3c.dom.',
#     'org.xml.sax.',
#     'org.xmlpull.v1.',
#     'org.junit',
#     'org.opentest4j'
# ]
standard_java_packages = ['java.', 'org.junit', 'org.opentest4j']

method_regex = (
    r'\s*'
    r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
    r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
    r'(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*'
    r'(<[\w\s,?<>]+>\s*)?'
    r'[\w<>\[\],\s?]+[\w\s,<>.\[\]?]*\s+'
    r'(\w+)\s*'
    r'\(\s*([\w\s,<>\[\].?]*?)\s*\)\s*'
    r'(throws\s+[\w.<>,\s]+)?\s*'
    r'\{'
)
class_regex = (
    r'\s*'
    r'(public|private|protected|static|final|abstract)?\s*'
    r'(public|private|protected|static|final|abstract)?\s*'
    r'(public|private|protected|static|final|abstract)?\s*'
    r'class\s+'
    r'(\w+(\s*<[\w\s,<>]+>)?)\s*'
    r'(\s+extends\s+\w+)?'
    r'(\s+implements\s+[\w\s,<>]+)?'
    r'\s*\{'
)
max_multiline = 5

def identify_current_project_packages(source_code_path):
    packages = set()
    file_count = 0
    for root, _, files in os.walk(source_code_path):
        for file in files:
            if file.endswith('.java'):
                file_count += 1
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                for line in lines:
                    import_match = re.match(r'import\s+(static\s+)?([\w.]+(\.\*)?);', line)
                    if import_match:
                        imported = import_match.group(2)
                        short_class = imported.split('.')[-1]
                        class_package_map[short_class] = imported
                        if not any(imported.startswith(std) for std in standard_java_packages):
                            if not any (imported.startswith(pkg) for pkg in current_project_packages):
                                third_party_packages.add(imported)
    
    return third_party_packages, class_package_map


def identify_override_methods(source_code_path):
    override_methods = set()
    for root, _, files in os.walk(source_code_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                if "/java/" not in file_path:
                    continue
                class_path = file_path.split("/java/")[1].split(".")[0].replace("/", ".")
                class_base_path = class_path.split("$")[0]


                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    outer_class_brace_level = 0
                    inner_class_brace_level = 0
                    inside_outer_class = False
                    inside_inner_class = False

                    for i, line in enumerate(lines):
                        if re.match(class_regex, line) and inside_outer_class:
                            inner_class_match = re.match(class_regex, line)
                            if inner_class_match:
                                inside_inner_class = True
                                inner_class_name = inner_class_match.group(4)
                                class_path += ('$' + inner_class_name)
                        
                        if re.match(class_regex, line) and (not inside_outer_class):
                            inside_outer_class = True
                        
                        if line.strip() == "@Override":
                            next_lines = ''
                            next_line_num = i + 1
                            for k in range(max_multiline - 1):
                                next_lines += lines[next_line_num]
                                next_line_num += 1

                                method_match = re.match(
                                    method_regex,
                                    next_lines
                                )
                                if method_match:
                                    method_signature = method_match.group(5)
                                    full_method_name = class_base_path +\
                                        (("$" + class_path.split('$')[1]) if ('$' in class_path) else '') +\
                                        ":" + method_signature
                                    override_methods.add(full_method_name)
                                    break
                        

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

    return override_methods



def parse_callgraph(callgraph_file):
    call_graph = []
    method_param_map = {}
    with open(callgraph_file, 'r') as f:
        for line in f:
            if line.startswith("M:"):
                caller, callee = line.strip().split()
                caller_method = caller.split(':')[1] + ":" +\
                    caller.split(':')[2].split('(')[0]
                caller_method = re.sub(r'\$\d+', '', re.sub(r'lambda\$', '', caller_method))
                callee_method = callee.split(')')[1]\
                    .split('(')[0]
                callee_method = re.sub(r'\$\d+', '', re.sub(r'lambda\$', '', callee_method))
                call_graph.append((caller_method, callee_method))
                caller_params = caller.split("(")[1].split(")")[0].split(",")
                callee_params = callee.split(")")[1].split("(")[1].split(")")[0].split(",")
                if caller_method in method_param_map:
                    method_param_map[caller_method].update(caller_params)
                else:
                    params = set()
                    params.update(caller_params)
                    method_param_map[caller_method] = params
                if callee_method in method_param_map:
                    method_param_map[callee_method].update(callee_params)
                else:
                    params = set()
                    params.update(callee_params)
                    method_param_map[callee_method] = params
    return call_graph, method_param_map


def identify_third_party_dependencies(call_graph, third_party_packages, override_methods, method_param_map):
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
        if any(callee_class.startswith(pkg) for pkg in third_party_packages)\
            and (caller_method in override_methods):
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
            if (callee_method == method) and (caller_method in override_methods):
                classes_to_remove.add(caller_class)

        for caller_method, callee_method in call_graph:
            caller_class = caller_method.split(":")[0]
            callee_class = callee_method.split(":")[0]
            classes_to_remove_copy = classes_to_remove.copy()
            for class_to_remove in classes_to_remove_copy:
                if caller_class.split("$")[0] == class_to_remove:
                    classes_to_remove.add(caller_class)
                if callee_class.split("$")[0] == class_to_remove:
                    classes_to_remove.add(callee_class)                

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
                    classes_to_remove.add(dependent_class)
        
        for caller_method, callee_method in call_graph:

            callee_class = callee_method.split(":")[0]
            for callee_param in method_param_map[callee_method]:
                if (callee_param in classes_to_remove) or (callee_param in third_party_packages):
                    if callee_class in dependent_class_methods:
                        dependent_class_methods[callee_class].add(callee_method)
                    else:
                        methods = set()
                        methods.add(callee_method)
                        dependent_class_methods[callee_class] = methods
                    if (not callee_method in examined) and (not callee_method in to_examine):
                        to_examine.append(callee_method)

            if callee_class in classes_to_remove:
                if callee_class in dependent_class_methods:
                    dependent_class_methods[callee_class].add(callee_method)
                else:
                    methods = set()
                    methods.add(callee_method)
                    dependent_class_methods[callee_class] = methods
                if (not callee_method in examined) and (not callee_method in to_examine):
                    to_examine.append(callee_method)
            
            caller_class = caller_method.split(":")[0]
            for caller_param in method_param_map[caller_method]:
                if (caller_param in classes_to_remove) or (caller_param in third_party_packages):
                    if caller_class in dependent_class_methods:
                        dependent_class_methods[caller_class].add(caller_method)
                    else:
                        methods = set()
                        methods.add(caller_method)
                        dependent_class_methods[caller_class] = methods
                    if (not caller_method in examined) and (not caller_method in to_examine):
                        to_examine.append(caller_method)
            
            if caller_class in classes_to_remove:
                if caller_class in dependent_class_methods:
                    dependent_class_methods[caller_class].add(caller_method)
                else:
                    methods = set()
                    methods.add(caller_method)
                    dependent_class_methods[caller_class] = methods
                if (not caller_method in examined) and (not caller_method in to_examine):
                    to_examine.append(caller_method)
                
    return classes_to_remove, dependent_class_methods


def refactor_code(source_code_path, dependent_class_methods, third_party_packages, classes_to_remove):
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

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                with open(file_path, 'w') as f:
                    skip_class = False
                    for class_to_remove in classes_to_remove:
                        if class_to_remove == class_base_path:
                            placeholder_written = False
                            skip_class = True
                            package, _, _ = class_base_path.rpartition('.')
                            f.write("package " + package + ";\n")
                            for i, line in enumerate(lines):
                                if placeholder_written:
                                    break
                                multiline = line
                                for j in range(max_multiline):
                                    if j > 0 and (i + j) < len(lines):
                                        multiline += lines[i + j]
                                    if re.match(class_regex, multiline):
                                        f.write(multiline.replace("\n", " ").split("{")[0].split("extends")[0].split("implements")[0])
                                        f.write("{}")
                                        placeholder_written = True
                                        break
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
                    skipping_inner_class = False
                    multiline = None
                    match_some_header = False
                    annotation_cached = False
                    remove_line = False

                    for i, line in enumerate(lines):
                        multiline = line
                        if skip_lines > 0:
                            skip_lines -= 1
                            continue
                        # Skip third-party import statements
                        import_match = re.match(r'import\s+(static\s+)?([\w.]+(\.\*)?);', line)
                        if import_match:
                            imported = import_match.group(2)
                            if (any(imported.startswith(third_pkg) for third_pkg in third_party_packages)) \
                                or (any(imported.startswith(dep_method.replace(":", ".").replace("$", ".")) for dep_method in third_party_packages)) \
                                or (any((imported == class_to_remove.replace("$", ".")) for class_to_remove in classes_to_remove)):
                                continue
                        
                        match_some_header = False
                        for j in range(max_multiline):
                            if j > 0 and (i + j) < len(lines):
                                multiline += lines[i + j] #(" " + lines[i + j].strip())
                            if re.match(class_regex, multiline) and inside_outer_class:
                                inner_class_match = re.match(class_regex, multiline)
                                if inner_class_match:
                                    inside_inner_class = True
                                    match_some_header = True
                                    skip_lines += j
                                    inner_class_name = inner_class_match.group(4)
                                    class_path += ('$' + inner_class_name)
                                    for class_to_remove in classes_to_remove:
                                        if "$" in class_to_remove:
                                            parts = class_to_remove.split('$')
                                            if (parts[0] + "$" + parts[1]) == class_path:
                                                skipping_inner_class = True
                                    break
                            
                            if re.match(class_regex, multiline) and (not inside_outer_class):
                                inside_outer_class = True
                                match_some_header = True
                                skip_lines += j
                            
                            if j == 0:
                                if re.match(r'\s*@\w+(\([^()]*\))?', multiline) and not inside_method:
                                    annotation_buffer.append(multiline)
                                    annotation_cached = True
                                    if i + j < len(lines):
                                        next_line_num = i + 1
                                        next_line = lines[next_line_num]
                                        while re.match(r'^\s*(//.*|/\*(.|[\r\n])*?\*/)?\s*$', next_line) and annotation_buffer:
                                            annotation_buffer.append(next_line)
                                            skip_lines += 1
                                            next_line_num += 1
                                        next_lines = ''
                                        for k in range(max_multiline - 1):
                                            next_lines += lines[next_line_num] #(lines[next_line_num].strip() + " ")
                                            if (next_line_num + 1) < len(lines):
                                                next_line_num += 1
                                            else:
                                                break
                                            method_match = re.match(
                                                method_regex,
                                                next_lines
                                            )
                                            if method_match:
                                                method_signature = method_match.group(5)
                                                full_method_name = class_base_path +\
                                                    (("$" + class_path.split('$')[1]) if ('$' in class_path) else '') +\
                                                    ":" + method_signature
                                                print(next_lines)
                                                exceptions_thrown = method_match.group(7).split("throws")[1].split(",") if method_match.group(7) != None else []
                                                exceptions_thrown_cleaned = [exception.strip() for exception in exceptions_thrown]
                                                classes_names_to_remove = [path.replace("$", ".").split(".")[-1] for path in classes_to_remove]
                                                if (full_method_name in methods_to_remove) or any(ex in classes_names_to_remove for ex in exceptions_thrown_cleaned):
                                                    match_some_header = True
                                                    annotation_buffer = []
                                                    annotation_cached = False
                                                    remove_line = True
                                                    break
                                    else:
                                        f.write(multiline)
                                        break
                                else:
                                    annotation_cached = False
                            
                            # Check if the line is a method header
                            method_match = re.match(
                                method_regex,
                                multiline
                            )
                            if (not inside_method) and method_match:
                                method_signature = method_match.group(5)
                                full_method_name = class_base_path +\
                                    (("$" + class_path.split('$')[1]) if ('$' in class_path) else '') +\
                                    ":" + method_signature
                                inside_method = True
                                skip_method = full_method_name in methods_to_remove
                                method_brace_level = 0  # Start counting from the opening brace
                                match_some_header = True
                                skip_lines += j
                            
                            if match_some_header:
                                break

                        if annotation_cached:
                            continue
                        
                        if annotation_buffer:
                            for annotation in annotation_buffer:
                                if not skipping_inner_class:
                                    f.write(annotation)
                            annotation_buffer = []
                            annotation_cached = False
                        
                        if not match_some_header:
                            multiline = line

                        if inside_method:
                            method_brace_level += multiline.count('{')
                            method_brace_level -= multiline.count('}')

                            if method_brace_level == 0:
                                inside_method = False
                                if skip_method:
                                    skip_method = False
                                    continue
                            if skip_method:
                                continue

                        if inside_outer_class:
                            outer_class_brace_level += multiline.count('{')
                            outer_class_brace_level -= multiline.count('}')
                            if outer_class_brace_level == 0:
                                inside_outer_class = False
                        
                        if inside_inner_class:
                            inner_class_brace_level += multiline.count('{')
                            inner_class_brace_level -= multiline.count('}')
                            if inner_class_brace_level == 0:
                                inside_inner_class = False
                                class_path = class_path.split('$')[0]
                                if skipping_inner_class:
                                    skipping_inner_class = False
                                    continue

                        if remove_line:
                            remove_line = False
                            continue

                        if skipping_inner_class:
                            continue

                        f.write(multiline)



def main():
    current_project_packages = identify_current_project_packages(source_code_path)
    third_party_packages, class_package_map = identify_third_party_packages(source_code_path, current_project_packages)
    call_graph, method_param_map = parse_callgraph('callgraph.txt')
    override_methods = identify_override_methods(source_code_path)
    classes_to_remove, dependent_methods = identify_third_party_dependencies(call_graph, third_party_packages, override_methods, method_param_map)
    refactor_code(source_code_path, dependent_methods, third_party_packages, classes_to_remove)
    print("Refactored code to remove third-party dependencies and their dependents.")


if __name__ == "__main__":
    main()
