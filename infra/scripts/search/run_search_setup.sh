#!/bin/bash

set -e

cpx_file="cpx.tar.gz"
cwd=$(pwd)
script_dir=$(dirname $(realpath "$0"))
cd ${script_dir}

# Arguments:
storage_account_name=$1
blob_container_name=$2

# Fetch data:
cp ../../data/${cpx_file} .

# Unzip data:
mkdir cpx_data && mv ${cpx_file} cpx_data/
cd cpx_data && tar -xvzf ${cpx_file} && cd ..

# Upload data to storage account blob container:
echo "Uploading CPX files to blob container..."
az storage blob upload-batch \
    --auth-mode login \
    --destination ${blob_container_name} \
    --account-name ${storage_account_name} \
    --source "cpx_data" \
    --pattern "*.md" \
    --overwrite

# Install requirements:
echo "Installing requirements..."
python3 -m pip install -r requirements.txt

# Run setup:
echo "Running index setup..."
python3 index_setup.py

# Cleanup:
rm -rf cpx_data/
cd ${cwd}

echo "Search setup complete"
