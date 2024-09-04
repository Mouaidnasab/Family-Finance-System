pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS_ID = "Docker"
        IMAGE_NAME = "mouaidnasab/main_flask" // Replace with your image name
        VERSION_FILE = "VERSION.txt" // File where the version is temporarily stored
    }

    stages {
        stage('Get Latest Version from Docker Hub') {
            steps {
                script {
                    // Fetch the latest version tag from Docker Hub
                    def latestTag = sh(script: "docker pull ${IMAGE_NAME}:latest && docker inspect --format '{{index .RepoTags 0}}' ${IMAGE_NAME}:latest | sed 's/${IMAGE_NAME}://' ", returnStdout: true).trim()
                    echo "Latest version on Docker Hub: ${latestTag}"

                    // Split version into major and minor parts
                    def (major, minor) = latestTag.tokenize('.')
                    
                    // Increment minor version by 0.01
                    def newMinor = minor.toFloat() + 0.01
                    def newVersion = "${major}.${String.format("%.2f", newMinor)}"

                    // Save the new version to the VERSION.txt file
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
                    // Use Groovy to read, update, and write the docker-compose.yml file
                    def dockerComposeFile = readFile('docker-compose.yml')
                    def updatedContent = dockerComposeFile.replaceAll(
                        "${IMAGE_NAME}:latest", 
                        "${IMAGE_NAME}:${env.VERSION}"
                    )
                    writeFile file: 'docker-compose.yml', text: updatedContent
                }
            }
        }

        stage('Remove Existing Container') {
            steps {
                script {
                    // Check if the container is running and remove it if it exists
                    sh '''
                    if [ $(docker ps -q -f name=flask_container) ]; then
                        echo "Removing existing container flask_container"
                        docker stop flask_container
                        docker rm -f flask_container
                    fi
                    '''
                }
            }
        }

        stage('Deploy with Docker Compose') {
            steps {
                script {
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
