pipeline {
    agent { docker { image 'public.ecr.aws/sam/build-python3.9:1.93.0' } }
    options {
        buildDiscarder(logRotator(numToKeepStr: '5', artifactNumToKeepStr: '5'))
    }
    stages {
        stage('build') {
            steps {
                sh 'SAM_CLI_TELEMETRY=0 HOME=/var/tmp sam build'
            }
        }
        stage('deploy to deb') {
            steps {
                withAWS(credentials: '32f7b64c-13db-4ad1-8caa-a3a9bdc0ef92', region: 'us-east-1') {
                    sh 'SAM_CLI_TELEMETRY=0 HOME=/var/tmp sam deploy --config-env=dev'
                }
            }
        }
        stage('deploy to qa') {
            steps {
                withAWS(credentials: '32f7b64c-13db-4ad1-8caa-a3a9bdc0ef92', region: 'us-east-1') {
                    sh 'SAM_CLI_TELEMETRY=0 HOME=/var/tmp sam deploy --config-env=qa'
                }
            }
        }
    }
}
