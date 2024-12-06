#include "smartdoor.h"

int main() {
    string profile;
    cout << "Enter your profile name: ";
    cin >> profile;

    // Folder for saving images
    string folderPath = "/home/pi/smartdoor/Captured Images";

    // Capture and save images
    captureSnapshot(profile, folderPath);

    return 0;
}
