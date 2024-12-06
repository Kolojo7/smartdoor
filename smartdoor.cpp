#include "smartdoor.h"
#include <iostream>

void captureSnapshot(const string& profile, const string& folderPath) {
    // Set up RealSense pipeline with higher resolution
    rs2::pipeline pipe;
    rs2::config cfg;
    cfg.enable_stream(RS2_STREAM_COLOR, 1280, 800, RS2_FORMAT_BGR8, 30);  // High resolution for color
    cfg.enable_stream(RS2_STREAM_DEPTH, 1280, 720, RS2_FORMAT_Z16, 30);   // High resolution for depth
    pipe.start(cfg);

    // Allow auto-exposure to stabilize
    for (int i = 0; i < 30; ++i) pipe.wait_for_frames();

    // Capture frames
    rs2::frameset frames = pipe.wait_for_frames();
    rs2::frame color_frame = frames.get_color_frame();
    rs2::frame depth_frame = frames.get_depth_frame();

    if (!color_frame || !depth_frame) {
        cerr << "Error: Failed to capture valid frames!" << endl;
        return;
    }

    // Convert frames to OpenCV Mat
    cv::Mat color_image(cv::Size(color_frame.as<rs2::video_frame>().get_width(),
                                 color_frame.as<rs2::video_frame>().get_height()),
                        CV_8UC3, (void*)color_frame.get_data(), cv::Mat::AUTO_STEP);

    cv::Mat depth_image(cv::Size(depth_frame.as<rs2::video_frame>().get_width(),
                                 depth_frame.as<rs2::video_frame>().get_height()),
                        CV_16UC1, (void*)depth_frame.get_data(), cv::Mat::AUTO_STEP);

    // Normalize depth and apply a color map
    cv::Mat depth_normalized, depth_colored;
    cv::normalize(depth_image, depth_normalized, 0, 255, cv::NORM_MINMAX, CV_8UC1);
    cv::applyColorMap(depth_normalized, depth_colored, cv::COLORMAP_JET);

    // Construct file names using a different method
    string baseFileName = folderPath + "/" + profile;
    string colorFileName = baseFileName + "_rgb.jpg";
    string depthFileName = baseFileName + "_colordepth.png";

    // Save RGB image
    if (!cv::imwrite(colorFileName, color_image)) {
        cerr << "Error: Failed to save RGB image!" << endl;
    } else {
        cout << "Saved RGB image: " << colorFileName.substr(colorFileName.find_last_of("/") + 1) << endl;
    }

    // Save Depth image
    if (!cv::imwrite(depthFileName, depth_colored)) {
        cerr << "Error: Failed to save Depth image!" << endl;
    } else {
        cout << "Saved Depth image: " << depthFileName.substr(depthFileName.find_last_of("/") + 1) << endl;
    }

    // Upload to S3 after saving the images
    uploadToS3("smartdoorpictures", colorFileName, "RGB Pictures/" + profile + "_rgb.jpg");
    uploadToS3("smartdoorpictures", depthFileName, "Color Depth Pictures/" + profile + "_depth_colored.png");
}

void uploadToS3(const string& bucket_name, const string& file_name, const string& object_name) {
    Aws::SDKOptions options;
    Aws::InitAPI(options);
    {
        Aws::S3::S3Client s3_client;

        // Open the file
        ifstream input_file(file_name, ios::binary);
        if (!input_file.is_open()) {
            cerr << "Failed to open file: " << file_name << endl;
            return;
        }

        Aws::S3::Model::PutObjectRequest request;
        request.SetBucket(bucket_name);
        request.SetKey(object_name);

        // Set the file to upload
        shared_ptr<Aws::IOStream> data_stream = Aws::MakeShared<Aws::FStream>("UploadFileStream", file_name.c_str(), ios_base::in | ios_base::binary);
        request.SetBody(data_stream);

        // Perform the upload
        auto outcome = s3_client.PutObject(request);

        if (outcome.IsSuccess()) {
            cout << "Successfully uploaded the pictures to " << bucket_name << endl;
        } else {
            cerr << "Error uploading file: " << outcome.GetError().GetMessage() << endl;
        }
    }
    Aws::ShutdownAPI(options);
}
