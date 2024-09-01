pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS_ID = "docker"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/Mouaidnasab/Family-Finance-System.git'
            }
        }

        
        


        stage('Build and Push Docker Images') {
            steps {
                script {
                    // Ensure all containers and resources are cleaned up
                    sh 'docker-compose down --remove-orphans'
                    sh 'docker-compose build'
                    withDockerRegistry(credentialsId:  env.DOCKER_CREDENTIALS_ID) {
                        sh 'docker-compose push'
                    }
                }
            }
        }
        stage('Deploy with Docker Compose') {
            steps {
                script {
                    // Check and remove any existing container with the same name
                    sh '''
                    if [ $(docker ps -aq -f name=mysql_container) ]; then
                        docker rm -f mysql_container
                    fi
                    '''
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
