#ifndef SMARTDOOR_H
#define SMARTDOOR_H

#include <librealsense2/rs.hpp>
#include <opencv2/opencv.hpp>
#include <string>
#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>
#include <fstream>

using namespace std;

// Function to capture an image from the RealSense camera and save it
void captureSnapshot(const string& profile, const string& folderPath);

// Function to upload an image to an AWS S3 bucket
void uploadToS3(const string& bucket_name, const string& file_name, const string& object_name);

#endif
