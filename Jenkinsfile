pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS_ID = "c2df98b1-ff47-4992-a415-a7235de00f8a"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/Mouaidnasab/Family-Finance-System.git'
            }
        }

        
        stage('Build and Push Docker Images') {
            when {
                expression { currentBuild.result == null }
            }
            steps {
                script {
                    // Build and push Docker images using Docker Compose
                    sh 'docker-compose build'
                    docker.withRegistry('https://index.docker.io/v1/', env.DOCKER_CREDENTIALS_ID) {
                        sh 'docker-compose push'
                    }
                }
            }
        }

        stage('Deploy with Docker Compose') {
            when {
                expression { currentBuild.result == null }
            }
            steps {
                script {
                    // Stop and remove existing containers if they exist, then deploy new containers
                    sh 'docker-compose down'
                    sh 'docker-compose down --remove-orphans'
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
