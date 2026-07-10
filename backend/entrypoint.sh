#!/bin/sh
JVM_OPTS="${JVM_OPTS:--XX:+UseZGC -XX:MaxRAMPercentage=75.0}"
exec java $JVM_OPTS -jar /app/app.jar
