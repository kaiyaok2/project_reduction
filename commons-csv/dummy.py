import re

# Updated regex to match Java method headers
regex = r'\s*(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*(public|private|protected|static|synchronized|final|abstract|native|transient|volatile|strictfp)?\s*(<[\w\s,?<>]+>\s*)?[\w<>[\]]+\s+(\w+)\s*\([^)]*\)\s*(throws\s+[\w.<>,\s]+)?\s*\{'

examples = [
    "public synchronized void printRecord(final Iterable<?> values) throws IOException {",
    "public static Matcher<Token> hasContent(final String expectedContent) {",
    "public void exampleMethod() {",
    "private int calculateSum(int a, int b) {",
    "protected List<String> getList() throws CustomException {",
    "static synchronized <T> void doSomething(T param) {",
    "protected int ZUBAC(int dw, T<T> GAga) {",
    "void testAT() {",
    "public void testIsInconsistent() throws IOException {",
    "public void printRecord(final Object... values) throws IOException {",
    "public final class CSVPrinter implements Flushable, Closeable {",
    "public CSVPrinter(final Appendable appendable, final CSVFormat format) throws IOException {"
]

for example in examples:
    match = re.match(regex, example)
    if match:
        print(f"Example: {example}")
        print(f"Method name: {match.group(5)}\n")
    else:
        print(f"No match for: {example}\n")




print('\n=================================================\n')
import re

# Updated regex to match Java class headers, including 'final' modifier
class_regex = (
    r'\s*'
    r'(public|private|protected|static|final|abstract)?\s*'  # Optional access modifiers including 'final'
    r'(public|private|protected|static|final|abstract)?\s*'  # Optional second modifier
    r'(public|private|protected|static|final|abstract)?\s*'  # Optional third modifier
    r'class\s+'  # 'class' keyword
    r'(\w+)\s*'  # Class name
    r'(\s+extends\s+\w+)?'  # Optional 'extends' clause
    r'(\s+implements\s+[\w\s,<>]+)?'  # Optional 'implements' clause
    r'\s*\{'
)

# Example Java class headers
examples = [
    "public static class MyClass implements Interface1, Interface2 {",
    "private final class AnotherClass extends BaseClass {",
    "protected class SimpleClass {",
    "class NoModifierClass {",
    "final class CSVRecordIterator implements Iterator<CSVRecord> {",
    "public final class CSVParser implements Iterable<CSVRecord>, Closeable {"
]

for example in examples:
    match = re.match(class_regex, example)
    if match:
        print(f"Example: {example}")
        print(f"Class name: {match.group(4)}\n")
    else:
        print(f"No match for: {example}\n")