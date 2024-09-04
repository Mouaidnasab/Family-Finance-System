pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS_ID = "Docker"
        IMAGE_NAME = "mouaidnasab/main_flask" // Replace with your image name
        VERSION_FILE = "VERSION.txt" // File where the version is stored
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/Mouaidnasab/Family-Finance-System.git'
            }
        }

        stage('Read Current Version') {
            steps {
                script {
                    // Read the current version from the file
                    def currentVersion = sh(script: "cat ${VERSION_FILE}", returnStdout: true).trim()
                    echo "Current version: ${currentVersion}"

                    // Split version into major and minor parts
                    def (major, minor) = currentVersion.tokenize('.')
                    
                    // Increment minor version by 0.01
                    def newMinor = minor.toFloat() + 0.01
                    def newVersion = "${major}.${String.format("%.2f", newMinor)}"

                    // Save the new version back to the file
                    writeFile file: "${VERSION_FILE}", text: newVersion
                    echo "New version: ${newVersion}"

                    // Set environment variable for later stages
                    env.VERSION = newVersion
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image with the incremented version
                    sh "docker build --build-arg VERSION=${env.VERSION} -t ${IMAGE_NAME}:${env.VERSION} ."
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    withDockerRegistry(credentialsId: env.DOCKER_CREDENTIALS_ID) {
                        // Push the Docker image with the incremented version
                        sh "docker push ${IMAGE_NAME}:${env.VERSION}"
                    }
                }
            }
        }

        stage('Update Docker Compose File') {
            steps {
                script {
                    // Use Groovy to update docker-compose.yml
                    def yaml = readYaml file: 'docker-compose.yml'
                    yaml.services.flask_app.image = "${IMAGE_NAME}:${env.VERSION}"
                    writeYaml file: 'docker-compose.yml', data: yaml
                }
            }
        }

        stage('Deploy with Docker Compose') {
            steps {
                script {
                    sh 'docker-compose down --remove-orphans'
                    sh 'docker-compose pull'
                    sh 'docker-compose up -d'
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        failure {
            echo 'Pipeline failed, no deployment will be performed.'
        }
        
        success {
            echo 'Pipeline succeeded, application deployed using Docker Compose.'
        }
    }
}
