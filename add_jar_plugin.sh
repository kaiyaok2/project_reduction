#!/bin/bash

plugin_config=$(cat <<EOF
    <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-jar-plugin</artifactId>
        <version>3.2.0</version>
        <executions>
            <execution>
                <goals>
                    <goal>test-jar</goal>
                </goals>
            </execution>
        </executions>
    </plugin>
EOF
)

insertion_point="<plugins>"

sed -i "/$insertion_point/a\\
$plugin_config" pom.xml

echo "Plugin configuration added to pom.xml"
