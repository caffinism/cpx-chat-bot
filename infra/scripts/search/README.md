# Conversational-Agent: Search Index Setup

## Environment Variables
Expected environment variables:
```
AOAI_ENDPOINT=<aoai-endpoint>
EMBEDDING_DEPLOYMENT_NAME=<embedding-deployment-name>
EMBEDDING_MODEL_NAME=<embedding-model-name>
EMBEDDING_MODEL_DIMENSIONS=<embedding-model-dimensions>

STORAGE_ACCOUNT_CONNECTION_STRING=<storage-connection-string>
BLOB_CONTAINER_NAME=<blob-container-name>

SEARCH_ENDPOINT=<search-endpoint>
SEARCH_INDEX_NAME=<search-index-name>
```

## Running Setup (local)
```
az login
bash run_search_setup.sh <storage-account-name> <blob-container-name>
```