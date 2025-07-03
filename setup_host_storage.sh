#!/bin/bash

# Create host storage directory if it doesn't exist
STORAGE_DIR="/var/skytrack_storage"
sudo mkdir -p $STORAGE_DIR
sudo chmod 777 $STORAGE_DIR

# Create subdirectories
mkdir -p $STORAGE_DIR/fileuploads
mkdir -p $STORAGE_DIR/fileuploads/tac_docs
mkdir -p $STORAGE_DIR/fileuploads/Receipt_files
mkdir -p $STORAGE_DIR/fileuploads/kyc_files
mkdir -p $STORAGE_DIR/fileuploads/cop_files
mkdir -p $STORAGE_DIR/fileuploads/file_bin
mkdir -p $STORAGE_DIR/fileuploads/man
mkdir -p $STORAGE_DIR/fileuploads/media
mkdir -p $STORAGE_DIR/fileuploads/driver
mkdir -p $STORAGE_DIR/fileuploads/notice

echo "Host storage directories created at $STORAGE_DIR"
echo "Make sure to mount this directory as a volume in your Docker container"
echo "Example: docker run -v $STORAGE_DIR:/host_storage your_image_name"
