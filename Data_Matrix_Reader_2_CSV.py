# -*- coding: utf-8 -*-
# """
# Created on Wed Dec  7 09:47:58 2022

# @author: frank.kubler

import cv2
import csv
import numpy as np
import threading

import zxingcpp  # pip install zxing-cpp (mini python 3.8)
from sys import platform
import sys

# global variable (implicite here)
my_mutex = threading.Lock()
data = None
keep_going = True


class PrintThread(threading.Thread):  # manipulation du résultat du scan

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global data
        global keep_going
        global my_mutex

        # adding time and date stuff and rearranging it
        from datetime import date, datetime
        today = date.today()
        previous_data = ''

        while keep_going:

            date = today.strftime("%Y-%m-%d")

            now = datetime.now()
            timeRN = now.strftime("%H:%M:%S")

            with my_mutex:
                to_publish_data = data
            if to_publish_data and previous_data != to_publish_data:
                print(f"cool new data found : {to_publish_data} , {date}, {timeRN}")
                previous_data = to_publish_data
            # else:
            #     last_data=''

            # **** This location is where we are adding the ability for the code to capture the Data and write it to a Text file
            # For this here we are writing the Information to Database.csv File located in the same directory (the desktop) as this code.
                filename = date + '_Database.csv'
                with open(filename, mode='a') as csvfile:

                    csvfileWriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                    csvfileWriter.writerow([to_publish_data + ', ' + date + "_" + timeRN])


class QrDecode(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):

        global data
        global keep_going
        global my_mutex

        # set up camera object called Cap which we will use to find OpenCV
        # check where the camera is connected(external webcam priority (2 to 0 )) and linux or windows (direct show needed for windows)
        if platform == "linux" or platform == "linux2":

            cap = cv2.VideoCapture(0)
            ret, img = cap.read()
            port = 0
            if not ret:
                cap = cv2.VideoCapture(1)
                ret, img = cap.read()
                port = 1
                if not ret:
                    cap = cv2.VideoCapture(2)
                    ret, img = cap.read()
                    port = 2
                    if not ret:
                        sys.exit('there is no camera connected')
            print('camera port is : ', port)

        elif platform == "win32":  # for PC
            cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)
            ret, img = cap.read()
            port = 2
            if not ret:
                cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                ret, img = cap.read()
                port = 1
                if not ret:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    ret, img = cap.read()
                    port = 0
                    if not ret:
                        sys.exit('there is no camera connected')

                print('camera port is : ', port)

        # This creates an Infinite loop to keep your camera searching for data at all times
        while keep_going:

            # Below is the method to get a image of the QR code
            ret, img = cap.read()
            results = zxingcpp.read_barcodes(img)

            if ret:
                for result in results:
                    # extract the bounding box location of the barcode and draw
                    # the bounding box surrounding the barcode on the image

                    # mutex writing result
                    with my_mutex:
                        data = result.text

                    position_list_str = str(result.position)  # zxingcpp object to string
                    position_list = position_list_str.split(' ')  # split space

                    # print((position_list)) # format result.position : (x1xy1,x2xy2,x3xy3,x4xy4)

                    x = []
                    y = []
                    for pos in range(len(position_list)):
                        # print(position_list[pos].split('x')[0])
                        tmp_x = ((position_list[pos].split('x')[0]))  # split over 'x' take first part  
                        tmp_y = ((position_list[pos].split('x')[1]))  # split over 'x' take first part  
                        x.append(tmp_x)
                        y.append(tmp_y)

                    y[3] = y[3].replace('\x00', '')  # supression du caractère de fin de byte \x00

                    x = [int(i) for i in x]  # x is str list : conversion into int
                    y = [int(i) for i in y]  # y is str list : conversion into int
                    rectangle = np.array([(x[0], y[0]), (x[1], y[1]), (x[2], y[2]), (x[3], y[3]), (x[0], y[0])])

                    cv2.polylines(img, [rectangle], False, (0, 255, 0), thickness=2)
                    # cv2.putText(img, result.text, (x1, y1 - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    cv2.putText(img, result.text, (x[0], y[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            # Below will display the live camera feed to the Desktop on Raspberry Pi OS LINUX OR WINDOWS  preview
            cv2.imshow("code detector / press esc to exit()", img)

            # At any point if you want to stop the Code all you need to do is press 'q' on your keyboard
            if (cv2.waitKey(1) == 27):  # 27 : key 'esc' other posibility : (cv2.waitKey(1) ==ord("q")
                keep_going = False
        # When the code is stopped the below closes all the applications/windows that the above has created
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':

    t1 = QrDecode()
    t1.start()

    t = PrintThread()
    t.start()
    t1.join()
    t.join()

    print('threads terminated')
