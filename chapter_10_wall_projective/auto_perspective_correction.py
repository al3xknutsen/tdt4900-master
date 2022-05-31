import math
import os

import cv2
import numpy as np

def perspective_correction(img_input, path_output, corners):
    # Read input
    # img = cv2.imread(path_input)
    img_height, img_width = img_input.shape[:2]

    # Specify input coordinates for corners in the following order:
    # Top left, top right, bottom right, bottom left
    input = np.float32(corners)
    tl, tr, _, bl = input

    # Compute length of top and left edges, and use these as output dimensions
    width = round(math.hypot(tl[0] - tr[0], tl[1] - tr[1]))
    height = round(math.hypot(tl[0] - bl[0], tl[1] - bl[1]))

    # Compute minimum and maximum values for x and y
    x, y = tl
    x_min = int(x)
    x_max = int(x + width - 1)
    y_min = int(y)
    y_max = int(y + height - 1)

    # Collect output coordinates
    output = np.float32([[x_min,y_min], [x_max,y_min], [x_max,y_max], [x_min,y_max]])

    # Compute perspective matrix
    matrix = cv2.getPerspectiveTransform(input, output)

    # Do perspective transformation, setting area outside image to black
    img_output = cv2.warpPerspective(img_input, matrix, (img_width, img_height), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))

    # Crop the image to only the output square
    img_output = img_output[y_min:y_max, x_min:x_max]

    # Save the corrected output
    cv2.imwrite(path_output, img_output)
    return img_output

def click_event(event, x, y, _, params):
	# Get event parameters
	img, img_name, path_output, corners, moving, img_clean, corner_index = params

	if event == cv2.EVENT_LBUTTONDOWN:
		# Start movement mode! The closest corner to the clicked
		# coordinates will be moved
		moving[0] = True

		# Calculate the distances between the place clicked and every
		# corner point, and sort the list afterwards. Corner indices
		# are preserved.
		distances = [(i, math.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2)) for i, c in enumerate(corners)]
		distances = sorted(distances, key=lambda d: d[1])

		# Set the currently selected corner to the be one with the smallest
		# distance from the clicked coordinates
		corner_index[0] = distances[0][0]
	
	elif event == cv2.EVENT_MOUSEMOVE:
		# Do nothing if the left mouse key has not be pressed first!
		if not moving[0]:
			return

		# Update the corner coordinates of the currently selected corner
		corners[corner_index[0]] = [x, y]

		# First, reset the image to a clean copy (without the box)
		img = img_clean.copy()

		# Draw a box on the image with the new coordinates and show result
		cv2.drawContours(img, [corners], 0, (0, 0, 0), 3)
		cv2.imshow("image", img)
	
	elif event == cv2.EVENT_LBUTTONUP:
		# Disable movement mode
		moving[0] = False
	
	elif event == cv2.EVENT_RBUTTONUP:
		# On right click: Perform perspective correction!
		perspective_correction(img_clean, path_output + img_name, corners)

if __name__=="__main__":
	# Define file paths
	root = "images/figures/"
	path_input = root + "raw/"
	path_output = root + "corrected/"

	# Get a list of all image files to be corrected
	images = os.listdir(path_input)

	# Collect corner coordinates
	corners = []

	# Loop through all images
	for img_name in images:
		# Parameters to be passed to the mouse callback. They are stored in
		# 1-element lists in order to pass by reference (because primitives
		# are passed by value)
		moving = [False]
		corner_index = [0]

		# Read an image from file
		img = cv2.imread(path_input + img_name, 1)

		# Create a clean copy of the image, to use for reset when redrawing
		img_clean = img.copy()

		# Set a box in the middle of the screen as start coordinates
		height, width, _ = img.shape
		corners = np.array([(width // 3, height // 3),
					(2 * width // 3, height // 3),
					(2 * width // 3, 2 * height // 3),
					(width // 3, 2 * height // 3)])
		
		# Draw the box!
		cv2.drawContours(img, [corners], 0, (0, 0, 0), 3)
		
		# Show the image
		cv2.namedWindow("image", cv2.WINDOW_NORMAL)
		cv2.imshow('image', img)

		# Listen for mouse events
		cv2.setMouseCallback('image', click_event, [img, img_name, path_output, corners, moving, img_clean, corner_index])

		# Stop and wait!
		cv2.waitKey(0)

	# When all images have been processed: Close all windows
	cv2.destroyAllWindows()
