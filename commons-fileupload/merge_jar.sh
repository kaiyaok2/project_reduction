#!/bin/bash

# Define the input JAR files
MAIN_JAR="target/commons-fileupload-1.5.jar"
TEST_JAR="target/commons-fileupload-1.5-tests.jar"
MERGED_JAR="target/commons-fileupload-1.5-merged.jar"

# Check if the main JAR file exists
if [ ! -f "$MAIN_JAR" ]; then
  echo "Main JAR file $MAIN_JAR does not exist."
  exit 1
fi

# Check if the test JAR file exists
if [ ! -f "$TEST_JAR" ]; then
  echo "Test JAR file $TEST_JAR does not exist."
  exit 1
fi

# Create a temporary directory to extract the JAR contents
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Extract the main JAR file
unzip -q "$MAIN_JAR" -d "$TEMP_DIR"

# Extract the test JAR file, overwriting existing files
unzip -q -o "$TEST_JAR" -d "$TEMP_DIR"

# Create the merged JAR file
jar cf "$MERGED_JAR" -C "$TEMP_DIR" .

# Print success message
echo "Merged JAR created at $MERGED_JAR"
