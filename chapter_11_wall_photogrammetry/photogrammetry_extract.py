import cv2

def extract_nth_frame(path_video, path_images, n):
    vidcap = cv2.VideoCapture(path_video)
    success, image = vidcap.read()
    count = 0
    success = True

    while success:
        success, image = vidcap.read()
        if count % n == 0:
            cv2.imwrite(f"{path_images}{str(count).zfill(5)}.jpg", image)     # save frame as JPEG file
        if cv2.waitKey(10) == 27:                     # exit if Escape is hit
            break
        count += 1

if __name__ == "__main__":
    path_video = "C1_front60Single_blur.mp4"
    path_images = "Photogrammetry/images/"

    extract_nth_frame(path_video, path_images, 10)
