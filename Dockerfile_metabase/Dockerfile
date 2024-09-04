FROM arm64v8/openjdk:11-jre-slim

# Set environment variable for Metabase database file
ENV MB_DB_FILE=/metabase.db

# Create the /app directory
RUN mkdir -p /app

# Install wget and download Metabase v0.50.23
RUN apt-get update && \
    apt-get install -y wget && \
    wget -q https://downloads.metabase.com/v0.50.23/metabase.jar -O /app/metabase.jar

# Expose port 3000 for Metabase
EXPOSE 3000

# Set working directory
WORKDIR /app

# Command to run Metabase
CMD ["java", "-jar", "/app/metabase.jar"]
