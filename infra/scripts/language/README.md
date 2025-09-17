# Conversational-Agent: Language Setup

## Environment Variables
Expected environment variables:
```
LANGUAGE_ENDPOINT=<language-service-endpoint>

CLU_PROJECT_NAME=<clu-project-name>
CLU_MODEL_NAME=<clu-model-name>
CLU_DEPLOYMENT_NAME=<clu-deployment-name>

CQA_PROJECT_NAME=<cqa-project-name>
CQA_DEPLOYMENT_NAME=production

ORCHESTRATION_PROJECT_NAME=<orchestration-project-name>
ORCHESTRATION_MODEL_NAME=<orchestration-model-name>
ORCHESTRATION_DEPLOYMENT_NAME=<orchestration-deployment-name>
```

## Running Setup (local)
```
az login
bash run_language_setup.sh
```