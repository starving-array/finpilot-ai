FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
COPY common/pom.xml common/pom.xml
COPY customer/pom.xml customer/pom.xml
COPY feature/pom.xml feature/pom.xml
COPY scoring/pom.xml scoring/pom.xml
COPY audit/pom.xml audit/pom.xml
RUN mvn dependency:go-offline -B
COPY . .
RUN mvn clean package -Dmaven.test.skip=true -B

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/scoring/target/*.jar app.jar
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
